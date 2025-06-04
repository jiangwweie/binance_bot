# 定时任务
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config.settings import Settings


class SchedulerManager:
    def __init__(self, strategy, notifier, db):
        self.strategy = strategy
        self.notifier = notifier
        self.db = db
        self.scheduler = BackgroundScheduler()

    def _add_jobs(self):
        """添加定时任务"""
        # 多时间框架任务
        for tf, config in Settings.TIMEFRAMES.items():
            self.scheduler.add_job(
                self._check_timeframe,
                trigger=CronTrigger(**config['trigger']),
                kwargs={'timeframe': tf},
                name=f'{tf}_check'
            )

        # 心跳任务
        self.scheduler.add_job(
            self._heartbeat,
            'interval',
            minutes=30,
            name='heartbeat'
        )

    def _check_timeframe(self, timeframe):
        """执行指定时间框架的信号检查"""
        self.db.log_message('INFO', f"开始检查 {timeframe} 级别信号")

        try:
            # 获取当前时间框架配置
            config = Settings.TIMEFRAMES.get(timeframe, {})
            if not config:
                self.db.log_message('WARNING', f"未找到 {timeframe} 的时间框架配置")
                return

            # 遍历所有交易对
            for symbol in Settings.SYMBOLS:
                try:
                    # 执行策略分析
                    signal = self.strategy.analyze(
                        symbol=symbol,
                        timeframe=timeframe,
                    )

                    # 处理生成的信号
                    if signal:
                        self._process_signal(signal)

                except Exception as e:
                    err_msg = f"{symbol} {timeframe} 分析失败: {str(e)}"
                    self.db.log_message('ERROR', err_msg)
                    self.notifier.send("error", err_msg)

        except Exception as e:
            self.db.log_message('CRITICAL', f"全局检查失败: {str(e)}")
            self.notifier.send("error", f"定时任务崩溃: {str(e)}")

    def _process_signal(self, signal):
        """处理交易信号"""
        # 记录到数据库
        self.db.log_signal(signal)
        # 发送通知
        msg = (f"🚨🚨🚨：{signal.symbol}\n"
               f"时间级别：{signal.timeframe}，"
               f"交易方向：{'多⬆️' if signal.direction == 'BULLISH' else '空⬇️'}\n"
               f"入场点位：{signal.entry_price}\n"
               f"止盈点位：{signal.take_profit}\n"
               f"盈利点数：{abs(signal.take_profit - signal.entry_price)}\n"
               f"止损点位：{signal.stop_loss}\n"
               f"亏损点数：{abs(signal.stop_loss - signal.entry_price)}\n")
        print(f"交易信号={msg}", )
        self.notifier.send("交易信号", msg)

        # 执行风控检查
        # if self.strategy.risk_manager.validate_signal(signal):
        #     # 触发下单逻辑
        #     self._execute_order(signal)
        # else:
        #     self.db.log_message('WARNING', f"信号未通过风控: {signal.symbol}")

    def _heartbeat(self):
        """系统心跳"""
        print("系统运行正常")
        self.db.log_message('INFO', "系统运行正常")

    def start(self):
        """启动调度器"""
        self._add_jobs()
        self.scheduler.start()
        try:
            while True:
                pass
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
            self.db.log_message('INFO', "系统正常关闭")
