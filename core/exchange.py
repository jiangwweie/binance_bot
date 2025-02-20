# 交易所接口
import ccxt
from config.settings import Settings


class BinanceFutureClient:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': Settings.BINANCE_API_KEY,
            'secret': Settings.BINANCE_SECRET,
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })

    def get_ohlcv(self, symbol, timeframe, limit=100):
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)