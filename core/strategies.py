# 交易策略
# core/strategies.py
from dataclasses import dataclass
from datetime import datetime
import logging
import talib
import numpy as np
from typing import List, Optional
from config.settings import Settings
from core.database import DatabaseManager
from core.patterns import CandlePatternDetector
from core.risk import RiskManager
from core.exchange import BinanceFutureClient


@dataclass
class TradingSignal:
    symbol: str
    timeframe: str
    direction: str  # LONG/SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    leverage: int
    confidence: float = 1.0
    timestamp: str = datetime.now().isoformat()


class BaseStrategy:
    """策略基类（抽象类）"""

    def __init__(self):
        self.exchange = BinanceFutureClient()
        self.pattern_detector = CandlePatternDetector()
        self.risk_manager = RiskManager()
        self.db = DatabaseManager()

    def analyze(self, symbol: str, timeframe: str) -> Optional[TradingSignal]:
        """分析主方法（需子类实现）"""
        raise NotImplementedError


class ProfessionalPinBarStrategy(BaseStrategy):
    """专业版Pin Bar策略"""

    def __init__(self):
        super().__init__()
        self.higher_tf_map = {
            '15m': '4h',
            '1h': '1d',
            '4h': '1d'
        }

    def analyze(self, symbol: str, timeframe: str) -> Optional[TradingSignal]:
        try:
            # 获取当前时间框架数据
            current_data = self._get_ohlcv(symbol, timeframe)
            if len(current_data) < 50:
                return None

            # 获取高级别趋势
            higher_tf = self.higher_tf_map.get(timeframe)
            trend = self._get_trend(symbol, higher_tf) if higher_tf else "NEUTRAL"

            # 检测最新3根K线的形态
            signals = []
            for i in range(-3, 0):
                current_candle = self._parse_candle(current_data[i])
                prev_candle = self._parse_candle(current_data[i - 1]) if i > -3 else None

                # 检测Pin Bar
                if pin_signal := self.pattern_detector.detect_pinbar(current_candle):
                    signals.append(self._create_signal(
                        symbol, timeframe, pin_signal, current_candle, trend
                    ))

                # 检测吞没形态
                if prev_candle and (
                engulf_signal := self.pattern_detector.detect_engulfing(current_candle, prev_candle)):
                    signals.append(self._create_signal(
                        symbol, timeframe, engulf_signal, current_candle, trend
                    ))

            # 选择置信度最高的信号
            valid_signals = [s for s in signals if s and self._filter_signal(s, trend)]
            if not valid_signals:
                return None

            best_signal = max(valid_signals, key=lambda x: x.confidence)
            self.db.log_signal(best_signal)
            return best_signal

        except Exception as e:
            logging.error(f"策略分析异常: {str(e)}")
            return None

    def _get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        """获取K线数据"""
        return self.exchange.get_ohlcv(symbol, timeframe, limit)

    @staticmethod
    def _parse_candle(ohlcv: list) -> dict:
        """解析CCXT返回的K线数据"""
        return {
            'timestamp': ohlcv[0],
            'open': ohlcv[1],
            'high': ohlcv[2],
            'low': ohlcv[3],
            'close': ohlcv[4],
            'volume': ohlcv[5]
        }

    def _get_trend(self, symbol: str, timeframe: str) -> str:
        """获取高级别趋势"""
        data = self._get_ohlcv(symbol, timeframe, 200)
        closes = np.array([c[4] for c in data], dtype=np.float64)

        # 使用双EMA判断趋势
        ema50 = talib.EMA(closes, timeperiod=50)[-1]
        ema200 = talib.EMA(closes, timeperiod=200)[-1]

        if ema50 > ema200 * 1.02:  # 考虑2%的过滤阈值
            return "BULLISH"
        elif ema50 < ema200 * 0.98:
            return "BEARISH"
        return "NEUTRAL"

    def _create_signal(self, symbol: str, timeframe: str,
                       direction: str, candle: dict, trend: str) -> Optional[TradingSignal]:
        """创建交易信号"""
        # 趋势过滤
        if trend not in ["NEUTRAL", direction.upper()]:
            logging.debug(f"趋势不符过滤: {direction} vs {trend}")
            return None

        # 计算ATR波动率
        atr = self._calculate_atr(symbol, timeframe)

        # 计算风险参数
        position_size, leverage = self.risk_manager.calculate_position(
            timeframe, self._calculate_confidence(candle, atr)
        )

        # 构建信号对象
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
        """计算ATR波动率"""
        data = self._get_ohlcv(symbol, timeframe, 100)
        high = np.array([c[2] for c in data], dtype=np.float64)
        low = np.array([c[3] for c in data], dtype=np.float64)
        close = np.array([c[4] for c in data], dtype=np.float64)
        return talib.ATR(high, low, close, timeperiod=period)[-1]

    @staticmethod
    def _calculate_stop_loss(candle: dict, direction: str, atr: float) -> float:
        """计算止损价格"""
        if direction == 'BULLISH':
            return candle['low'] - 0.5 * atr
        return candle['high'] + 0.5 * atr

    @staticmethod
    def _calculate_take_profit(candle: dict, direction: str, atr: float) -> float:
        """计算止盈价格"""
        risk_reward_ratio = 3.0
        if direction == 'BULLISH':
            return candle['close'] + risk_reward_ratio * atr
        return candle['close'] - risk_reward_ratio * atr

    @staticmethod
    def _calculate_confidence(candle: dict, atr: float) -> float:
        """计算信号置信度（0-1）"""
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']

        # 基于实体占比计算置信度
        confidence = (body_size / candle_range) if candle_range != 0 else 0
        return min(max(confidence, 0.3), 0.9)  # 限制在0.3-0.9之间

    def _filter_signal(self, signal: TradingSignal, trend: str) -> bool:
        """信号过滤器"""
        # 最小波动率过滤
        min_atr_ratio = 0.005  # ATR至少是价格的0.5%
        current_price = signal.entry_price
        atr = self._calculate_atr(signal.symbol, signal.timeframe)

        if (atr / current_price) < min_atr_ratio:
            return False

        # 趋势一致性过滤
        if trend not in ["NEUTRAL", signal.direction]:
            return False

        return True