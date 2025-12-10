# ------------------------------------------------------------
# LlmStrategy_Exact_Full.py
# 完全复刻 MQL4 神龙通道（结构优化 + 超清晰注释版）
# 逻辑与原版完全相同，只是提升了可读性与模块化
# 作者: 神龙通道至尊版（保留你原作者名）
# ------------------------------------------------------------

from datetime import time
from functools import partial
import numpy as np

from myutility import BarGenerator, Interval
from vnpy_ctastrategy import (
    CtaTemplate, StopOrder, TickData, BarData, TradeData,
    OrderData, ArrayManager
)
# from vnpy_ctastrategy.backtesting import Interval


class DragenStrategyExact(CtaTemplate):
    """
    神龙通道策略（完全复刻 MQL4）
    说明：
    - 目标：在vn.py上按原MQL4实现的索引与计算完全复刻（包括数组方向、EMA平滑与XMA中心移动平均逻辑）。
    - 不改变任何逻辑，仅重构、模块化、并添加详尽注释以便理解。
    """

    # -------------------------
    # 参数（与你原版保持一致）
    # -------------------------
    author = "神龙通道至尊版"

    fixed_size: int = 1
    xma_n_3: int = 25
    xma_n_3_1: int = 25
    xma_n_2: int = 25
    xma_n_2_1: int = 25
    belt_weights_len: int = 20
    sh: int = 30
    belt_smooth_period: int = 90

    # weight_sum 采用与原版相同计算（class-level 计算，和实例属性一致）
    weight_sum = belt_weights_len * (belt_weights_len + 1) / 2
# 支持用户传入多个目标周期，例如 ["4h","1d","1h","30m","15m"]
    long_kline = "4H"
    _long_map = {"D": 60*24, "4H": 4*60, "1H": 60}
    parameters = [
        "fixed_size",
        "xma_n_3", "xma_n_3_1",
        "xma_n_2", "xma_n_2_1",
        "belt_weights_len", "belt_smooth_period",
        "sh", "target_intervals"
    ]

    variables = [
        "last_signal",
        "entry_price"
    ]

    # ============================================================
    # 初始化
    # ============================================================
    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict):
        """
        初始化仅设置基础状态，不做重计算。
        ArrayManager 采用 300 的历史长度（保持原版）。
        """
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 状态变量（与原版字段一致）
        self.last_signal = ""
        self.entry_price = 0.0

        # 保证 target_intervals 已由 setting 覆盖（如果存在）
        if isinstance(setting, dict) and setting.get("target_intervals"):
            self.long_kline = setting.get("target_intervals")
        self.long_minutes = self._long_map.get(self.long_kline, 60*4)

    def on_init(self) -> None:
        """
        on_init 时创建 4 小时的合成 BarGenerator，并加载历史数据。
        注意：load_bar(300, Interval.HOUR, None, True) 与原版保持一致。
        """
        self.write_log("神龙通道策略初始化")
        
        # 生成 4 小时 K 线（每 4 根小时线合成一根 4H）
        
        # 每个周期创建独立的 ArrayManager（大小保持 300，和原版一致）
        self.am = ArrayManager(1000)

        # 绑定回调（使用 partial 传入目标周期标识）
        on_window_bar = partial(self._on_tf_bar, self.long_kline)
        # 构建每个目标周期的 BarGenerator 与 ArrayManager
        if self.long_kline == "D":
            # 日线特殊处理，固定 daily_end
            daily_end = time(21, 59)  # 收盘时间 00:00 UTC+8
            self.bg_long = BarGenerator(
                self.on_bar,
                window=1,
                on_window_bar=on_window_bar,
                interval=Interval.DAILY,
                daily_end=daily_end
            )
        elif self.long_kline == "4H":
            self.bg_long = BarGenerator(
                self.on_bar,
                window=1,
                on_window_bar=on_window_bar,
                interval=Interval.FOUR_HOURS
            )
        else:
            # 其他周期按分钟聚合
            self.bg_long = BarGenerator(
                self.on_bar,
                window=self.long_minutes,
                on_window_bar=on_window_bar,
                interval=Interval.MINUTE
            )

        # 为每种 interval_type 加载历史（300）
        # try:
        #     # note: 原版使用 load_bar(300, Interval.HOUR, None, True)
        #     # 这里保持一致：加载最近 300 根该 interval_type 的 bar
        #     self.load_bar(100, interval_type, None, True)
        # except Exception as e:
        #     # 记录但继续（以保持容错性）
        #     self.write_log(f"加载历史失败: {interval_type}, 错误: {e}")

    # ============================================================
    # 事件入口（保持原版流程）
    # ============================================================
    def on_bar(self, bar: BarData):
        """
        所有原始 bar（任意周期）都会经过这里。
        我们需要把原始 bar 发送给所有注册的 BarGenerator，让它们自行合成目标周期。
        """
        # print(f" Bar: {bar.datetime} O:{bar.open_price} H:{bar.high_price} L:{bar.low_price} C:{bar.close_price}，interval: {bar.interval}")
        try:
            self.bg_long.update_bar(bar)
        except Exception as e:
            # 容错，记录错误
            self.write_log(f"BarGenerator.update_bar 错误: {e}")
 
