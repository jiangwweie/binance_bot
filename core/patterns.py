# K线形态识别
class CandlePatternDetector:
    @staticmethod
    def detect_pinbar(candle):
        """
        识别Pin Bar形态
        :param candle: dict {'open':, 'high':, 'low':, 'close':}
        :return: 'bullish'/'bearish'/None
        """
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']

        if total_range == 0:
            return None

        # 实体占比小于30%
        if body / total_range > 0.3:
            return None

        # 看涨Pin Bar（长下影）
        if (candle['close'] > candle['open'] and
                (candle['open'] - candle['low']) > 2 * body):
            print(f"发现长下影线,开盘价={candle['open']},最高= {candle['high']},最低= {candle['low']}, 收盘={candle['close']}")
            return 'bullish'

        # 看跌Pin Bar（长上影）
        if (candle['close'] < candle['open'] and
                (candle['high'] - candle['open']) > 2 * body):
            print(f"发现长上影线,开盘价={candle['open']},最高= {candle['high']},最低= {candle['low']}, 收盘={candle['close']}")
            return 'bearish'
        print(f"中性,开盘价={candle['open']},最高= {candle['high']},最低= {candle['low']}, 收盘={candle['close']}")
        return None

    @staticmethod
    def detect_engulfing(current, previous):
        """
        识别吞没形态
        :param current: 当前K线
        :param previous: 前一根K线
        :return: 'bullish'/'bearish'/None
        """
        # body_current = abs(current['close'] - current['open'])
        # body_prev = abs(previous['close'] - previous['open'])
        #
        # if body_current <= body_prev:
        #     return None
        #
        # # 看涨吞没
        # if (current['close'] > current['open'] and
        #         current['open'] < previous['close'] and
        #         current['close'] > previous['open']):
        #     return 'BULLISH'
        #
        # # 看跌吞没
        # if (current['close'] < current['open'] and
        #         current['open'] > previous['close'] and
        #         current['close'] < previous['open']):
        #     return 'BEARISH'

        return None
