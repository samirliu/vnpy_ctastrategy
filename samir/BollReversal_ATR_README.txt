✅ （1）总体设计理念：回测与实盘统一

核心思想：

回测模式

self.buy()/self.sell() 会立即成交

on_trade() 会在下一个 on_bar() 前被调用

所有委托→成交→持仓同步行为要与实盘一致

实盘模式

委托可能延迟成交

可能部分成交

成交必须依靠 on_trade() 来同步真实持仓
→ 所以策略必须 绝对不能在 on_bar 中直接修改 pos_state，必须只在 on_trade() 做最终确认

所以整个策略结构遵循：

on_bar()   ->  产生信号（只发单，不修改仓位）
on_trade() ->  真正更新仓位状态（唯一可信来源）


这就是统一版的核心。

✅ （2）长周期模块（BOLL 触发反转 Window）

长周期（D / 4H / 1H）计算：

计算 Bollinger 上轨、下轨

当收盘价触碰上轨 → 进入 short window

当触碰下轨 → 进入 long window

window 有两个持续时间：

由 long_kline 的 bar 数计算（long_end = start_bar + signal_window）

由 datetime 推算（bar.datetime + signal_window * 长周期）

产生 window 时会做：

重置 window 计数

清除另一方向 window

如果当前持仓与新信号相反，则立即执行平仓请求

※ 此时不会立即清仓，只是“发出平仓委托”，成交以后由 on_trade() 处理。

✅ （3）短周期模块（EMA 确认方向 + 开仓）

短周期（1H / 30m / 15m）负责：

步骤：

计算 fastEMA、slowEMA

当前是否 still in window？→ 由 window 字典判断

是否满足 EMA 反向穿越（确认信号）？

若满足且「本 window 内开仓次数 < 限制」→ 开仓

如果已有反向持仓 → 先发出平仓委托

开仓时同时设定 ATR 止损止盈（sl/tp）

开仓同样不直接改变持仓，只生成一个：

_pending_entry = {...}


等待 on_trade 来做最终持仓确认。

✅ （4）止损 / 止盈模块（check_exit_conditions）

短周期每根 bar 都会执行：

当前是否持多？

low <= sl → 发送多头止损平仓委托

high >= tp → 多头止盈

当前是否持空？

high >= sl → 空头止损

low <= tp → 空头止盈

系统优先使用 引擎的 self.pos（实盘 + 回测一致）

若 self.pos 无数据（某些版本回测不提供）再 fallback 到 pos_state

注意：
触发 SL/TP 时只是“发委托”，平仓动作必须靠 on_trade 确认。

✅ （5）信号反向平仓模块（check_signal_exit）

这是属于策略逻辑的“保险措施”：

如果当前是多头，但出现 快线下穿慢线 → 发平仓委托

如果当前是空头，但出现 快线上穿慢线 → 发平仓委托

同样，只是发委托，真正平仓靠 on_trade()。

✅ （6）核心 - 回测与实盘统一的 on_trade

这是整个策略的灵魂。

1. 开仓成交（Offset.OPEN）

根据 trade.direction：

LONG → 更新 pos_state.direction="long"

SHORT → 更新 pos_state.direction="short"

支持部分成交：volume 累加

记录最后一笔 entry_price（若需要可改平均价）

从 pending_entry 读取 sl/tp 写入 pos_state

完成后清除 pending_entry

2. 平仓成交（Offset.CLOSE）

如果是 closing long（SHORT fill）→ volume 减少

volume <= 0 → 清空 pos_state

同理 closing short

3. 清除 pending_close

当收到匹配 orderid 的 CLOSE 成交后，才真正移除 pending_close

✅ （7）close_position：为什么只是提交委托，不直接清仓？

因为：

实盘

订单可能延迟成交、部分成交、分批成交
必须靠成交回报来确定最终仓位

回测

即使 buy()/sell() 是“立刻成交”，vn.py 仍会调用 on_trade
我们必须保证逻辑一致。

因此 close_position 非常轻量：

发送委托
记录 pending_close
不改 pos_state


由 on_trade 统筹一切。

✅ （8）为什么这个版本对回测极度友好？

因为：

所有信号只发委托，不直接修改仓位
→ 回测与实盘行为一致

所有持仓变动只依赖 on_trade
→ 回测引擎和实盘引擎都会触发 on_trade，行为统一

支持部分成交 / 分批成交（volume 累加 / 减少）

pos_state 与 self.pos 双重保险

回测中 self.pos 通常可用

实盘中必须以 on_trade 为准

pos_state 是策略自有的仓位镜像

pending_entry / pending_close 专为回测 & 实盘同步设计

回测中可以立即清理

实盘中等成交才清理

因此这个版本达到最佳：

✔ 实盘可信
✔ 回测行为与实盘一致
✔ 回测可重复
✔ 没有重入问题
✔ 没有 double-entry or double-close
✔ 可以支持不同版本 vn.py 的差异