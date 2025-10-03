import ccxt
import os
import time
import pandas as pd
import pandas_ta as ta # New library for technical analysis
from dotenv import load_dotenv
# We are assuming the modular sentiment engine exists as discussed
from sentiment_analysis.engine import get_current_market_sentiment

# ==============================================================================
# CONFIGURATION MANAGER
# ==============================================================================
class ConfigurationManager:
    """ Manages all system configuration from the .env file and this class. """
    def __init__(self):
        load_dotenv()
        # --- Exchange & API ---
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret must be set in the .env file.")

        # --- General Trading Parameters ---
        self.symbol = 'BTC/USDT'
        self.timeframe = '1h'
        
        # --- Portfolio & Risk Management ---
        self.capital_base = 100.0
        self.risk_per_trade_percent = 2.0 # Risk 2% of total capital on any single trade
        self.dry_run = True # <<<< SET TO False TO EXECUTE REAL TRADES >>>>
        self.max_open_positions = 1 # For now, the system will only manage one position at a time.

        # =================================================================
        # STRATEGY-SPECIFIC PARAMETERS
        # You can uncomment and configure the section for the strategy you
        # want to make active.
        # =================================================================
        
        self.active_strategy = 'SENTIMENT_MOMENTUM' # Defines which strategy logic to run

        # --- Strategy 1: Sentiment Momentum (Current Active Strategy) ---
        self.sm_short_window = 10
        self.sm_long_window = 30
        self.sm_atr_period = 14
        self.sm_atr_multiplier = 1.5

        # --- Strategy 2: Mean Reversion (using Bollinger Bands & RSI) ---
        # self.mr_bollinger_period = 20
        # self.mr_bollinger_std_dev = 2.0
        # self.mr_rsi_period = 14
        # self.mr_rsi_oversold = 30
        # self.mr_rsi_overbought = 70

        # --- Strategy 3: Breakout (using Donchian Channels & Volume) ---
        # self.bo_donchian_period = 20 # Lookback period for highest high / lowest low
        # self.bo_volume_threshold_multiplier = 1.5 # e.g., volume must be 1.5x the average
        # self.bo_volume_lookback = 20

# ==============================================================================
# DATA HANDLER
# ==============================================================================
class DataHandler:
    """ Handles connection to the exchange and retrieval of market data. """
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.exchange = self._connect_to_exchange()

    def _connect_to_exchange(self):
        print("Connecting to Binance...")
        exchange = ccxt.binance({
            'apiKey': self.config.api_key, 'secret': self.config.api_secret,
            'options': {'defaultType': 'spot'},
        })
        exchange.load_markets()
        print("Successfully connected to Binance.")
        return exchange

    def fetch_ohlcv(self, limit=100):
        print(f"Fetching last {limit} {self.config.timeframe} candles for {self.config.symbol}...")
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.config.symbol, self.config.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # --- Calculate indicators based on the active strategy ---
            if self.config.active_strategy == 'SENTIMENT_MOMENTUM':
                df.ta.atr(length=self.config.sm_atr_period, append=True)
                df['short_sma'] = df['close'].rolling(window=self.config.sm_short_window).mean()
                df['long_sma'] = df['close'].rolling(window=self.config.sm_long_window).mean()
            
            # Add other indicator calculations for other strategies here...

            print("Data fetched and indicators calculated successfully.")
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

# ==============================================================================
# SENTIMENT ANALYZER
# ==============================================================================
class SentimentAnalyzer:
    """ Analyzes market sentiment by leveraging the dedicated sentiment engine. """
    def analyze(self):
        return get_current_market_sentiment()

# ==============================================================================
# STRATEGY ENGINE
# ==============================================================================
class SentimentMomentumStrategy:
    """ Generates signals based on a combination of technical momentum and sentiment. """
    def generate_signal(self, ohlcv_df: pd.DataFrame, sentiment: str):
        print("Analyzing market data for trading signals...")
        latest = ohlcv_df.iloc[-1]
        previous = ohlcv_df.iloc[-2]

        if latest['short_sma'] > latest['long_sma'] and previous['short_sma'] <= previous['long_sma']:
            print("Technical Buy Signal: Short SMA crossed above Long SMA.")
            if sentiment != 'negative':
                print("Sentiment Confirmed. Final Signal: BUY")
                return 'buy'
            else:
                print("Sentiment is Negative. Vetoing buy signal.")
                return 'hold'
        
        elif latest['short_sma'] < latest['long_sma'] and previous['short_sma'] >= previous['long_sma']:
            print("Technical Sell Signal: Short SMA crossed below Long SMA. Final Signal: SELL")
            return 'sell'
        
        return 'hold'

# ==============================================================================
# PORTFOLIO & RISK MANAGER (NEW)
# ==============================================================================
class PortfolioManager:
    """ Manages capital, position sizing, and overall portfolio risk. """
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.balance = self.config.capital_base
        self.last_position_size = 0.0

    def calculate_position_size(self, entry_price: float, stop_loss_price: float):
        risk_amount_dollars = self.balance * (self.config.risk_per_trade_percent / 100.0)
        price_risk_per_unit = entry_price - stop_loss_price
        
        if price_risk_per_unit <= 0:
            print("Error: Stop loss is not below entry price. Cannot calculate position size.")
            return 0.0

        position_size = risk_amount_dollars / price_risk_per_unit
        print(f"Portfolio Balance: ${self.balance:.2f}")
        print(f"Risk Amount for this trade: ${risk_amount_dollars:.2f}")
        print(f"Calculated Position Size (BTC): {position_size:.6f}")
        self.last_position_size = position_size
        return position_size

