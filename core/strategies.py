# 交易策略
# core/strategies.py
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import talib  # 技术分析库，用于计算技术指标

from core.database import DatabaseManager  # 数据库管理模块
from core.exchange import BinanceFutureClient  # 交易所接口
from core.patterns import CandlePatternDetector  # K线形态检测模块
from core.risk import RiskManager  # 风险管理模块


@dataclass
class TradingSignal:
    """交易信号数据结构"""
    symbol: str  # 交易对
    timeframe: str  # 时间周期
    direction: str  # 交易方向 LONG/SHORT
    entry_price: float  # 入场价格
    stop_loss: float  # 止损价
    take_profit: float  # 止盈价
    position_size: float  # 仓位大小
    leverage: int  # 杠杆倍数
    confidence: float = 1.0  # 信号置信度（0-1）
    timestamp: str = datetime.now().isoformat()  # 信号生成时间


class BaseStrategy:
    """策略基类（抽象类）"""

    def __init__(self):
        # 初始化交易所客户端、形态检测器、风险管理器和数据库
        self.exchange = BinanceFutureClient()
        self.pattern_detector = CandlePatternDetector()
        self.risk_manager = RiskManager()
        self.db = DatabaseManager()

    def analyze(self, symbol: str, timeframe: str) -> Optional[TradingSignal]:
        """分析主方法（需子类实现）"""
        raise NotImplementedError


