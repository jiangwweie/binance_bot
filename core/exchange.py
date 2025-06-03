import ccxt
import logging
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import Settings
import pandas as pd


class BinanceFutureClient:
    def __init__(self):
        config = {
            'apiKey': Settings.BINANCE_API_KEY,
            'secret': Settings.BINANCE_SECRET,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True
            },
            'enableRateLimit': True,
            'timeout': 15000,
            'proxies': {
                'http': Settings.PROXY,
                'https': Settings.PROXY,
            }
        }
        self.exchange = ccxt.binance(config)

    def _sync_time(self):
        try:
            server_time = self.exchange.fetch_time()
            local_time = self.exchange.milliseconds()
            self.time_diff = server_time - local_time
        except Exception as e:
            logging.warning(f"时间同步失败: {str(e)}")

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10))
    @lru_cache(maxsize=100)
    def get_ohlcv(self, symbol, timeframe, limit=100):
        try:
            return self.exchange.fetch_ohlcv(
                symbol,
                timeframe,
                limit=limit,
                params={'price': 'mark'}
            )
        except ccxt.NetworkError as e:
            logging.error(f"网络错误: {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logging.error(f"交易所错误: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"未知错误: {str(e)}")
            raise


def main():
    ##无代理初始化Binance交易所对象 binance = ccxt.binance()
    # 代理服务器地址和端口
    proxy = 'http://127.0.0.1:8118'

    # 初始化Binance交易所对象，并设置代理  # 初始化Binance交易所对象，这里我们不提供API密钥和私钥，因为我们只是获取公共数据
    binance = ccxt.binance({
        'proxies': {
            'http': proxy,
            'https': proxy,
        }
    })

    # 加载ETH/USDT市场数据
    markets = binance.load_markets()

    # 获取ETH/USDT的市场标识符，用于后续请求
    market_symbol = binance.market('ETH/USDT')['symbol']

    # 获取ETH/USDT的最新行情信息（ticker）
    ticker = binance.fetch_ticker(market_symbol)

    # 打印ETH/USDT的最新价格
    print(f"ETH/USDT 最新价格: {ticker['last']}")

    # 获取ETH/USDT的订单簿
    order_book = binance.fetch_order_book(market_symbol)

    # 打印ETH/USDT订单簿的前5个卖单和买单
    print("ETH/USDT 订单簿 - 前5个卖单:")
    for ask in order_book['asks'][:5]:
        print(f"价格: {ask[0]}, 数量: {ask[1]}")

    print("\nETH/USDT 订单簿 - 前5个买单:")
    for bid in order_book['bids'][:5]:
        print(f"价格: {bid[0]}, 数量: {bid[1]}")



if __name__ == "__main__":
    main()
