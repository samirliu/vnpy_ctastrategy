# LlmStrategy_Exact_Full.py
# 完全复刻 MQL4 神龙通道 LlmStrategy

from typing import List
import numpy as np
from vnpy_ctastrategy import (
    CtaTemplate, StopOrder, TickData, BarData, TradeData, 
    OrderData, BarGenerator, ArrayManager
)
from vnpy_ctastrategy.backtesting import Interval


class DragenStrategyExact(CtaTemplate):
    """
    神龙通道策略（完全复刻 MQL4）
    """
    author = "神龙通道至尊版"

    # 策略参数
    fixed_size: int = 1
    xma_n_3: int = 25
    xma_n_3_1: int = 25  
    xma_n_2: int = 25
    xma_n_2_1: int = 25
    belt_weights_len: int = 20
    sh: int = 30
    belt_smooth_period: int = 90
    weight_sum = belt_weights_len * (belt_weights_len + 1) / 2
    parameters = [
        "fixed_size", 
        "xma_n_3", 
        "xma_n_3_1",
        "xma_n_2", 
        "xma_n_2_1",
        "belt_weights_len",
        "belt_smooth_period",
        "sh"

    ]

    variables = ["last_signal", "entry_price"]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        max_period = max(
            self.xma_n_3 + self.xma_n_3_1,
            self.xma_n_2 + self.xma_n_2_1,
            self.belt_weights_len,
            self.belt_smooth_period
        )
        # self.am = ArrayManager(200)
        # self.bg = BarGenerator(self.on_bar)
        
        self.last_signal = ""
        self.entry_price = 0.0

    def on_init(self) -> None:
        self.write_log("神龙通道策略初始化")

        self.bg_4hour = BarGenerator(self.on_bar, 4, self.on_4hour_bar, Interval.HOUR)
        
        self.am = ArrayManager(300)
        self.load_bar(300, Interval.HOUR, None, True)
        # self.load_bar(max(self.xma_n_3, self.xma_n_2, self.belt_weights_len))

    def on_bar(self, bar: BarData):
        """处理 1 分钟/1 小时原始数据"""
        # 更新 BarGenerator
        self.bg_4hour.update_bar(bar)

    def on_4hour_bar(self, bar: BarData):
        """处理合成的 4 小时线"""
        print(f"4小时线: {bar.datetime}, O:{bar.open_price}, H:{bar.high_price}, "
              f"L:{bar.low_price}, C:{bar.close_price}, V:{bar.volume}")
        self._handle_bar(bar)

    def on_tick(self, tick: TickData) -> None:
        # self.bg.update_tick(tick)
        pass

    def _handle_bar(self, bar: BarData) -> None:

        print(">>> DEBUG on_bar 收到 Bar")
        print(f"    bar.datetime: {bar.datetime}  (type: {type(bar.datetime)})")
        print(f"    bar.vt_symbol: {getattr(bar, 'vt_symbol', None)}")
        print(f"    strategy.vt_symbol: {getattr(self, 'vt_symbol', None)}")
        print(f"    strategy.interval (if any): {getattr(self, 'interval', None)}")
        """
        完全复刻 MQL4 神龙通道 belt0/belt1 计算
        只打印，不执行下单逻辑
        """
        self.am.update_bar(bar)
        if not self.am.inited:
            return
        # -------------------- 提取 highs / lows --------------------
        highs = np.array(self.am.high)
        highs = highs[::-1] 
        lows = np.array(self.am.low)
        lows = lows[::-1]
        length = len(highs) - self.sh
        belt2, belt3, belt4, slld_0, slld_8 = self._compute_belt_exact(length, highs, lows)
        xma3_1, xma2_1 = self._compute_xma_exact(length, highs, lows)

        g_ibuf_116 = 2.0 * xma3_1 - xma2_1
        g_ibuf_120 = 2.0 * xma2_1 - xma3_1
        g_ibuf_124 = 3.9 * (xma2_1 - xma3_1) + xma2_1
        g_ibuf_128 = xma3_1 - 3.9 * (xma2_1 - xma3_1)
        idx_0, idx_1 = 0, 1

            # 确保长度足够
        def safe_get(arr, idx):
            try:
                return float(arr[idx])
            except Exception as e:
                self.write_log(f"⚠️ safe_get错误: 数组长度{len(arr)}, 索引{idx}, 错误: {e}")
                return float('nan')
        # 当前K线的下通道边界值 
        g116_0 = safe_get(g_ibuf_116, idx_0)
        # 前一根K线的下通道边界值 
        g116_1 = safe_get(g_ibuf_116, idx_1)
        # 当前K线的上通道边界值
        g120_0 = safe_get(g_ibuf_120, idx_0)
        # 前一根K线的上通道边界值
        g120_1 = safe_get(g_ibuf_120, idx_1)
        #上SL线，上止损线
        slld0_0 = safe_get(slld_0, idx_0)
        #下SL线，下止损线
        slld8_0 = safe_get(slld_8, idx_0)

        low_0, low_1 = lows[idx_0], lows[idx_1]
        high_0, high_1 = highs[idx_0], highs[idx_1]
        
        li_16 = False
        li_20 = False

        condition_buy = (
            g116_1 < low_1 and 
            g116_0 > low_0 and
            ((g120_0 > slld0_0 and g116_0 > slld8_0) or 
             (g120_0 < slld0_0 and g116_0 > slld8_0))
        )
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

        condition_close_sell = condition_close_sell and not li_16
        condition_close_buy = condition_close_buy and not li_20

        price = bar.close_price
        if condition_buy:

            # 打印BarData信息
            print(f"Bar信息 - 时间: {bar.datetime}, O: {bar.open_price}, H: {bar.high_price}, L: {bar.low_price}, C: {bar.close_price}, V: {bar.volume}")
            print(f"指标值: g116_0={g116_0:.4f}, g116_1={g116_1:.4f}, g120_0={g120_0:.4f}, g120_1={g120_1:.4f}, slld0_0={slld0_0:.4f}, slld8_0={slld8_0:.4f}")
            print(f"价格: low_0={low_0:.4f}, low_1={low_1:.4f}, high_0={high_0:.4f}, high_1={high_1:.4f}")
            self.write_log("condition_buy trigger")
            # 打印BarData信息
            self.write_log(f"Bar信息 - 时间: {bar.datetime}, O: {bar.open_price}, H: {bar.high_price}, L: {bar.low_price}, C: {bar.close_price}, V: {bar.volume}")
            self.write_log(f"指标值: g116_0={g116_0:.4f}, g116_1={g116_1:.4f}, g120_0={g120_0:.4f}, g120_1={g120_1:.4f}, slld0_0={slld0_0:.4f}, slld8_0={slld8_0:.4f}")
            self.write_log(f"价格: low_0={low_0:.4f}, low_1={low_1:.4f}, high_0={high_0:.4f}, high_1={high_1:.4f}")
            self.on_signal("BUY", price)
            # SL-BUY同时触发
            self.on_signal("SL-BUY", price)
        elif condition_sell:
            self.write_log("condition_sell trigger")
            # 打印BarData信息
            self.write_log(f"Bar信息 - 时间: {bar.datetime}, O: {bar.open_price}, H: {bar.high_price}, L: {bar.low_price}, C: {bar.close_price}, V: {bar.volume}")
            self.write_log(f"指标值: g116_0={g116_0:.4f}, g116_1={g116_1:.4f}, g120_0={g120_0:.4f}, g120_1={g120_1:.4f}, slld0_0={slld0_0:.4f}, slld8_0={slld8_0:.4f}")
            self.write_log(f"价格: low_0={low_0:.4f}, low_1={low_1:.4f}, high_0={high_0:.4f}, high_1={high_1:.4f}")
            self.on_signal("SELL", price) 
            # SL-SELL同时触发
            self.on_signal("SL-SELL", price)
        elif condition_close_buy:
            self.write_log("CLOSE-BUY trigger")
            # 打印BarData信息
            self.write_log(f"Bar信息 - 时间: {bar.datetime}, O: {bar.open_price}, H: {bar.high_price}, L: {bar.low_price}, C: {bar.close_price}, V: {bar.volume}")
            self.write_log(f"指标值: g116_0={g116_0:.4f}, g116_1={g116_1:.4f}, g120_0={g120_0:.4f}, g120_1={g120_1:.4f}, slld0_0={slld0_0:.4f}, slld8_0={slld8_0:.4f}")
            self.write_log(f"价格: low_0={low_0:.4f}, low_1={low_1:.4f}, high_0={high_0:.4f}, high_1={high_1:.4f}")
            self.on_signal("CLOSE-BUY", price)
        elif condition_close_sell:
            self.write_log("CLOSE-SELL trigger")
            # 打印BarData信息
            self.write_log(f"Bar信息 - 时间: {bar.datetime}, O: {bar.open_price}, H: {bar.high_price}, L: {bar.low_price}, C: {bar.close_price}, V: {bar.volume}")
            self.write_log(f"指标值: g116_0={g116_0:.4f}, g116_1={g116_1:.4f}, g120_0={g120_0:.4f}, g120_1={g120_1:.4f}, slld0_0={slld0_0:.4f}, slld8_0={slld8_0:.4f}")
            self.write_log(f"价格: low_0={low_0:.4f}, low_1={low_1:.4f}, high_0={high_0:.4f}, high_1={high_1:.4f}")
            self.on_signal("CLOSE-SELL", price)


        # -------------------- 不触发交易，只发事件 --------------------
        self.put_event()

    # ------------------ 核心计算函数 ------------------
    def _compute_belt_exact(self, length: int, highs: np.ndarray, lows: np.ndarray) -> tuple:
        """
        精确复刻MQL4的Belt计算 - 所有数组初始化为0
        """
        n = self.belt_weights_len + 1
        
        if length < n:
            return tuple([np.full(length, np.nan) for _ in range(5)])
        
        # 初始化数组为0，与MQL4一致！
        belt0 = np.zeros(length)
        belt1 = np.zeros(length)
        belt2 = np.zeros(length)  
        belt3 = np.zeros(length)  
        belt4 = np.zeros(length)  
        slld_0 = np.zeros(length)
        slld_0 = np.zeros(length)

        # 计算belt0和belt1
