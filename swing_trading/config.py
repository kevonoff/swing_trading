import os
from dotenv import load_dotenv

class ConfigurationManager:
    def __init__(self):
        load_dotenv()
        # --- API Credentials ---
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret must be set in the .env file.")

        # --- General Trading Parameters ---
        self.symbol = 'BTC/USDT'
        self.timeframe = '1h'
        self.active_strategy = 'SENTIMENT_MOMENTUM' # Use this to switch strategies

        # --- Portfolio & Risk Management ---
        self.capital_base = 100.0
        self.risk_per_trade_percent = 2.0 # Risk 2% of total capital on any single trade
        self.dry_run = True # <<<< SET TO False TO EXECUTE REAL TRADES >>>>

        # ======================================================================
        # STRATEGY-SPECIFIC PARAMETERS
        # ======================================================================

        # --- 1. Sentiment Momentum Strategy (sm_) ---
        self.sm_short_window = 10
        self.sm_long_window = 30
        self.sm_atr_period = 14
        self.sm_atr_multiplier = 1.5

        # --- 2. Mean Reversion Strategy (mr_) ---
        # self.mr_bollinger_period = 20
        # self.mr_bollinger_std_dev = 2.0
        # self.mr_rsi_period = 14
        # self.mr_rsi_oversold = 30

        # --- 3. Breakout Strategy (bo_) ---
        # self.bo_donchian_period = 20
        # self.bo_volume_factor = 1.5 # e.g., volume must be 1.5x the average
