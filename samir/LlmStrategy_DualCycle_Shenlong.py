# LlmStrategy_DualCycle_Shenlong.py
# 双周期通用策略框架：
# - 长周期 Shenlong 信号插件（可触发开仓或平仓）
# - 短周期 EMA/Cross 信号插件（仅在 long/short window 内开仓）
# - 支持回测和实盘统一
# - 完整 SL/TP、安全平仓处理

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, time

from vnpy_ctastrategy import CtaTemplate, BarGenerator, ArrayManager
from vnpy.trader.object import BarData, TradeData
from vnpy.trader.constant import Interval, Direction, Offset


# -------------------------
# 数据结构
# -------------------------
@dataclass
class PendingWindow:
    """
    长周期窗口信息：
    - direction: 当前窗口方向 long/short
    - start_bar: 窗口开始的长周期 Bar 计数
    - long_end: 窗口结束 Bar 计数
    - long_end_time: 窗口结束时间
    """

    direction: str
    start_bar: int
    long_end: int
    long_end_time: datetime


class PositionState:
    """内部仓位状态管理"""

    def __init__(self):
        self.direction: Optional[str] = None  # long/short/None
        self.entry_price: float = 0.0
        self.sl: float = 0.0
        self.tp: float = 0.0
        self.volume: float = 0.0


# -------------------------
# 信号策略接口
# -------------------------
class LongSignalStrategy:
    """
    长周期策略接口：
    - 返回值可为 'long'/'short'（开仓）或 'close_long'/'close_short'（平仓）或 None
    """

    def generate_window_signal(self, am: ArrayManager, bar: BarData):
        return None


class ShortSignalStrategy:
    """
    短周期策略接口：
    - 只在 long/short pending window 内触发开仓信号
    - 返回值 'long'/'short'/None
    """

    def generate_entry_signal(
        self, am: ArrayManager, bar: BarData, window_direction: str
    ):
        return None