# ------------------------- 合成周期回调 -------------------------
    def _on_tf_bar(self, tf: str, bar: BarData) -> None:
        """
        某个目标周期 (tf) 的合成 Bar 到达时，会走这里。
        我们把 bar 更新到对应的 am，并执行核心计算逻辑。
        """
        # debug 打印（保持原版调试信息）
        print(f"[{tf}] 目标周期 Bar: {bar.datetime} O:{bar.open_price} H:{bar.high_price} L:{bar.low_price} C:{bar.close_price}")

        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 调用核心逻辑，注意传入该周期专属的 am
        self._process_bar_logic(tf, bar, self.am)

    def on_tick(self, tick: TickData) -> None:
        """保留（原版为空实现）"""
        pass

    # ============================================================
    # 核心处理：把你原来 on_4hour_bar 中的逻辑全部封装进这里
    # ============================================================
    def _process_bar_logic(self, tf: str, bar: BarData, am: ArrayManager) -> None:
        """
        tf: 目标周期字符串（例如 '4h'）
        bar: 合成周期的 BarData
        am: 对应周期的 ArrayManager（0=最旧, -1=最新）


        本函数严格保留你原版的计算、索引方向、边界处理与下单逻辑。
        关键点：为了复刻 MQL4 的索引（MQL4: 0=最新），我们把 am.high/am.low 反转。
        """
        # ------------- 数据准备（不改变） -------------
        highs = np.array(am.high)[::-1] # 0=最新
        lows = np.array(am.low)[::-1]
        length = len(highs) - self.sh

        # -------------------- 指标计算（调用独立函数） --------------------
        # _compute_belt_exact 返回 belt2, belt3, belt4, slld_0, slld_8（数组，MQL4方向）
        belt2, belt3, belt4, slld_0, slld_8 = self._compute_belt_exact(length, highs, lows)
        # _compute_xma_exact 返回 xma3_1, xma2_1（数组，MQL4方向）
        xma3_1, xma2_1 = self._compute_xma_exact(length, highs, lows)

        # 下面这些 ibuf 的计算直接沿用你原来实现
        g_ibuf_116 = 2.0 * xma3_1 - xma2_1
        g_ibuf_120 = 2.0 * xma2_1 - xma3_1
        # for i in range(0, 5):
        #     print(
        #         f"Bar {i}: g_ibuf_116={g_ibuf_116[i]} , g_ibuf_120={g_ibuf_120[i]}"
        #     )
        # g_ibuf_124 = 3.9 * (xma2_1 - xma3_1) + xma2_1
        # g_ibuf_128 = xma3_1 - 3.9 * (xma2_1 - xma3_1)

        # -------------------- 安全取值（因数组可能过短） --------------------
        # 原版在几个地方做了类似的保护，这里抽象成 safe() 小函数，仍然写日志以便诊断
        def safe(arr, idx):
            try:
                return float(arr[idx])
            except Exception as e:
                # 记录错误信息（不抛出异常，保持原代码容错风格）
                self.write_log(f"⚠️ safe 取值错误: 数组长度={len(arr)}, 索引={idx}, 错误={e}")
                return float("nan")

        # 取当前（索引0）与前一根（索引1）的指标值（MQL4 索引方向）
        g116_0 = safe(g_ibuf_116, 0)
        g116_1 = safe(g_ibuf_116, 1)
        g120_0 = safe(g_ibuf_120, 0)
        g120_1 = safe(g_ibuf_120, 1)
        slld0_0 = safe(slld_0, 0)
        slld8_0 = safe(slld_8, 0)

        # 当前与前一根的实际价格（注意 highs/lows 已经是 MQL4 顺序）
        low_0, low_1 = lows[0], lows[1]
        high_0, high_1 = highs[0], highs[1]

        # -------------------- 原始信号逻辑（保持完全一致） --------------------
        li_16 = False
        li_20 = False

        # BUY 条件（逐步保留你原版的判断式）
        condition_buy = (
            g116_1 < low_1 and
            g116_0 > low_0 and
            ((g120_0 > slld0_0 and g116_0 > slld8_0) or
             (g120_0 < slld0_0 and g116_0 > slld8_0))
        )

        # SELL 条件
        condition_sell = (
            high_1 < g120_1 and
            high_0 > g120_0 and
            ((g120_0 < slld0_0 and g116_0 < slld8_0) or
             (g120_0 < slld0_0 and g116_0 > slld8_0))
        )

        # 设置状态标志（基于实际触发的信号）
        if condition_buy:
            li_16 = True
        if condition_sell:
            li_20 = True

        # 关闭（CLOSE）条件（原逻辑包含额外的 not li_16 / not li_20）
        condition_close_sell = (
            g116_1 < low_1 and
            g116_0 > low_0 and
            ((g120_0 < slld0_0 and g116_0 < slld8_0) or
             not (g120_0 < slld0_0 and g116_0 > slld8_0)) and
            not li_16
        )
        condition_close_buy = (
            high_1 < g120_1 and
            high_0 > g120_0 and
            ((g120_0 > slld0_0 and g116_0 > slld8_0) or
             not (g120_0 < slld0_0 and g116_0 > slld8_0)) and
            not li_20
        )

        # 再次保护性地与 li_16/li_20 进行逻辑与（与原版重复但无副作用）
        condition_close_sell = condition_close_sell and not li_16
        condition_close_buy = condition_close_buy and not li_20

        # 最终用于下单/发信号的价格（原版使用 bar.close_price）
        price = bar.close_price

        # -------------------- 触发动作（日志 + 调用 on_signal） --------------------
        # 我把重复的日志打印封装成 _log_bar_info 来减少重复代码，但日志内容与原版保持一致
        if condition_buy:
            self._log_bar_info("BUY", bar, g116_0, g116_1, g120_0, g120_1, slld0_0, slld8_0, low_0, low_1, high_0, high_1)
            # 触发 BUY 与对应的 SL-BUY（原版同时触发）
            self.on_signal("BUY", price)
            self.on_signal("SL-BUY", price)

        elif condition_sell:
            self._log_bar_info("SELL", bar, g116_0, g116_1, g120_0, g120_1, slld0_0, slld8_0, low_0, low_1, high_0, high_1)
            self.on_signal("SELL", price)
            self.on_signal("SL-SELL", price)

        elif condition_close_buy:
            self._log_bar_info("CLOSE-BUY", bar, g116_0, g116_1, g120_0, g120_1, slld0_0, slld8_0, low_0, low_1, high_0, high_1)
            self.on_signal("CLOSE-BUY", price)

        elif condition_close_sell:
            self._log_bar_info("CLOSE-SELL", bar, g116_0, g116_1, g120_0, g120_1, slld0_0, slld8_0, low_0, low_1, high_0, high_1)
            self.on_signal("CLOSE-SELL", price)

        # 和原版一致：处理完成后发送事件
        self.put_event()

    # ============================================================
    # 日志辅助函数（把重复的写日志/打印封装，保持原信息）
    # ============================================================
    def _log_bar_info(self, tag: str, bar: BarData,
                      g116_0, g116_1, g120_0, g120_1, slld0_0, slld8_0, low_0, low_1, high_0, high_1) -> None:
        """
        统一打印和 write_log 的信息格式，和原实现的信息一致。
        只做封装以减少重复代码。
        """
        # 控制台打印（原版有打印）
        # print(f"{tag} - Bar信息 - 时间: {bar.datetime}, O: {bar.open_price}, H: {bar.high_price}, L: {bar.low_price}, C: {bar.close_price}, V: {bar.volume}")
        # print(f"{tag} - 指标值: g116_0={g116_0:.6f}, g116_1={g116_1:.6f}, g120_0={g120_0:.6f}, g120_1={g120_1:.6f}, slld0_0={slld0_0:.6f}, slld8_0={slld8_0:.6f}")

        # 写入策略日志（vn.py 的 write_log）
        self.write_log(f"{tag} trigger")
        self.write_log(f"Bar信息 - 时间: {bar.datetime}, O: {bar.open_price}, H: {bar.high_price}, L: {bar.low_price}, C: {bar.close_price}, V: {bar.volume}")
        self.write_log(f"指标值: g116_0={g116_0:.6f}, g116_1={g116_1:.6f}, g120_0={g120_0:.6f}, g120_1={g120_1:.6f}, slld0_0={slld0_0:.6f}, slld8_0={slld8_0:.6f}")
        self.write_log(f"价格: low_0={low_0:.4f}, low_1={low_1:.4f}, high_0={high_0:.4f}, high_1={high_1:.4f}")
        # 注意：原版还写了价格信息（low/high），如果需要可以再添加。当前保持内容一致性并简洁。

    # ============================================================
    # 计算部分（完全复刻 MQL4 行为）
    # ============================================================
    def _compute_belt_exact(self, length: int, highs: np.ndarray, lows: np.ndarray) -> tuple:
        """
        精确复刻 MQL4 的 Belt 计算（数组方向与 MQL4 一致：0=最新）
        返回：belt2, belt3, belt4, slld_0, slld_8
        细节注释：
        - 输入 highs/lows 已经是 MQL4 顺序（0=最新），length 表示有效计算长度（len(highs)-sh）
        - 为保持 MQL4 的行为，数组初始化全部为 0（而不是 NaN），并且 EMA 平滑按照 MQL4 那样正向迭代
        - 公式与原版一致：belt0/belt1 用加权求和，belt2/belt3 用 EMA 平滑，belt4=belt2-belt3，slld0=belt2+2*belt4, slld8=belt3-2*belt4
        """
        n = self.belt_weights_len + 1

        # 如果可用长度不足，返回长度为 length 的 NaN 数组（调用端会用 safe() 处理）
        if length < n:
            return tuple([np.full(length, np.nan) for _ in range(5)])

        # 初始数组均为 0，与 MQL4 ArrayInitialize(array,0) 的行为一致
        belt0 = np.zeros(length)
        belt1 = np.zeros(length)
        belt2 = np.zeros(length)
        belt3 = np.zeros(length)
        belt4 = np.zeros(length)
        slld_0 = np.zeros(length)
        slld_8 = np.zeros(length)

        # -------------------------
        # 逐条计算 belt0/belt1（加权和）
        # 原逻辑：对每个 i，累加权重 * highs[i+w] 与 weight * lows[i+w]
        # 注意：遍历方向采用从 length-1 到 0，与 MQL4 的索引映射一致（保持行为）
        # -------------------------
        for i in range(length - 1, -1, -1):
            # 防护：确保 i + belt_weights_len 在 highs 索引范围内
            if i + self.belt_weights_len >= len(highs):
                # 如果越界就跳过，这与原版在边界处理上的行为一致
                continue

            sum_high = 0.0
            sum_low = 0.0
            # w 从 0 到 n-1，对应权重 belt_weights_len - w
            for w in range(n):
                weight = self.belt_weights_len - w
                # 原版在 MQL4 中的索引对应到我们的 highs 已经是 MQL4 顺序（0=最新），
                # 因此直接使用 highs[i + w] 与 lows[i + w]
                sum_high += weight * highs[i + w]
                sum_low += weight * lows[i + w]

            belt0[i] = sum_high / self.weight_sum
            belt1[i] = sum_low / self.weight_sum
            # print(
            #     f"H={highs[i]}, L={lows[i]}"
            #     f"Bar {i}, belt0={belt0[i]:.5f}, belt1={belt1[i]:.5f}"
            # )
        # -------------------------
        # EMA 平滑（与 MQL4 保持一致）
        # belt2[i] = (2*belt0[i] + (period-1)*belt2[i+1]) / (period+1)
        # 从 length-2 到 0 反向迭代，保持 MQL4 的累积效果
        # -------------------------
        for i in range(length - 2, -1, -1):
            belt2[i] = (2 * belt0[i] + (self.belt_smooth_period - 1) * belt2[i + 1]) / (self.belt_smooth_period + 1)
            belt3[i] = (2 * belt1[i] + (self.belt_smooth_period - 1) * belt3[i + 1]) / (self.belt_smooth_period + 1)
            # print(
            #     f"Bar {i + 1}: belt2= {belt2[i + 1]}, belt3 = {belt3[i+1]}"
            # )
 

        # belt4 与 slld
        belt4 = belt2 - belt3
        slld_0 = belt2 + 2.0 * belt4
        slld_8 = belt3 - 2.0 * belt4
        # for i in range(0, 5):
        #     print(
        #         f"Bar {i}: belt0= {belt0[i]}, belt1= {belt1[i]}, belt2={belt2[i]}, belt3 = {belt3[i]}, belt4 = {belt4[i]}, slld_0 = {slld_0[i]}, slld_8 = {slld_8[i]}"
        #     )
        return belt2, belt3, belt4, slld_0, slld_8

    def _compute_centered_ma_mql4(self, length: int, data: np.ndarray, window: int) -> np.ndarray:
        """
        中心移动平均计算（保持 ArrayManager 顺序，但在计算时映射索引）
        """
        result = np.zeros(len(data))
        half_window = (window - 1) // 2
        
        # 使用 ArrayManager 顺序（0=最旧，-1=最新）
        # 但在计算时映射到 MQL4 的逻辑
        for mql4_i in range(length, -1, -1):  # 从最旧到最新 (与 MQL4 一致)
            if mql4_i >= half_window:
                # 正常情况
                sum_val = 0.0
                for mql4_j in range(mql4_i + half_window, mql4_i - half_window - 1, -1):
                    # 使用 lows[-1-mql4_j] 来访问 MQL4 索引对应的数据
                    # if (mql4_j < len(data)):
                    sum_val += data[mql4_j]
                result[mql4_i] = sum_val / window
            else:
                # 边界情况
                sum_val = 0.0
                for mql4_j in range(mql4_i + half_window, -1, -1):
                    # if (mql4_j < len(data)):
                    sum_val += data[mql4_j]
                
                # MQL4 的特殊权重调整
                adjustment = (half_window - mql4_i) / (half_window + mql4_i + 1)
                result[mql4_i] = (sum_val + sum_val * adjustment) / window
        # result = result[::-1] 
        # for i in range(0, 5):
        #     print(
        #         f"Bar {i}: result={result[i]}"
        #     )
        return result

    def _compute_xma_exact(self, length: int, highs: np.ndarray, lows: np.ndarray) -> tuple:
        """
        精确复刻 MQL4 的 XMA（双重中心化移动平均）：
        - 先对 lows 做一次中心化平均 -> xma3_0，然后再对 xma3_0 做第二次中心化平均 -> xma3_1
        - 对 highs 做同样的两次平滑得到 xma2_1
        返回 (xma3_1, xma2_1)，数组方向均为 MQL4（0=最新）
        """
        # 第一次中心平均（低价）
        xma3_0 = self._compute_centered_ma_mql4(length, lows, self.xma_n_3)
        # 第二次中心平均（低价）
        xma3_1 = self._compute_centered_ma_mql4(length, xma3_0, self.xma_n_3_1)
        # 第一次中心平均（高价）
        xma2_0 = self._compute_centered_ma_mql4(length, highs, self.xma_n_2)
        # 第二次中心平均（高价）
        xma2_1 = self._compute_centered_ma_mql4(length, xma2_0, self.xma_n_2_1)

        return xma3_1, xma2_1

    # ============================================================
    # 交易执行部分（与原版一致）
    # ============================================================
    def on_signal(self, signal: str, price: float) -> None:
        """
        执行买卖指令（不改逻辑）
        - signal 是字符串，如 "BUY","SELL","CLOSE-BUY","CLOSE-SELL","SL-BUY","SL-SELL"
        - price 为下单价格（原版使用 bar.close_price）
        行为与原版完全一致：
         * BUY: 如果持有空头先平空 then 开多；pos==0 则直接开多
         * SELL: 如果持有多头先平多 then 开空；pos==0 则直接开空
         * CLOSE-BUY/CLOSE-SELL: 平仓
         * SL-BUY/SL-SELL: 作为止损，平仓（按原版逻辑）
        """
        signal = signal.upper()
        self.last_signal = f"{signal}@{price}"
        pos = self.pos

        if signal == "BUY":
            if pos < 0:
                # 先平空（cover），再开多
                self.cover(price, abs(pos))
                self.buy(price, self.fixed_size)
            elif pos == 0:
                self.buy(price, self.fixed_size)

        elif signal == "SELL":
            if pos > 0:
                # 先平多，再开空
                self.sell(price, abs(pos))
                self.short(price, self.fixed_size)
            elif pos == 0:
                self.short(price, self.fixed_size)

        elif signal == "CLOSE-BUY":
            if pos > 0:
                self.sell(price, abs(pos))

        elif signal == "CLOSE-SELL":
            if pos < 0:
                self.cover(price, abs(pos))

        elif signal == "SL-BUY":
            # 止损逻辑：当持有多头时平仓
            if pos > 0:
                self.sell(price, abs(pos))

        elif signal == "SL-SELL":
            # 止损逻辑：当持有空头时平仓
            if pos < 0:
                self.cover(price, abs(pos))

        # 发事件以便 GUI/策略管理器更新
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        """保留（原版为空实现）"""
        pass

    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调：记录 entry_price（与原版一致），并触发事件更新
        """
        self.entry_price = float(trade.price)
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder) -> None:
        """保留（原版为空实现）"""
        pass
