import os

class ConfigurationManager:
    """
    Manages all configuration settings for the trading bot.
    """
    def __init__(self):
        # API keys are now loaded directly from environment variables
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')

        # --- General Settings ---
        self.symbol = 'BTC/USDT'
        self.timeframe = '1h'
        
        # --- Portfolio & Risk ---
        self.capital_base = 100.0
        self.risk_per_trade_percent = 2.0
        self.dry_run = True # Set to False to execute real trades
        self.taker_fee_percent = 0.1
        self.slippage_percent = 0.05

        # --- Strategy Selection ---
        self.active_strategy = "SENTIMENT_MOMENTUM"

        # ======================================================================
        # STRATEGY PARAMETERS
        # ======================================================================
        
        # --- Strategy: Sentiment Momentum ---
        self.sm_short_window = 10
        self.sm_long_window = 30
        self.sm_atr_period = 14
        self.sm_atr_multiplier = 2.5
        
        # --- (Example) Strategy: Mean Reversion ---
        # self.mr_bollinger_period = 20
        # self.mr_bollinger_std_dev = 2.0
        
        # --- (Example) Strategy: Breakout ---
        # self.bo_donchian_period = 20

    def get_strategy_config(self) -> dict:
        """
        Returns a dictionary of parameters for the currently active strategy.
        """
        if self.active_strategy == "SENTIMENT_MOMENTUM":
            return {
                "name": self.active_strategy,
                "sm_short_window": self.sm_short_window,
                "sm_long_window": self.sm_long_window,
                "sm_atr_period": self.sm_atr_period,
                "sm_atr_multiplier": self.sm_atr_multiplier,
            }
        # Add other strategies here in the future
        # elif self.active_strategy == "MEAN_REVERSION":
        #     return { ... }
        
        raise ValueError(f"Strategy '{self.active_strategy}' is not defined.")

