import ccxt
import pandas as pd
import time

class DataHandler:
    """
    Handles all communication with the exchange to fetch market data.
    """
    def __init__(self, config):
        self.config = config
        self.exchange = self._connect_to_exchange()
        
        # --- Rate Limiting ---
        self.rate_limit_delay_seconds = 0.1 # Enforces max 10 requests/sec, well under 1200/min
        self.last_request_time = 0

    def _apply_rate_limit(self):
        """
        Ensures that we do not exceed the exchange's API rate limits.
        """
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.rate_limit_delay_seconds:
            sleep_time = self.rate_limit_delay_seconds - elapsed_time
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _connect_to_exchange(self):
        """
        Establishes a connection to the exchange with retry logic.
        """
        print("Connecting to Binance.US...")
        max_retries = 5
        for attempt in range(max_retries):
            try:
                exchange = ccxt.binanceus({
                    'apiKey': self.config.api_key,
                    'secret': self.config.api_secret,
                    'options': {'defaultType': 'spot'},
                    'enableRateLimit': True, # Enable ccxt's built-in rate limiter
                })
                exchange.load_markets()
                print("Successfully connected to Binance.US.")
                return exchange
            except Exception as e:
                print(f"Connection failed on attempt {attempt + 1}/{max_retries}: {e}")
                time.sleep(5)
        raise ConnectionError("Failed to connect to the exchange after several retries.")

    def fetch_ohlcv(self, limit=100) -> pd.DataFrame:
        """
        Fetches historical OHLCV data from the exchange.
        """
        try:
            # Apply our custom rate limit before making the API call
            self._apply_rate_limit()
            
            print(f"Fetching last {limit} {self.config.timeframe} candles for {self.config.symbol}...")
            ohlcv = self.exchange.fetch_ohlcv(self.config.symbol, self.config.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Basic data validation
            if df.empty or 'close' not in df.columns or df['close'].isnull().all():
                print("Warning: Fetched data is empty or invalid.")
                return pd.DataFrame()

            return df
        except Exception as e:
            print(f"An error occurred while fetching OHLCV data: {e}")
            return pd.DataFrame()

    def fetch_latest_data(self) -> pd.DataFrame:
        """
        Fetches the most recent data required for the strategy.
        """
        # Fetch enough data for the longest indicator window
        required_candles = self.config.sm_long_window + 20 # Add a buffer
        return self.fetch_ohlcv(limit=required_candles)

