# 主程序入口
import logging

from config.settings import Settings
from core.strategies import ProfessionalPinBarStrategy
from utils.scheduler import SchedulerManager
from utils.notifiers import ServerChanNotifier, WechatWorkNotifier
from core.database import DatabaseManager


def main():
    # 初始化组件
    strategy = ProfessionalPinBarStrategy()
    notifier = WechatWorkNotifier()
    db = DatabaseManager()

    # 启动定时任务
    SchedulerManager(strategy, notifier, db).start()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(Settings.LOG_PATH),
            logging.StreamHandler()
        ]
    )
    main()