# -------------------------
# 长周期插件示例：Shenlong
# -------------------------
class ShenlongLong(LongSignalStrategy):
    """
    Shenlong 指标复刻：
    - 可触发开仓 'long'/'short'
    - 可触发平仓 'close_long'/'close_short'
    """

    def __init__(
        self,
        sh=30,
        xma_n_3=25,
        xma_n_3_1=25,
        xma_n_2=25,
        xma_n_2_1=25,
        belt_weights_len=20,
        belt_smooth_period=90,
    ):
        self.sh = sh
        self.xma_n_3 = xma_n_3
        self.xma_n_3_1 = xma_n_3_1
        self.xma_n_2 = xma_n_2
        self.xma_n_2_1 = xma_n_2_1
        self.belt_weights_len = belt_weights_len
        self.belt_smooth_period = belt_smooth_period
        

    def generate_window_signal(self, am: ArrayManager, bar: BarData):
        """
        返回：
        - 'long' / 'short' → 新窗口触发短周期开仓
        - 'close_long' / 'close_short' → 立即平仓
        - None → 无信号
        """
        if not am.inited or len(am.close_array) < max(
            self.sh, self.xma_n_3_1 + self.xma_n_3
        ):
            return None

        highs = am.high_array[::-1]  # 0 最新
        lows = am.low_array[::-1]
        length = len(highs) - self.sh

        # Belt/XMA 计算
        belt2, belt3, belt4, slld_0, slld_8 = self._compute_belt_exact(
            length, highs, lows
        )
        xma3_1, xma2_1 = self._compute_xma_exact(length, highs, lows)

        # g_ibuf buffers
        g_ibuf_116 = 2.0 * xma3_1 - xma2_1
        g_ibuf_120 = 2.0 * xma2_1 - xma3_1

        def safe(arr, idx):
            try:
                return float(arr[idx])
            except:
                return float("nan")

        g116_0 = safe(g_ibuf_116, 0)
        g116_1 = safe(g_ibuf_116, 1)
        g120_0 = safe(g_ibuf_120, 0)
        g120_1 = safe(g_ibuf_120, 1)
        slld0_0 = safe(slld_0, 0)
        slld8_0 = safe(slld_8, 0)
        low_0, low_1 = lows[0], lows[1]
        high_0, high_1 = highs[0], highs[1]

        # 开仓条件
        condition_buy = (
            g116_1 < low_1
            and g116_0 > low_0
            and (
                (g120_0 > slld0_0 and g116_0 > slld8_0)
                or (g120_0 < slld0_0 and g116_0 > slld8_0)
            )
        )
        condition_sell = (
            high_1 < g120_1
            and high_0 > g120_0
            and (
                (g120_0 < slld0_0 and g116_0 < slld8_0)
                or (g120_0 < slld0_0 and g116_0 > slld8_0)
            )
        )

        # 平仓条件
        condition_close_buy = (
            high_1 < g120_1
            and high_0 > g120_0
            and (
                (g120_0 > slld0_0 and g116_0 > slld8_0)
                or not (g120_0 < slld0_0 and g116_0 > slld8_0)
            )
        )
        condition_close_sell = (
            g116_1 < low_1
            and g116_0 > low_0
            and (
                (g120_0 < slld0_0 and g116_0 < slld8_0)
                or not (g120_0 < slld0_0 and g116_0 > slld8_0)
            )
        )

        if condition_buy:
            return "long"
        elif condition_sell:
            return "short"
        elif condition_close_buy:
            return "close_long"
        elif condition_close_sell:
            return "close_short"
        return None

    # -------------------------
    # Belt/XMA 计算（复刻 MQL4）
    # -------------------------
    def _compute_belt_exact(self, length, highs, lows):
        n = self.belt_weights_len + 1
        if length < n:
            return tuple([[float("nan")] * length for _ in range(5)])
        belt0 = [0.0] * length
        belt1 = [0.0] * length
        belt2 = [0.0] * length
        belt3 = [0.0] * length
        belt4 = [0.0] * length
        slld_0 = [0.0] * length
        slld_8 = [0.0] * length
        weight_sum = sum(range(1, n + 1))
        for i in range(length - 1, -1, -1):
            if i + self.belt_weights_len >= len(highs):
                continue
            sum_high = 0.0
            sum_low = 0.0
            for w in range(n):
                weight = self.belt_weights_len - w
                sum_high += weight * highs[i + w]
                sum_low += weight * lows[i + w]
            belt0[i] = sum_high / weight_sum
            belt1[i] = sum_low / weight_sum
        for i in range(length - 2, -1, -1):
            belt2[i] = (2 * belt0[i] + (self.belt_smooth_period - 1) * belt2[i + 1]) / (
                self.belt_smooth_period + 1
            )
            belt3[i] = (2 * belt1[i] + (self.belt_smooth_period - 1) * belt3[i + 1]) / (
                self.belt_smooth_period + 1
            )
        belt4 = [b2 - b3 for b2, b3 in zip(belt2, belt3)]
        slld_0 = [b2 + 2 * b4 for b2, b4 in zip(belt2, belt4)]
        slld_8 = [b3 - 2 * b4 for b3, b4 in zip(belt3, belt4)]
        return belt2, belt3, belt4, slld_0, slld_8

    def _compute_centered_ma_mql4(self, length, data, window):
        """复刻 MQL4 中心化 MA"""
        result = [0.0] * len(data)
        half = (window - 1) // 2
        for i in range(length, -1, -1):
            if i >= half:
                result[i] = sum(data[i - half : i + half + 1]) / window
            else:
                result[i] = sum(data[0 : i + half + 1]) / window
        return result

    def _compute_xma_exact(self, length, highs, lows):
        xma3_0 = self._compute_centered_ma_mql4(length, lows, self.xma_n_3)
        xma3_1 = self._compute_centered_ma_mql4(length, xma3_0, self.xma_n_3_1)
        xma2_0 = self._compute_centered_ma_mql4(length, highs, self.xma_n_2)
        xma2_1 = self._compute_centered_ma_mql4(length, xma2_0, self.xma_n_2_1)
        return xma3_1, xma2_1


# -------------------------
# 短周期策略示例：EMA Cross
# -------------------------
class EMA_CrossShort(ShortSignalStrategy):
    """短周期开仓策略示例"""

    def __init__(self, fast=5, slow=30):
        self.fast = fast
        self.slow = slow

    def generate_entry_signal(self, am, bar, window_direction):
        if not am.inited:
            return None
        fast = am.ema(self.fast)
        slow = am.ema(self.slow)
        if window_direction == "long":
            if fast[-2] < slow[-2] and fast[-1] > slow[-1]:
                return "long"
        elif window_direction == "short":
            if fast[-2] > slow[-2] and fast[-1] < slow[-1]:
                return "short"
        return None


