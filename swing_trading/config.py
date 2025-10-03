import os

class ConfigurationManager:
    """
    Manages all configuration settings for the trading bot.
    Centralizes parameters for easy access and modification.
    """
    def __init__(self):
        # --- Exchange & API ---
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        if not self.api_key or not self.api_secret:
            # For backtesting, API keys are not strictly required, so we'll just warn
            print("Warning: API key/secret not found. Live trading will fail.")

        self.symbol = 'BTC/USDT'
        self.timeframe = '1h'
        
        # --- Portfolio & Risk ---
        self.capital_base = 100.0
        self.risk_per_trade_percent = 2.0 # Risk 2% of total capital on any single trade
        
        # --- Real-World Simulation (NEW) ---
        # Standard taker fee for many exchanges like Binance
        self.taker_fee_percent = 0.1 
        # Assumed price movement between signal and execution
        self.slippage_percent = 0.05 

        # --- Execution ---
        self.dry_run = True # Set to False to execute real trades

        # --- Active Strategy ---
        self.active_strategy = "SENTIMENT_MOMENTUM"

        # --- Strategy Parameters ---
        # 1. Sentiment Momentum Strategy
        self.sm_params = {
            "name": "SENTIMENT_MOMENTUM",
            "params": {
                "short_window": 10,
                "long_window": 30,
                "atr_period": 14,
                "atr_multiplier": 2.0,
            }
        }
        
        # 2. Mean Reversion (Bollinger Bands) - Placeholder
        self.mr_params = {
            "name": "MEAN_REVERSION",
            "params": {
                "bb_window": 20,
                "bb_std_dev": 2.0,
            }
        }
