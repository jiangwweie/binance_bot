# 数据库管理
import sqlite3
from datetime import datetime
from config.settings import Settings


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(Settings.DB_PATH)
        self._create_tables()

    def _create_tables(self):
        """创建数据库表结构"""
        cursor = self.conn.cursor()

        # 交易信号表
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

        # 系统日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                level TEXT,
                message TEXT
            )
        ''')
        self.conn.commit()

    def log_signal(self, signal):
        """记录交易信号"""
        try:
            cursor = self.conn.cursor()
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
            self.conn.commit()
        except Exception as e:
            self.log_message("ERROR", f"记录信号失败: {str(e)}")

    def log_message(self, level, message):
        """记录系统日志"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO logs VALUES (
                    NULL,?,?,?
                )
            ''', (datetime.now(), level, message))
            self.conn.commit()
        except Exception as e:
            print(f"日志记录失败: {str(e)}")