# -------------------------
# 核心策略类
# -------------------------
class LlmStrategy(CtaTemplate):
    author = "ChatGPT"

    long_kline = "D"
    short_kline = "30m"
    signal_window = 4
    atr_window = 14
    sl_multiplier = 1.5
    tp_multiplier = 4.0
    max_trades_per_window = 1
    trade_volume = 1

    parameters = [
        "long_kline",
        "short_kline",
        "signal_window",
        "atr_window",
        "sl_multiplier",
        "tp_multiplier",
        "max_trades_per_window",
        "trade_volume",
    ]
    variables = ["long_bar_count"]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 状态
        self.pos_state = PositionState()
        self._pending_entry: Optional[dict] = None
        self._pending_close: Optional[dict] = None
        self.pending_windows: Dict[str, PendingWindow] = {}
        self.trades_taken_in_window: Dict[str, int] = {"long": 0, "short": 0}
        self.long_bar_count: int = 0

        # 周期映射
        self._long_map = {"D": 60 * 24, "4H": 4 * 60, "1H": 60}
        self._short_map = {"1H": 60, "30m": 30, "15m": 15, "5m": 5}
        self.long_minutes = self._long_map.get(self.long_kline, 60 * 24)
        self.short_minutes = self._short_map.get(self.short_kline, 30)

        # BarGenerator 初始化
        if self.long_kline == "D":
            self.bg_long = BarGenerator(
                self.on_bar,
                window=1,
                on_window_bar=self.on_long_bar,
                interval=Interval.DAILY,
                daily_end=time(0, 0),
            )
        else:
            self.bg_long = BarGenerator(
                self.on_bar,
                window=self.long_minutes,
                on_window_bar=self.on_long_bar,
                interval=Interval.MINUTE,
            )
        self.bg_short = BarGenerator(
            self.on_bar,
            window=self.short_minutes,
            on_window_bar=self.on_short_bar,
            interval=Interval.MINUTE,
        )

        # ArrayManager
        self.am_long = ArrayManager(100)
        self.am_short = ArrayManager(100)

        # 默认插件
        self.long_signal_strategy: LongSignalStrategy = ShenlongLong()
        self.short_signal_strategy: ShortSignalStrategy = EMA_CrossShort()

    # -------------------------
    # 主 on_bar
    # -------------------------
    def on_bar(self, bar: BarData):
        """接收每根分钟/日线"""
        self.check_exit_conditions(bar)
        self.bg_long.update_bar(bar)
        self.bg_short.update_bar(bar)

    # -------------------------
    # 长周期处理
    # -------------------------
    def on_long_bar(self, bar: BarData):
        self.long_bar_count += 1
        self.am_long.update_bar(bar)
        if not self.am_long.inited:
            return

        signal = self.long_signal_strategy.generate_window_signal(self.am_long, bar)

        # 平仓信号优先
        if signal == "close_long" and self.pos_state.direction == "long":
            self.close_position(bar.close, "LongWindow Close triggered")
        elif signal == "close_short" and self.pos_state.direction == "short":
            self.close_position(bar.close, "ShortWindow Close triggered")
        # 新窗口开仓
        elif signal in ["long", "short"]:
            self.pending_windows[signal] = PendingWindow(
                direction=signal,
                start_bar=self.long_bar_count,
                long_end=self.long_bar_count + self.signal_window,
                long_end_time=bar.datetime + timedelta(days=1),
            )
            self.trades_taken_in_window[signal] = 0
            opposite = "long" if signal == "short" else "short"
            self.pending_windows.pop(opposite, None)
            # 立即反转平仓
            if signal == "long" and (
                self.pos_state.direction == "short" or getattr(self, "pos", 0) < 0
            ):
                self.close_position(bar.close, "Reversed by long-window")
            elif signal == "short" and (
                self.pos_state.direction == "long" or getattr(self, "pos", 0) > 0
            ):
                self.close_position(bar.close, "Reversed by short-window")

        # 清理过期窗口
        expired = []
        for side, w in self.pending_windows.items():
            if self.long_bar_count >= w.long_end or bar.datetime >= w.long_end_time:
                expired.append(side)
        for k in expired:
            del self.pending_windows[k]

    # -------------------------
    # 短周期开仓
    # -------------------------
    def on_short_bar(self, bar: BarData):
        self.am_short.update_bar(bar)
        if not self.am_short.inited:
            return
        atr = self.am_short.atr(self.atr_window)
        for side in list(self.pending_windows.keys()):
            if self.trades_taken_in_window[side] >= self.max_trades_per_window:
                continue
            entry_signal = self.short_signal_strategy.generate_entry_signal(
                self.am_short, bar, side
            )
            if entry_signal == "long":
                self.open_long(
                    bar.close,
                    self.trade_volume,
                    bar.close - atr * self.sl_multiplier,
                    bar.close + atr * self.tp_multiplier,
                )
                self.trades_taken_in_window[side] += 1
            elif entry_signal == "short":
                self.open_short(
                    bar.close,
                    self.trade_volume,
                    bar.close + atr * self.sl_multiplier,
                    bar.close - atr * self.tp_multiplier,
                )
                self.trades_taken_in_window[side] += 1
        self.check_signal_exit(bar)

    # -------------------------
    # 开仓/平仓接口
    # -------------------------
    def open_long(self, price, volume, sl, tp):
        try:
            orderid = self.buy(price, volume)
        except:
            orderid = None
        self._pending_entry = {
            "side": "long",
            "price": price,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "orderid": orderid,
        }
        self.write_log(f"[open_long] price={price} vol={volume} orderid={orderid}")

    def open_short(self, price, volume, sl, tp):
        try:
            orderid = self.sell(price, volume)
        except:
            orderid = None
        self._pending_entry = {
            "side": "short",
            "price": price,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "orderid": orderid,
        }
        self.write_log(f"[open_short] price={price} vol={volume} orderid={orderid}")

    def close_position(self, price, reason):
        net_pos = getattr(self, "pos", None)
        if net_pos is not None:
            vol = abs(net_pos)
            dirn = "long" if net_pos > 0 else ("short" if net_pos < 0 else None)
        else:
            vol = int(self.pos_state.volume)
            dirn = self.pos_state.direction
        if vol <= 0 or dirn is None:
            self.pos_state = PositionState()
            return
        try:
            if dirn == "long":
                orderid = self.sell(price, vol)
            else:
                orderid = self.buy(price, vol)
        except:
            orderid = None
        self._pending_close = {
            "side": dirn,
            "price": price,
            "volume": vol,
            "orderid": orderid,
            "reason": reason,
        }
        self.write_log(
            f"[close_position] side={dirn} price={price} vol={vol} orderid={orderid} reason={reason}"
        )

    # -------------------------
    # SL/TP 检查
    # -------------------------
    def check_exit_conditions(self, bar: BarData):
        net_pos = getattr(self, "pos", None)
        if (net_pos is None or net_pos == 0) and self.pos_state.direction is None:
            return
        sl = self.pos_state.sl
        tp = self.pos_state.tp
        if self.pos_state.direction == "long":
            if sl and bar.low <= sl:
                self.close_position(sl, "SL_LONG hit")
            elif tp and bar.high >= tp:
                self.close_position(tp, "TP_LONG hit")
        elif self.pos_state.direction == "short":
            if sl and bar.high >= sl:
                self.close_position(sl, "SL_SHORT hit")
            elif tp and bar.low <= tp:
                self.close_position(tp, "TP_SHORT hit")

    # -------------------------
    # 插件接口：短周期信号触发平仓
    # -------------------------
    def check_signal_exit(self, bar: BarData):
        # 可由 short_signal_strategy 或其他插件实现反向平仓逻辑
        pass

    # -------------------------
    # 成交同步
    # -------------------------
    def on_trade(self, trade: TradeData):
        try:
            if trade.offset == Offset.OPEN:
                pending = self._pending_entry or {}
                if pending and pending.get("orderid") == trade.orderid:
                    side = pending["side"]
                    sl = pending.get("sl")
                    tp = pending.get("tp")
                    self.pos_state.direction = side
                    self.pos_state.entry_price = trade.price
                    self.pos_state.volume = trade.volume
                    self.pos_state.sl = sl
                    self.pos_state.tp = tp
                    self._pending_entry = None
            elif trade.offset == Offset.CLOSE:
                if (
                    self.pos_state.direction == "long"
                    and trade.direction == Direction.SHORT
                ):
                    self.pos_state.volume -= trade.volume
                    if self.pos_state.volume <= 0:
                        self.pos_state = PositionState()
                elif (
                    self.pos_state.direction == "short"
                    and trade.direction == Direction.LONG
                ):
                    self.pos_state.volume -= trade.volume
                    if self.pos_state.volume <= 0:
                        self.pos_state = PositionState()
                pending_close = self._pending_close or {}
                if pending_close and pending_close.get("orderid") == trade.orderid:
                    self._pending_close = None
        except Exception as e:
            self.write_error(f"on_trade error: {e}")

    def on_order(self, order):
        pass

    def on_stop_order(self, stop_order):
        pass
