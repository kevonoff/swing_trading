import ccxt
import os
import time
import pandas as pd
from config import ConfigurationManager

class DataHandler:
    """
    Handles all communication with the exchange to fetch market data.
    """
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.exchange = self._connect_to_exchange()

    def _connect_to_exchange(self):
        """
        Connects to the exchange with retry logic for robustness.
        """
        print("Connecting to Binance...")
        for i in range(5): # Retry up to 5 times
            try:
                exchange = ccxt.binance({
                    'apiKey': self.config.api_key, 'secret': self.config.api_secret,
                    'options': {'defaultType': 'spot'},
                    'enableRateLimit': True
                })
                exchange.load_markets()
                print("Successfully connected to Binance.")
                return exchange
            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                print(f"Connection failed: {e}. Retrying in {2**i} seconds...")
                time.sleep(2**i)
        raise ConnectionError("Could not connect to Binance after multiple retries.")

    def fetch_ohlcv(self, limit=100) -> pd.DataFrame:
        """
        Fetches the most recent OHLCV data.
        """
        print(f"Fetching last {limit} {self.config.timeframe} candles for {self.config.symbol}...")
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.config.symbol, self.config.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if df.empty:
                print("Warning: Fetched OHLCV data is empty.")

            return df
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            return pd.DataFrame() # Return empty DataFrame on failure

    def fetch_historical_data(self, start_date_str: str) -> pd.DataFrame:
        """
        Fetches historical data from a specific start date to now.
        """
        print(f"Fetching historical data for {self.config.symbol} since {start_date_str}...")
        all_ohlcv = []
        try:
            since = self.exchange.parse8601(start_date_str + 'T00:00:00Z')
            while True:
                ohlcv = self.exchange.fetch_ohlcv(self.config.symbol, self.config.timeframe, since=since, limit=1000)
                if len(ohlcv) == 0:
                    break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def get_current_price(self) -> float:
        """
        Gets the latest ticker price for the symbol.
        """
        try:
            ticker = self.exchange.fetch_ticker(self.config.symbol)
            return ticker['last']
        except Exception as e:
            print(f"Could not fetch current price: {e}")
            return None

