from typing import List, Dict, Any
from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
import numpy as np
from datetime import datetime


class BollReversalCrossStrategy(CtaTemplate):
    """
    基于长周期布林带触边并在短周期内等待 EMA(5) 与 EMA(30) 金叉/死叉作为反转入场。
    - 长周期（默认日线）用于 Bollinger 判断（触上轨 => 触发看空候选；触下轨 => 触发看多候选）
    - 在随后的 N 个长周期内（可调），若短周期 EMA5 与 EMA30 出现相应交叉，则开仓。
    - 默认短周期：30分钟
    可配置项见 __init__ 中的参数声明部分。
    """

    author = "ChatGPT"

    # ---------------------------------------------------------------------
    # 参数（外部可配置）
    # ---------------------------------------------------------------------
    parameters = [
        "long_kline",         # 长周期标识 (str)，支持 'W','D','4H','1H'（映射为分钟）
        "short_kline",        # 短周期标识 (str)，支持 '1H','30m','15m','5m'
        "boll_n",             # Bollinger 窗口
        "boll_dev",           # Bollinger 偏差倍数
        "ema_short_n",        # 短周期 EMA 快 (默认5)
        "ema_long_n",         # 短周期 EMA 慢 (默认30)
        "candidate_long_bars",# 触发后在多少个长周期内有效（默认4）
        "order_volume",       # 每次下单手数
    ]

    # 默认值
    long_kline = "D"
    short_kline = "30m"
    boll_n = 20
    boll_dev = 2.0
    ema_short_n = 5
    ema_long_n = 30
    candidate_long_bars = 4
    order_volume = 1

    variables = [
        "long_minutes", "short_minutes",
        "pending_windows",   # 存放当前所有候选窗口
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting: Dict[str, Any]):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 将可读周期映射为分钟数（用于 BarGenerator）
        self._long_map = {"W": 60 * 24 * 7, "D": 60 * 24, "4H": 4 * 60, "1H": 60}
        self._short_map = {"1H": 60, "30m": 30, "15m": 15, "5m": 5}

        # 将用户选择的周期转成分钟
        self.long_minutes = self._long_map.get(self.long_kline, 60 * 24)  # 默认日线
        self.short_minutes = self._short_map.get(self.short_kline, 30)

        # BarGenerator & ArrayManager (分别为短、长周期)
        # 注意：BarGenerator 参数名/签名在不同 vn.py 版本略有差别；我们采用常见回调模式：
        # bg = BarGenerator(on_bar, on_xmin_bar, window_minutes)
        self.bg_short = BarGenerator(self.on_bar, self.on_short_bar, self.short_minutes)
        self.bg_long = BarGenerator(self.on_bar, self.on_long_bar, self.long_minutes)

        self.am_short = ArrayManager()  # 用于短周期指标计算
        self.am_long = ArrayManager()   # 用于长周期 boll 等计算

        # pending_windows: 列表，元素为 dict:
        # {
        #   "direction": "short" 或 "long",  # 表示候选反转方向：当长周期触上轨 => 'short'（做空）
        #   "remaining": int,                # 剩余的长周期数量
        #   "trigger_time": datetime         # 触发时间(长bar的dt)
        # }
        self.pending_windows: List[Dict[str, Any]] = []

        # 追踪短周期 ema 用于判断交叉 (保存上一周期的 ema 值)
        self._prev_ema_short = None
        self._prev_ema_long = None

        # 是否初始化完成（用于打印）
        self.inited = False

    # ---------------------------------------------------------------------
    # 辅助函数
    # ---------------------------------------------------------------------
    def _calc_boll(self, arr_close: np.ndarray):
        """
        直接用 numpy 计算 boll (mid, upper, lower)
        arr_close: numpy array (latest values)
        """
        if len(arr_close) < self.boll_n:
            return None, None, None
        window = arr_close[-self.boll_n:]
        mid = float(np.mean(window))
        std = float(np.std(window, ddof=0))
        upper = mid + self.boll_dev * std
        lower = mid - self.boll_dev * std
        return mid, upper, lower

    def _add_pending_window(self, direction: str, trigger_time: datetime):
        wd = {
            "direction": direction,
            "remaining": int(self.candidate_long_bars),
            "trigger_time": trigger_time,
        }
        self.pending_windows.append(wd)
        self.write_log(f"Added pending window: {direction} at {trigger_time}, remaining {wd['remaining']}")

    def _decay_pending_windows(self):
        # 每来一个新的长周期 bar，就把 remaining -1，删掉到期的
        new_list = []
        for wd in self.pending_windows:
            wd["remaining"] -= 1
            if wd["remaining"] > 0:
                new_list.append(wd)
            else:
                self.write_log(f"Pending window expired: {wd['direction']} triggered at {wd['trigger_time']}")
        self.pending_windows = new_list

    def _check_pending_windows_for_short_signal(self, short_ema_fast, short_ema_slow, short_bar: BarData):
        """
        在短周期 bar 到来时检查是否存在有效候选窗口，若存在且出现交叉则下单。
        逻辑：
          - 如果短周期 EMA5 从上向下穿过 EMA30（ema_fast < ema_slow 且 prev_fast >= prev_slow）
            且有 pending window direction == 'short' => 开空（short）
          - 如果短周期 EMA5 从下向上穿过 EMA30 且有 pending window direction == 'long' => 开多（buy）
        """
        if self._prev_ema_short is None or self._prev_ema_long is None:
            return

        # detect cross
        prev_fast = self._prev_ema_short
        prev_slow = self._prev_ema_long
        cur_fast = short_ema_fast
        cur_slow = short_ema_slow

        # check dead/ golden crosses
        crossed_down = (prev_fast >= prev_slow) and (cur_fast < cur_slow)
        crossed_up = (prev_fast <= prev_slow) and (cur_fast > cur_slow)

        # decide if there is any pending window matching
        for wd in list(self.pending_windows):  # copy 避免中途修改
            if wd["direction"] == "short" and crossed_down:
                # 开空
                price = short_bar.close_price
                volume = int(self.order_volume)
                self.write_log(f"OPEN SHORT signaled by EMA cross at {short_bar.datetime} price {price}")
                # self.short(price, volume)  # 如果你想用限价/市价的不同API，请调整
                try:
                    self.short(price, volume)
                except Exception as e:
                    self.write_error(f"short order error: {e}")
                # 使用后删除该窗口（避免重复）
                self.pending_windows.remove(wd)
                break
            elif wd["direction"] == "long" and crossed_up:
                # 开多
                price = short_bar.close_price
                volume = int(self.order_volume)
                self.write_log(f"OPEN LONG signaled by EMA cross at {short_bar.datetime} price {price}")
                try:
                    self.buy(price, volume)
                except Exception as e:
                    self.write_error(f"buy order error: {e}")
                self.pending_windows.remove(wd)
                break

    # ---------------------------------------------------------------------
    # CTA 生命周期方法（常见）
    # ---------------------------------------------------------------------
    def on_init(self):
        """
        初始化（回测/实盘启动时调用一次）
        """
        self.write_log("on_init")
        self.load_bar(10)  # 尝试加载少量历史（不同 vn.py 版本可改）
        self.put_event()

    def on_start(self):
        self.write_log("on_start")
        self.put_event()

    def on_stop(self):
        self.write_log("on_stop")
        self.put_event()

    def on_tick(self, tick: TickData):
        """
        若你的数据以 tick 为基础，需要把 tick 转成 bar 更新给 bg；
        这里不做特殊处理，直接忽略（默认使用 bar 驱动）。
        """
        pass

    def on_bar(self, bar: BarData):
        """
        收到基础级别 bar（通常是 1分钟或最小级别），交由两个 BarGenerator 生成短/长周期 bar
        """
        # 更新两个聚合器
        try:
            self.bg_short.update_bar(bar)
            self.bg_long.update_bar(bar)
        except Exception:
            # 在一些 vn.py 版本 BarGenerator 的构造或方法名不同，若报错请贴报错信息给我
            pass

    # ---------------------------------------------------------------------
    # 长周期 bar 回调（用于 Bollinger 判断 + 候选窗口管理）
    # ---------------------------------------------------------------------
    def on_long_bar(self, bar: BarData):
        """
        每生成一个长周期（例如日线）就会进来一次。
        - 计算 Bollinger（基于 close 序列）
        - 若 high >= upper => 视为触上轨，加入 short 候选窗口
        - 若 low <= lower  => 视为触下轨，加入 long 候选窗口
        - 对候选窗口进行衰减（remaining-1）
        """
        self.am_long.update_bar(bar)
        # 只有 am_long 数据充足时计算
        if not self.am_long.inited:
            return

        # 计算 boll
        arr = self.am_long.close[:]  # numpy array
        mid, upper, lower = self._calc_boll(arr)

        if upper is None:
            return

        # 触上轨（可能反转下跌 => 短期做空信号）
        if bar.high_price >= upper:
            self.write_log(f"Long bar touched UPPER Boll at {bar.datetime} (high {bar.high_price} >= {upper:.2f})")
            self._add_pending_window("short", bar.datetime)

        # 触下轨（可能反转上涨 => 短期做多信号）
        if bar.low_price <= lower:
            self.write_log(f"Long bar touched LOWER Boll at {bar.datetime} (low {bar.low_price} <= {lower:.2f})")
            self._add_pending_window("long", bar.datetime)

        # 候选窗口衰减（每来一个长周期）
        self._decay_pending_windows()

        # 发布事件
        self.put_event()

    # ---------------------------------------------------------------------
    # 短周期 bar 回调（用于 EMA 交叉检测并在 matching pending window 时下单）
    # ---------------------------------------------------------------------
    def on_short_bar(self, bar: BarData):
        """
        每生成一个短周期（例如 30m）会进来一次，
        - 更新短周期 ArrayManager，计算 EMA 快/慢
        - 判断 EMA 交叉（与上周期比较）
        - 若交叉且存在 pending window（方向匹配） => 下单
        """
        self.am_short.update_bar(bar)
        if not self.am_short.inited:
            return

        # 计算 EMA
        # ArrayManager.ema(n) 返回一个 float （假定）
        try:
            ema_fast = float(self.am_short.ema(self.ema_short_n))
            ema_slow = float(self.am_short.ema(self.ema_long_n))
        except Exception:
            # 若 ArrayManager 无 ema 接口或行为不同，可以改成 numpy 计算：
            close_arr = self.am_short.close[-max(self.ema_long_n, self.ema_short_n):]
            if len(close_arr) < self.ema_long_n:
                return
            # 简单 EMA 计算（使用 pandas 会更简洁，但此处避免依赖）
            def calc_ema(arr, n):
                alpha = 2.0 / (n + 1)
                ema = arr[0]
                for x in arr[1:]:
                    ema = alpha * x + (1 - alpha) * ema
                return ema
            ema_fast = calc_ema(close_arr[-self.ema_short_n:], self.ema_short_n)
            ema_slow = calc_ema(close_arr[-self.ema_long_n:], self.ema_long_n)

        # 检测是否与上一个短周期发生交叉
        # 如果是第一次，_prev... 可能为 None
        if self._prev_ema_short is None or self._prev_ema_long is None:
            # 仅记录并等待下一根
            self._prev_ema_short = ema_fast
            self._prev_ema_long = ema_slow
            return

        # 检查 pending windows 并在条件满足时下单
        self._check_pending_windows_for_short_signal(ema_fast, ema_slow, bar)

        # 更新 prev
        self._prev_ema_short = ema_fast
        self._prev_ema_long = ema_slow

        # 发布事件
        self.put_event()

    # ---------------------------------------------------------------------
    # 订单 / 成交 / 报单 回调（可按需扩展）
    # ---------------------------------------------------------------------
    def on_order(self, order: OrderData):
        super().on_order(order)
        self.put_event()

    def on_trade(self, trade: TradeData):
        super().on_trade(trade)
        self.write_log(f"Trade: {trade.direction} {trade.volume} @ {trade.price}")
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        super().on_stop_order(stop_order)
        self.put_event()
