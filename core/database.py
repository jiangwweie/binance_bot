import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config.settings import Settings
import threading


class DatabaseManager:
    _instance_lock = threading.Lock()
    _pool = ThreadPoolExecutor(max_workers=5)  # 根据CPU核心数调整

    def __new__(cls):
        """单例模式确保线程池唯一"""
        if not hasattr(cls, "_instance"):
            with cls._instance_lock:
                if not hasattr(cls, "_instance"):
                    cls._instance = super().__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """初始化数据库连接（仅主线程执行）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 创建信号表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    symbol TEXT,
                    timeframe TEXT,
                    signal_type TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size REAL,
                    leverage INTEGER,
                    confidence REAL
                )
            ''')
            # 创建日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    level TEXT,
                    message TEXT
                )
            ''')
            conn.commit()

    @staticmethod
    def _get_connection():
        """获取新的数据库连接（线程安全）"""
        return sqlite3.connect(Settings.DB_PATH, check_same_thread=False)

    def log_signal(self, signal):
        """异步记录交易信号（保持参数不变）"""
        self._pool.submit(self._log_signal_impl, signal)

    def _log_signal_impl(self, signal):
        """实际的信号记录实现"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO signals VALUES (
                        NULL,?,?,?,?,?,?,?,?,?,?
                    )
                ''', (
                    datetime.now(),
                    signal.symbol,
                    signal.timeframe,
                    signal.signal_type,
                    signal.entry_price,
                    signal.stop_loss,
                    signal.take_profit,
                    signal.position_size,
                    signal.leverage,
                    signal.confidence
                ))
                conn.commit()
        except Exception as e:
            self.log_message("ERROR", f"记录信号失败: {str(e)}")

    def log_message(self, level, message):
        """异步记录日志（保持参数不变）"""
        self._pool.submit(self._log_message_impl, level, message)

    def _log_message_impl(self, level, message):
        """实际的日志记录实现"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO logs VALUES (
                        NULL,?,?,?
                    )
                ''', (datetime.now(), level, message))
                conn.commit()
        except Exception as e:
            print(f"日志记录失败: {str(e)}")

    def __del__(self):
        """清理资源"""
        self._pool.shutdown(wait=True)