# -------------------- 逐个计算 --------------------
        for i in range(length-1, -1, -1):
            if i + self.belt_weights_len >= len(highs):
                continue

            sum_high = 0.0
            sum_low = 0.0
            for w in range(n):
                weight = self.belt_weights_len - w
                # 关键修改：使用 -1 - (i + w) 对应 MQL4 的 ii + w
                sum_high += weight * highs[i + w]
                sum_low += weight * lows[i + w]

            belt0[i] = sum_high / self.weight_sum
            belt1[i] = sum_low / self.weight_sum
                
            # print(
            #     f"H={highs[i]}, L={lows[i]}"
            #     f"Bar {i}, belt0={belt0[i]:.5f}, belt1={belt1[i]:.5f}"
            # )

        # EMA平滑 - 直接计算，不检查条件（与MQL4完全一致）
        for i in range(length-2, -1, -1):
            # print(
            #     f"belt0i={belt0[i]}, belt2i+1={belt2[i+1]}"
            # )
            # print(f"Bar {i}: belt0 = {belt0[i]}, belt2 = {belt2[i+1]}")
            belt2[i] = (2 * belt0[i] + (self.belt_smooth_period - 1) * belt2[i+1]) / (self.belt_smooth_period + 1)
            belt3[i] = (2 * belt1[i] + (self.belt_smooth_period - 1) * belt3[i+1]) / (self.belt_smooth_period + 1)
            # print(
            #     f"H={highs[i]}, L={lows[i]}"
            #     f"Bar {i}, belt2={belt2[i]:.5f}, belt3={belt3[i]:.5f}"
            # )
        
        # 计算belt4和slld
        belt4 = belt2 - belt3
        slld_0 = belt2 + 2.0 * belt4
        slld_8 = belt3 - 2.0 * belt4

        # belt2 = belt2[::-1]  # 反转数组，使索引 0 = 最旧，索引 -1 = 最新
        # belt3 = belt3[::-1]
        # belt4 = belt4[::-1]
        # slld_0 = slld_0[::-1]
        # slld_8 = slld_8[::-1]
                # 打印最终的belt0和belt1值
        # print("=== 最终belt0和belt1值 ===")
        # for i in range(0, length):
        #     print(f"Bar {i}: highs = {highs[i]}, lows = {lows[i]}")
        #     print(f"Bar {i}: belt0 = {belt0[i]}, belt1 = {belt1[i]},belt2 = {belt2[i]}, belt3 = {belt3[i]}, belt4 = {belt4[i]}, slld_0 = {slld_0[i]}, slld_8 = {slld_8[i]}")
        return belt2, belt3, belt4, slld_0, slld_8

    # def _compute_centered_ma(self, data: np.ndarray, window: int) -> np.ndarray:
    #     """
    #     中心移动平均（完全复刻 MQL4 iMAOnArray）
    #     对数组开头和结尾自动处理可用窗口长度
    #     """
    #     length = len(data)
    #     result = np.zeros(length)
    #     half_window = (window - 1) // 2

    #     for i in range(length):
    #         left = max(0, i - half_window)
    #         right = min(length - 1, i + half_window)
    #         actual_len = right - left + 1
    #         result[i] = np.sum(data[left:right + 1]) / actual_len

    #     return result



    def _compute_centered_ma_mql4(self, length: int, data: np.ndarray, window: int) -> np.ndarray:
        """
        中心移动平均计算（保持 ArrayManager 顺序，但在计算时映射索引）
        """
        result = np.zeros(len(data))
        half_window = (window - 1) // 2
        
        # 使用 ArrayManager 顺序（0=最旧，-1=最新）
        # 但在计算时映射到 MQL4 的逻辑
        for mql4_i in range(length-1, -1, -1):  # 从最旧到最新 (与 MQL4 一致)
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
        精确复刻MQL4的XMA计算
        高低XMA分别计算，使用双重平滑
        """
        # 初始化数组为0，与MQL4 ArrayInitialize一致


        # -------------------
        # XMA3_0 - 低价/第一次平滑
        xma3_0 = self._compute_centered_ma_mql4(length, lows, self.xma_n_3)
        # XMA3_1 - 第二次平滑
        xma3_1 = self._compute_centered_ma_mql4(length, xma3_0, self.xma_n_3_1)
        # # XMA2_0 - 高价/第一次平滑
        xma2_0 = self._compute_centered_ma_mql4(length, highs, self.xma_n_2)
        # # XMA2_1 - 第二次平滑
        xma2_1 = self._compute_centered_ma_mql4(length, xma2_0, self.xma_n_2_1)

        
        # -------------------
        # 可选调试输出（仅用于确认前后5根K线）
        # for i in range(0, length):
        #     print(
        #         f"Bar {i}: XMA3_1={xma3_1[i]:.6f}, XMA2_1={xma2_1[i]:.6f}"
        #     )

        return xma3_1, xma2_1
    

    # ------------------ 交易执行 ------------------
    def on_signal(self, signal: str, price: float) -> None:
        signal = signal.upper()
        self.last_signal = f"{signal}@{price}"
        pos = self.pos

        if signal == "BUY":
            if pos < 0:
                self.cover(price, abs(pos))
                self.buy(price, self.fixed_size)
            elif pos == 0:
                self.buy(price, self.fixed_size)
        elif signal == "SELL":
            if pos > 0:
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
            if pos > 0:
                self.sell(price, abs(pos))
        elif signal == "SL-SELL":
            if pos < 0:
                self.cover(price, abs(pos))
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        pass

    def on_trade(self, trade: TradeData) -> None:
        self.entry_price = float(trade.price)
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder) -> None:
        pass
    def get_mql4_index(self, am_index: int, total_bars: int) -> int:
        """
        将 ArrayManager 索引转换为 MQL4 索引
        
        ArrayManager: 0=最旧, -1=最新
        MQL4: 0=最新, 越大=越老
        
        转换公式: mql4_index = total_bars - 1 - am_index
        """
        return total_bars - 1 - am_index

    def get_am_index(self, mql4_index: int, total_bars: int) -> int:
        """
        将 MQL4 索引转换为 ArrayManager 索引
        """
        return total_bars - 1 - mql4_index