# ==============================================================================
# EXECUTION HANDLER (NEW)
# ==============================================================================
class ExecutionHandler:
    """ Handles the execution of trade orders on the exchange. """
    def __init__(self, config: ConfigurationManager, exchange):
        self.config = config
        self.exchange = exchange

    def execute_order(self, side: str, amount: float, symbol: str):
        print("-" * 10 + f" EXECUTION ({'DRY RUN' if self.config.dry_run else 'LIVE'}) " + "-" * 10)
        print(f"Side: {side.upper()}, Amount: {amount:.6f} {symbol.split('/')[0]}")
        
        if self.config.dry_run:
            print("DRY RUN: No real order will be placed.")
            return {"status": "ok", "dry_run": True}
        
        try:
            if side == 'buy':
                order = self.exchange.create_market_buy_order(symbol, amount)
            elif side == 'sell':
                order = self.exchange.create_market_sell_order(symbol, amount)
            else:
                return None
            
            print("LIVE: Order placed successfully.")
            print(order)
            return order
        except Exception as e:
            print(f"!!! ORDER EXECUTION FAILED: {e} !!!")
            return None

# # ==============================================================================
# # MAIN TRADER
# # ==============================================================================
# class Trader:
#     """ Orchestrator for the entire trading process. """
#     def __init__(self, config: ConfigurationManager, data_handler: DataHandler, strategy: SentimentMomentumStrategy, 
#                  sentiment_analyzer: SentimentAnalyzer, portfolio_manager: PortfolioManager, execution_handler: ExecutionHandler):
#         self.config = config
#         self.data_handler = data_handler
#         self.strategy = strategy
#         self.sentiment_analyzer = sentiment_analyzer
#         self.portfolio_manager = portfolio_manager
#         self.execution_handler = execution_handler
        
#         self.in_position = False
#         self.stop_loss_price = None

#     def run(self):
#         print("Starting the trading application: Project Compounder")
#         print(f"Initial Capital: ${self.config.capital_base:.2f} USDT")
#         print(f"Risk Per Trade: {self.config.risk_per_trade_percent}%")
#         print(f"Mode: {'DRY RUN' if self.config.dry_run else '!!! LIVE TRADING !!!'}")
#         print("-" * 50)

#         while True:
#             try:
#                 ohlcv_data = self.data_handler.fetch_ohlcv()
#                 if ohlcv_data is None or ohlcv_data.empty:
#                     time.sleep(60)
#                     continue

#                 latest_candle = ohlcv_data.iloc[-1]
                
#                 # --- STOP-LOSS CHECK ---
#                 if self.in_position and latest_candle['close'] < self.stop_loss_price:
#                     print(f"!!! STOP-LOSS TRIGGERED at ${self.stop_loss_price:.2f} !!!")
#                     self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
#                     self.in_position = False
#                     self.stop_loss_price = None
#                     # We assume the sell updates our balance. In a real system, we'd confirm this.
#                     continue

#                 # --- SIGNAL GENERATION ---
#                 current_sentiment = self.sentiment_analyzer.analyze()
#                 signal = self.strategy.generate_signal(ohlcv_data, current_sentiment)

#                 if signal == 'buy' and not self.in_position:
#                     entry_price = latest_candle['close']
#                     atr_value = latest_candle[f'ATRr_{self.config.sm_atr_period}']
#                     self.stop_loss_price = entry_price - (atr_value * self.config.sm_atr_multiplier)
                    
#                     print(f"Buy signal detected. Entry: ${entry_price:.2f}, Stop-Loss: ${self.stop_loss_price:.2f}")
                    
#                     position_size = self.portfolio_manager.calculate_position_size(entry_price, self.stop_loss_price)
                    
#                     if position_size > 0:
#                         self.execution_handler.execute_order('buy', position_size, self.config.symbol)
#                         self.in_position = True

#                 elif signal == 'sell' and self.in_position:
#                     print("Sell signal detected. Closing position.")
#                     self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
#                     self.in_position = False
#                     self.stop_loss_price = None

#                 else: # signal == 'hold'
#                     status = "In Position" if self.in_position else "Awaiting Signal"
#                     print(f"Holding. Status: {status}. Current Price: ${latest_candle['close']:.2f}")

#                 print("-" * 50)
#                 time.sleep(3600)

#             except KeyboardInterrupt:
#                 print("\nShutdown signal received. Exiting application.")
#                 break
#             except Exception as e:
#                 print(f"An unexpected error occurred in the main loop: {e}")
#                 time.sleep(60)

# # ==============================================================================
# # BOOTSTRAP
# # ==============================================================================
# if __name__ == '__main__':
#     config = ConfigurationManager()
#     data_handler = DataHandler(config)
#     sentiment_analyzer = SentimentAnalyzer()
#     strategy = SentimentMomentumStrategy()
#     portfolio_manager = PortfolioManager(config)
#     execution_handler = ExecutionHandler(config, data_handler.exchange)
    
#     trader = Trader(config, data_handler, strategy, sentiment_analyzer, portfolio_manager, execution_handler)
#     trader.run()

