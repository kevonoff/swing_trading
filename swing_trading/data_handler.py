import ccxt
import pandas as pd
import time
import os
import pickle

class DataHandler:
    """
    Handles all communication with the exchange to fetch market data, with local caching.
    """
    def __init__(self, config):
        self.config = config
        self.exchange = self._connect_to_exchange()
        # This will fail if connection is not established, which is good.
        self.platform_id = self.exchange.id
        
        # --- Caching ---
        self.cache_file = 'data.data'
        self.cache = self._load_cache()

        # --- Rate Limiting ---
        self.rate_limit_delay_seconds = 0.1 # Enforces max 10 requests/sec, well under 1200/min
        self.last_request_time = 0

    def _load_cache(self) -> dict:
        """
        Loads the data cache from a local pickle file.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    print(f"Loading data from local cache file: {self.cache_file}")
                    return pickle.load(f)
            except (pickle.UnpicklingError, EOFError):
                print("Warning: Cache file is corrupt or empty. Starting fresh.")
                return {}
        return {}

    def _save_cache(self):
        """
        Saves the current data cache to a local pickle file.
        """
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.cache, f)

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
        Establishes a connection to the exchange with retry logic and fixes for recursion errors.
        """
        print("Connecting to Binance.US...")
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Step 1: Instantiate the exchange class with an explicit timeout
                exchange = ccxt.binanceus({
                    'apiKey': self.config.api_key,
                    'secret': self.config.api_secret,
                    'options': {
                        'defaultType': 'spot',
                    },
                    'enableRateLimit': True,
                    'timeout': 30000,  # 30 seconds timeout
                })
                
                # Step 2: Explicitly load the markets after instantiation
                exchange.load_markets()
                
                print("Successfully connected to Binance.US.")
                return exchange

            # Catch specific CCXT network errors for better debugging
            except ccxt.NetworkError as e:
                print(f"Connection failed on attempt {attempt + 1}/{max_retries} (NetworkError): {e}")
                time.sleep(5)
            # Catch other exceptions, including the RecursionError
            except Exception as e:
                print(f"Connection failed on attempt {attempt + 1}/{max_retries} (General Error): {e}")
                time.sleep(5)
        
        raise ConnectionError("Failed to connect to the exchange after several retries.")

    def fetch_ohlcv(self, limit=100) -> pd.DataFrame:
        """
        Fetches historical OHLCV data, utilizing the cache first.
        """
        # --- Caching Logic ---
        # Key format: platform_symbol_timeframe_limit
        symbol_safe = self.config.symbol.replace('/', '')
        cache_key = f"{self.platform_id}_{symbol_safe}_{self.config.timeframe}_{limit}"
        
        if cache_key in self.cache:
            print(f"Found data in cache for key: {cache_key}")
            return self.cache[cache_key]
        
        # --- API Fetch Logic (if not in cache) ---
        try:
            self._apply_rate_limit()
            
            print(f"Fetching last {limit} {self.config.timeframe} candles for {self.config.symbol} from exchange...")
            ohlcv = self.exchange.fetch_ohlcv(self.config.symbol, self.config.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if df.empty or 'close' not in df.columns or df['close'].isnull().all():
                print("Warning: Fetched data is empty or invalid.")
                return pd.DataFrame()

            # --- Save to Cache ---
            print(f"Saving new data to cache with key: {cache_key}")
            self.cache[cache_key] = df
            self._save_cache()

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

