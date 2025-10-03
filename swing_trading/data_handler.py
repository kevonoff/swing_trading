import ccxt
import pandas as pd
import time
from datetime import datetime

class DataHandler:
    """
    Handles all communication with the exchange to fetch market data.
    """
    def __init__(self, config):
        self.config = config
        self.exchange = self._connect_to_exchange()

    def _connect_to_exchange(self):
        """ Connects to the exchange with retry logic. """
        max_retries = 5
        for attempt in range(max_retries):
            try:
                print("Connecting to Binance...")
                exchange = ccxt.binance({
                    'apiKey': self.config.api_key, 'secret': self.config.api_secret,
                    'options': {'defaultType': 'spot'},
                    'enableRateLimit': True,
                })
                exchange.load_markets()
                print("Successfully connected to Binance.")
                return exchange
            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                print(f"Connection failed on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1)) # Exponential backoff
                else:
                    print("Could not connect to the exchange after several retries. Exiting.")
                    raise
        return None

    def fetch_ohlcv(self, limit=100):
        """ Fetches the most recent OHLCV candles for live trading. """
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.config.symbol, self.config.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            return pd.DataFrame()

    def fetch_historical_data(self, start_date_str: str):
        """
        Fetches historical OHLCV data from a specific start date to now.
        """
        print(f"Fetching historical data for {self.config.symbol} since {start_date_str}...")
        try:
            since = self.exchange.parse8601(start_date_str + 'T00:00:00Z')
            all_ohlcv = []
            while since < self.exchange.milliseconds():
                ohlcv = self.exchange.fetch_ohlcv(self.config.symbol, self.config.timeframe, since=since, limit=1000)
                if len(ohlcv):
                    since = ohlcv[-1][0] + self.exchange.parse_timeframe(self.config.timeframe) * 1000
                    all_ohlcv.extend(ohlcv)
                else:
                    break
            
            if not all_ohlcv:
                print("Warning: No historical data returned from the exchange.")
                return pd.DataFrame()
                
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            # Remove potential duplicates from overlapping fetches
            df.drop_duplicates(subset='timestamp', inplace=True)
            df.set_index('timestamp', inplace=True)
            print(f"Successfully fetched {len(df)} historical data points.")
            return df.reset_index() # Return with timestamp as a column to match fetch_ohlcv
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.DataFrame()