class ProfessionalPinBarStrategy(BaseStrategy):
    """专业版Pin Bar策略 - 结合吞没形态和高级别趋势分析"""

    def __init__(self):
        super().__init__()
        # 定义时间框架映射关系（当前周期→更高级别周期）
        self.higher_tf_map = {
            '5m': '15m',
            '15m': '4h',
            '1h': '4h',
            '4h': '1d',
            '1d': '1W'
        }

    def analyze(self, symbol: str, timeframe: str) -> Optional[TradingSignal]:
        """策略核心分析方法"""
        try:
            # 获取当前时间框架数据
            current_data = self._get_ohlcv(symbol, timeframe)
            # 数据不足时返回
            if len(current_data) < 50:
                return None

            # 获取高级别趋势（用于信号过滤）
            higher_tf = self.higher_tf_map.get(timeframe)
            trend = self._get_trend(symbol, higher_tf) if higher_tf else "NEUTRAL"

            # 检测最新3根K线的形态
            signals = []
            for i in range(-3, 0):  # 遍历最新三根K线
                current_candle = self._parse_candle(current_data[i])
                prev_candle = self._parse_candle(current_data[i - 1]) if i > -3 else None

                # 检测Pin Bar形态
                if pin_signal := self.pattern_detector.detect_pinbar(current_candle):
                    signals.append(self._create_signal(
                        symbol, timeframe, pin_signal, current_candle, trend
                    ))

                # 检测吞没形态（需要前一根K线）
                if prev_candle and (engulf_signal := self.pattern_detector.detect_engulfing(current_candle, prev_candle)):
                    signals.append(self._create_signal(
                        symbol, timeframe, engulf_signal, current_candle, trend
                    ))

            # 过滤有效信号并选择置信度最高的
            valid_signals = [s for s in signals if s and self._filter_signal(s, trend)]
            if not valid_signals:
                return None

            # 选择置信度最高的信号
            best_signal = max(valid_signals, key=lambda x: x.confidence)
            # 记录信号到数据库
            self.db.log_signal(best_signal)
            return best_signal

        except Exception as e:
            logging.error(f"策略分析异常: {str(e)}")
            return None

    def _get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        """获取K线数据（原始格式）"""
        return self.exchange.get_ohlcv(symbol, timeframe, limit)

    @staticmethod
    def _parse_candle(ohlcv: list) -> dict:
        """解析交易所返回的K线数据为字典格式"""
        return {
            'timestamp': ohlcv[0],  # 时间戳
            'open': ohlcv[1],  # 开盘价
            'high': ohlcv[2],  # 最高价
            'low': ohlcv[3],  # 最低价
            'close': ohlcv[4],  # 收盘价
            'volume': ohlcv[5]  # 成交量
        }

    def _get_trend(self, symbol: str, timeframe: str) -> str:
        """判断高级别趋势：双EMA策略"""
        data = self._get_ohlcv(symbol, timeframe, 200)
        # 提取收盘价数据
        closes = np.array([c[4] for c in data], dtype=np.float64)

        # 计算50日和200日指数移动平均线
        ema50 = talib.EMA(closes, timeperiod=50)[-1]
        ema200 = talib.EMA(closes, timeperiod=200)[-1]

        # 带过滤阈值的趋势判断（防止假信号）
        if ema50 > ema200 * 1.02:  # 金叉且差距>2%
            return "BULLISH"
        elif ema50 < ema200 * 0.98:  # 死叉且差距>2%
            return "BEARISH"
        return "NEUTRAL"  # 震荡区间

    def _create_signal(self, symbol: str, timeframe: str,
                       direction: str, candle: dict, trend: str) -> Optional[TradingSignal]:
        """根据形态检测结果创建交易信号"""
        # 趋势过滤：只保留顺势或中性趋势中的信号
        if trend not in ["NEUTRAL", direction.upper()]:
            logging.debug(f"趋势不符过滤: {direction} vs {trend}")
            return None

        # 计算平均真实波动范围（ATR）用于仓位和止损计算
        atr = self._calculate_atr(symbol, timeframe)

        # 风险管理：计算仓位大小和杠杆
        position_size, leverage = self.risk_manager.calculate_position(
            timeframe, self._calculate_confidence(candle, atr)
        )

        # 构建交易信号对象
        return TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction.upper(),
            entry_price=candle['close'],
            stop_loss=self._calculate_stop_loss(candle, direction, atr),
            take_profit=self._calculate_take_profit(candle, direction, atr),
            position_size=position_size,
            leverage=leverage,
            confidence=self._calculate_confidence(candle, atr)
        )

    def _calculate_atr(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """计算平均真实波动范围（ATR）"""
        data = self._get_ohlcv(symbol, timeframe, 100)
        high = np.array([c[2] for c in data], dtype=np.float64)
        low = np.array([c[3] for c in data], dtype=np.float64)
        close = np.array([c[4] for c in data], dtype=np.float64)
        # 使用TALIB计算ATR
        return talib.ATR(high, low, close, timeperiod=period)[-1]

    @staticmethod
    def _calculate_stop_loss(candle: dict, direction: str, atr: float) -> float:
        """计算止损价格"""
        if direction.upper() == 'BULLISH':  # 多头：止损设在最低点下方0.5倍ATR
            return candle['low'] - 0.5 * atr
        return candle['high'] + 0.5 * atr  # 空头：止损设在最高点上方0.5倍ATR

    @staticmethod
    def _calculate_take_profit(candle: dict, direction: str, atr: float) -> float:
        """计算止盈价格（风险回报比3:1）"""
        risk_reward_ratio = 3.0
        if direction.upper() == 'BULLISH':  # 多头：入场价+3倍ATR
            return candle['close'] + risk_reward_ratio * atr
        return candle['close'] - risk_reward_ratio * atr  # 空头：入场价-3倍ATR

    @staticmethod
    def _calculate_confidence(candle: dict, atr: float) -> float:
        """计算信号置信度（基于实体/影线比例）"""
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']

        # 实体占比越高置信度越高
        confidence = (body_size / candle_range) if candle_range != 0 else 0
        # 限制在0.3-0.9之间（避免极端值）
        return min(max(confidence, 0.3), 0.9)

    def _filter_signal(self, signal: TradingSignal, trend: str) -> bool:
        """信号过滤器"""
        # 趋势一致性过滤（重要）
        if trend not in ["NEUTRAL", signal.direction.upper()]:
            return False

        # （注释掉的）波动率过滤示例：需要时启用
        # min_atr_ratio = 0.005
        # current_price = signal.entry_price
        # atr = self._calculate_atr(signal.symbol, signal.timeframe)
        # if (atr / current_price) < min_atr_ratio:
        #     return False

        return True  # 通过所有过滤条件
