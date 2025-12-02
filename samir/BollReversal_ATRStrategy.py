from typing import List, Dict, Any
from datetime import datetime, timedelta

import numpy as np
from vnpy_ctastrategy import (
    CtaTemplate,
    BarData,
    TradeData,
    OrderData,
    StopOrder,
    ArrayManager,
    BarGenerator,
)


class BollReversalAtrStrategy(CtaTemplate):
    """
    长周期布林带触边 -> 在接下来 N 根长周期内等待短周期 EMA5/EMA30 交叉确认；
    开仓后使用短周期 ATR 做止损（stop = 1.5 * ATR），止盈为 4 * ATR。
    每个窗口允许开仓次数可配置 (allow_trades_per_window)。
    ATR 使用短周期数据（默认 short_kline）。
    """

    author = "ChatGPT"

    # ---------------- 参数（可调） ----------------
    # 周期选择（字符串）
    long_kline = "D"        # 可: "W","D","4H","1H"
    short_kline = "30m"     # 可: "1H","30m","15m","5m"

    # Bollinger (长周期)
    boll_n = 20
    boll_dev = 2.0

    # EMA (短周期)
    ema_fast_n = 5
    ema_slow_n = 30

    # 窗口与开仓次数
    candidate_long_bars = 4
    allow_trades_per_window = 1

    # ATR 止损 / 止盈（按你已选）
    atr_window = 14
    stop_atr_mult = 1.5
    take_atr_mult = 4.0

    # 下单手数
    order_volume = 1

    parameters = [
        "long_kline", "short_kline",
        "boll_n", "boll_dev",
        "ema_fast_n", "ema_slow_n",
        "candidate_long_bars", "allow_trades_per_window",
        "atr_window", "stop_atr_mult", "take_atr_mult",
        "order_volume",
    ]

    # ---------------- 内部变量 ----------------
    variables = [
        "long_minutes", "short_minutes",
    ]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: Dict[str, Any]):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 周期映射（分钟）
        self._long_map = {"W": 60 * 24 * 7, "D": 60 * 24, "4H": 4 * 60, "1H": 60}
        self._short_map = {"1H": 60, "30m": 30, "15m": 15, "5m": 5}

        self.long_minutes = self._long_map.get(self.long_kline, 60 * 24)
        self.short_minutes = self._short_map.get(self.short_kline, 30)

        # BarGenerator：把基础 bar 聚合成短/长周期 bar
        # （构造签名在不同版本可能不同）
        self.bg_short = BarGenerator(self.on_bar, self.on_short_bar, self.short_minutes)
        self.bg_long = BarGenerator(self.on_bar, self.on_long_bar, self.long_minutes)

        # ArrayManager：用于计算指标
        # 给足够长度用于计算 EMA/ATR/BOLL
        self.am_short = ArrayManager(size=200)
        self.am_long = ArrayManager(size=200)

        # pending windows: 每个元素是 dict:
        # {
        #   "direction": "long" or "short",
        #   "start": datetime (long bar start),
        #   "end": datetime (long bar end),
        #   "remaining": int (剩余长周期数量),
        #   "used": int (已触发开仓次数)
        # }
        self.pending_windows: List[Dict[str, Any]] = []

        # 存储前一根短周期 EMA 值用于交叉检测（float）
        self.prev_ema_fast = None
        self.prev_ema_slow = None

        # 记录持仓状态（可选扩展）
        # self.pos = 0  # 如果想基于持仓限制开仓需使用

    # ---------------- 生命周期方法 ----------------
    def on_init(self):
        """初始化时加载历史数据"""
        self.write_log("on_init")
        # 加载足够多历史 bar，让 am inited
        try:
            self.load_bar(200)
        except Exception:
            # 有些 vn.py 版本没有 load_bar，需要用户保证回测时有历史
            pass
        self.put_event()

    def on_start(self):
        self.write_log("on_start")
        self.put_event()

    def on_stop(self):
        self.write_log("on_stop")
        self.put_event()

    def on_tick(self, tick):
        # 不处理 tick（默认用 bar 驱动）
        pass

    def on_bar(self, bar: BarData):
        """
        基础 bar 入口。把 bar 传给两个 BarGenerator 以产生短/长周期 bar。
        """
        try:
            self.bg_short.update_bar(bar)
            self.bg_long.update_bar(bar)
        except Exception:
            # 不同版本接口可能不同，若报错请贴出异常
            pass

    # ---------------- 长周期处理：布林带触边，生成窗口 ----------------
    def on_long_bar(self, bar: BarData):
        """
        每根长周期 bar（例如日线）到来就做 Boll 判断。
        我们把每根长 bar 对应的时间区间定义为：
            start = bar.datetime - timedelta(minutes=self.long_minutes)
            end   = bar.datetime
        这样短周期 bar 的 datetime 落在 (start, end] 就算属于该长周期。
        """
        self.am_long.update_bar(bar)
        if not self.am_long.inited:
            return

        # 计算布林带（使用 ArrayManager 的方法）
        try:
            mid = self.am_long.sma(self.boll_n)
            std = self.am_long.std(self.boll_n)
        except Exception:
            # 如果 ArrayManager 没有这些方法，使用 numpy 计算
            closes = self.am_long.close[-self.boll_n:]
            if len(closes) < self.boll_n:
                return
            mid = float(np.mean(closes))
            std = float(np.std(closes, ddof=0))

        upper = mid + self.boll_dev * std
        lower = mid - self.boll_dev * std

        # 计算当前 long bar 的区间（start, end]
        long_end = bar.datetime
        long_start = long_end - timedelta(minutes=self.long_minutes)

        touched = None
        if bar.high_price >= upper:
            touched = "short"   # 触上轨，后续期望短周期死叉 -> 做空
        elif bar.low_price <= lower:
            touched = "long"    # 触下轨，后续期望短周期金叉 -> 做多

        if touched:
            win = {
                "direction": touched,
                "start": long_start,
                "end": long_end,
                "remaining": int(self.candidate_long_bars),
                "used": 0
            }
            self.pending_windows.append(win)
            self.write_log(f"[WINDOW ADDED] dir={touched} start={long_start} end={long_end} remain={win['remaining']}")

        # 每来一根长周期，所有窗口的 remaining -1
        for w in self.pending_windows:
            w["remaining"] -= 1

        # 删除过期窗口（remaining <= 0）
        before = len(self.pending_windows)
        self.pending_windows = [w for w in self.pending_windows if w["remaining"] > 0]
        after = len(self.pending_windows)
        if before != after:
            self.write_log(f"Expired windows removed: {before - after}")

        self.put_event()

    # ---------------- 短周期处理：EMA 交叉检测 + 窗口匹配 + 下单 ----------------
    def on_short_bar(self, bar: BarData):
        """
        短周期到来时：
        1) 更新短周期 am
        2) 计算 EMA fast/slow, ATR（短周期）
        3) 通过 prev_ema_* 检测穿越（避免未完成bar重绘问题）
        4) 如果发生交叉，遍历 pending_windows，找出其中 start<=bar.datetime<=end+window_extension 并且 remaining>0
           注意：我们用 long window 的 start/end 定义窗口范围；同时允许窗口在其后续的 remaining 周期内触发（remaining 管理）
        """
        self.am_short.update_bar(bar)
        if not self.am_short.inited:
            return

        # 计算短周期 EMA 和 ATR
        try:
            ema_fast = float(self.am_short.ema(self.ema_fast_n))
            ema_slow = float(self.am_short.ema(self.ema_slow_n))
            atr = float(self.am_short.atr(self.atr_window))
        except Exception:
            # 如果 am 没有这些函数（极少见），可以退回自实现
            closes = self.am_short.close
            if len(closes) < max(self.ema_slow_n, self.atr_window):
                return
            ema_fast = self._calc_ema_manual(closes, self.ema_fast_n)
            ema_slow = self._calc_ema_manual(closes, self.ema_slow_n)
            atr = self._calc_atr_manual(closes, self.atr_window)

        # 如果还没有 prev 值，先记录并返回（需要两根 short bar 才能检测穿越）
        if self.prev_ema_fast is None or self.prev_ema_slow is None:
            self.prev_ema_fast = ema_fast
            self.prev_ema_slow = ema_slow
            return

        # 判定交叉（仅使用上两根短周期 EMA 值）
        crossed_up = (self.prev_ema_fast <= self.prev_ema_slow) and (ema_fast > ema_slow)
        crossed_down = (self.prev_ema_fast >= self.prev_ema_slow) and (ema_fast < ema_slow)

        # 更新 prev 值（放在后面以避免重复触发同一 bar）
        self.prev_ema_fast = ema_fast
        self.prev_ema_slow = ema_slow

        # 如果没有任何候选窗口，直接返回
        if len(self.pending_windows) == 0:
            return

        # 遍历 windows：我们允许在窗口存在期间任何短周期 bar 上触发（窗口的时间边界由 long bar 的 start/end + remaining 管理）
        for w in list(self.pending_windows):  # copy，方便在循环中修改
            # 跳过已用完次数或过期的窗口
            if w["used"] >= self.allow_trades_per_window or w["remaining"] <= 0:
                continue

            # 判定当前短 bar 是否属于该窗口时间范围
            # 这里认为：只要短 bar.datetime > w["start"] 且 short bar.datetime <= w["end"] + (candidate_long_bars-remaining)*long_minutes
            # 但为简单可靠，我们允许只要 bar.datetime >= w["start"] (即在该窗口自触发时开始后) 即可，
            # 因为窗口的 remaining 管理已经确保了生命周期。
            if bar.datetime < w["start"]:
                # 还没到该窗口开始
                continue

            # match direction + cross
            if w["direction"] == "short" and crossed_down:
                # 做空
                self._open_short(bar, atr)
                w["used"] += 1
                self.write_log(f"[WINDOW USED] short window used++ -> used={w['used']}")
                # 如果达到 allow_trades_per_window, 可以继续但逻辑会阻止
                continue

            if w["direction"] == "long" and crossed_up:
                # 做多
                self._open_long(bar, atr)
                w["used"] += 1
                self.write_log(f"[WINDOW USED] long window used++ -> used={w['used']}")
                continue

        # 清理那些 used >= allow_trades_per_window 且 remaining <=0 的窗口（不过 remaining 管理在 long_bar 已做）
        self.pending_windows = [w for w in self.pending_windows if not (w["used"] >= self.allow_trades_per_window and w["remaining"] <= 0)]

        self.put_event()

    # ---------------- 下单 + 止损/止盈 ----------------
    def _open_long(self, bar: BarData, atr: float):
        """
        开多：市价开仓（使用 bar.close），随后下达止损(止损单为 stop 单) 与 止盈限价单
        止损 = entry - stop_atr_mult * ATR
        止盈 = entry + take_atr_mult * ATR
        """
        price = bar.close_price
        vol = int(self.order_volume)

        if atr is None or atr <= 0:
            self.write_error("ATR invalid for SL/TP, refusing to open")
            return

        stop_price = price - self.stop_atr_mult * atr
        take_price = price + self.take_atr_mult * atr

        # 市价开仓（注意：vn.py buy() 行为可能为限价或市价，视版本）
        try:
            self.buy(price, vol)
            self.write_log(f"[OPEN LONG] price={price} vol={vol} SL={stop_price:.2f} TP={take_price:.2f}")
        except Exception as e:
            self.write_error(f"buy order failed: {e}")
            return

        # 下止损（stop）与止盈（限价）单
        try:
            # stop=True 标记为止损单（vn.py 的接口差异，请按你版本微调）
            self.sell(stop_price, vol, stop=True)   # 止损平仓（stop单）
            self.sell(take_price, vol)               # 止盈限价平仓
        except Exception as e:
            # 若接口不同，你可能需要用 submit_order/buy/sell_stop 等 API
            self.write_error(f"placing SL/TP failed: {e}")

    def _open_short(self, bar: BarData, atr: float):
        """
        开空：市价开空，随后下止损与止盈。
        止损 = entry + stop_atr_mult * ATR
        止盈 = entry - take_atr_mult * ATR
        """
        price = bar.close_price
        vol = int(self.order_volume)

        if atr is None or atr <= 0:
            self.write_error("ATR invalid for SL/TP, refusing to open")
            return

        stop_price = price + self.stop_atr_mult * atr
        take_price = price - self.take_atr_mult * atr

        try:
            self.short(price, vol)
            self.write_log(f"[OPEN SHORT] price={price} vol={vol} SL={stop_price:.2f} TP={take_price:.2f}")
        except Exception as e:
            self.write_error(f"short order failed: {e}")
            return

        try:
            self.cover(stop_price, vol, stop=True)  # 平空止损单 (stop)
            self.cover(take_price, vol)              # 平空止盈限价单
        except Exception as e:
            self.write_error(f"placing SL/TP failed: {e}")

    # ---------------- 备用：手写 EMA / ATR（若 ArrayManager 不可用） ----------------
    def _calc_ema_manual(self, closes: List[float], n: int) -> float:
        """
        简单手写 EMA（基于 closes 的最后 n 个点），用于回退。
        注意：速度/数值精度不如专用库，但作为备选可用。
        """
        arr = list(closes[-n:])
        if len(arr) == 0:
            return 0.0
        alpha = 2.0 / (n + 1)
        ema = arr[0]
        for x in arr[1:]:
            ema = alpha * x + (1 - alpha) * ema
        return ema

    def _calc_atr_manual(self, closes: List[float], n: int) -> float:
        """
        简单 ATR 计算（只使用 closes/ highs/ lows 非常简化版）
        这里不做复杂实现，更多为备援。
        """
        # 无法只用 closes 精确计算 ATR（需要 highs/lows）。因此此函数并不可靠。
        # 我保留在代码里仅作防御性 fallback。
        return 0.0

    # ---------------- 订单/成交回调 ----------------
    def on_order(self, order: OrderData):
        # 你可以在这里处理订单状态（记录 orderid、取消对应 SL/TP 等）
        pass

    def on_trade(self, trade: TradeData):
        self.write_log(f"[TRADE] {trade.direction} price={trade.price} vol={trade.volume}")
        self.put_event()
