import ccxt
import os
import time
import pandas as pd
from dotenv import load_dotenv

# Local module imports
from config import ConfigurationManager
from sentiment_analysis.engine import get_current_market_sentiment
from strategy_engine import StrategyEngine

# ==============================================================================
# DATA HANDLER
# ==============================================================================
class DataHandler:
    """ Handles connection to the exchange and retrieval of raw market data. """
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
            print("Raw data fetched successfully.")
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
# PORTFOLIO & RISK MANAGER
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
# EXECUTION HANDLER
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

# ==============================================================================
# MAIN TRADER
# ==============================================================================
class Trader:
    """ Orchestrator for the entire trading process. """
    def __init__(self, config: ConfigurationManager, data_handler: DataHandler, strategy_engine: StrategyEngine, 
                 sentiment_analyzer: SentimentAnalyzer, portfolio_manager: PortfolioManager, execution_handler: ExecutionHandler):
        self.config = config
        self.data_handler = data_handler
        self.strategy_engine = strategy_engine
        self.sentiment_analyzer = sentiment_analyzer
        self.portfolio_manager = portfolio_manager
        self.execution_handler = execution_handler
        
        self.in_position = False
        self.stop_loss_price = None

    def _get_strategy_config_from_manager(self) -> dict:
        """ Constructs the strategy 'request object' from the main config. """
        strategy_name = self.config.active_strategy
        if strategy_name == 'SENTIMENT_MOMENTUM':
            return {
                "name": "SENTIMENT_MOMENTUM",
                "params": {
                    "short_window": self.config.sm_short_window,
                    "long_window": self.config.sm_long_window,
                    "atr_period": self.config.sm_atr_period
                }
            }
        # Add other strategies here...
        # elif strategy_name == 'MEAN_REVERSION':
        #     return {"name": "MEAN_REVERSION", "params": {...}}
        return {}

    def run(self):
        print("Starting the trading application: Project Compounder")
        print(f"Mode: {'DRY RUN' if self.config.dry_run else '!!! LIVE TRADING !!!'}")
        print("-" * 50)

        while True:
            try:
                # 1. Get the strategy config for this run
                strategy_config = self._get_strategy_config_from_manager()
                if not strategy_config:
                    raise ValueError(f"Active strategy '{self.config.active_strategy}' is not configured.")

                # 2. Fetch raw data
                ohlcv_data = self.data_handler.fetch_ohlcv()
                if ohlcv_data is None or ohlcv_data.empty:
                    time.sleep(60)
                    continue
                
                # 3. Calculate indicators using the strategy engine
                ohlcv_data_with_indicators = self.strategy_engine.calculate_indicators(ohlcv_data, strategy_config)

                # 4. Check for stop-loss
                latest_candle = ohlcv_data_with_indicators.iloc[-1]
                if self.in_position and latest_candle['close'] < self.stop_loss_price:
                    print(f"!!! STOP-LOSS TRIGGERED at ${self.stop_loss_price:.2f} !!!")
                    self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
                    self.in_position = False
                    self.stop_loss_price = None
                    continue

                # 5. Generate Signal
                current_sentiment = self.sentiment_analyzer.analyze()
                signal = self.strategy_engine.generate_signal(ohlcv_data_with_indicators, strategy_config, current_sentiment)

                # 6. Act on signal
                if signal == 'buy' and not self.in_position:
                    entry_price = latest_candle['close']
                    # Note: This part is still specific to the ATR from the SM strategy.
                    # A more generic system would get stop-loss info from the strategy engine itself.
                    atr_value = latest_candle[f'ATRr_{self.config.sm_atr_period}']
                    self.stop_loss_price = entry_price - (atr_value * self.config.sm_atr_multiplier)
                    
                    print(f"Buy signal detected. Entry: ${entry_price:.2f}, Stop-Loss: ${self.stop_loss_price:.2f}")
                    
                    position_size = self.portfolio_manager.calculate_position_size(entry_price, self.stop_loss_price)
                    
                    if position_size > 0:
                        self.execution_handler.execute_order('buy', position_size, self.config.symbol)
                        self.in_position = True

                elif signal == 'sell' and self.in_position:
                    print("Sell signal detected. Closing position.")
                    self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
                    self.in_position = False
                    self.stop_loss_price = None

                else: # signal == 'hold'
                    status = "In Position" if self.in_position else "Awaiting Signal"
                    print(f"Holding. Status: {status}. Current Price: ${latest_candle['close']:.2f}")

                print("-" * 50)
                time.sleep(3600)

            except KeyboardInterrupt:
                print("\nShutdown signal received. Exiting application.")
                break
            except Exception as e:
                print(f"An unexpected error occurred in the main loop: {e}")
                time.sleep(60)

# ==============================================================================
# BOOTSTRAP
# ==============================================================================
if __name__ == '__main__':
    config = ConfigurationManager()
    data_handler = DataHandler(config)
    sentiment_analyzer = SentimentAnalyzer()
    strategy_engine = StrategyEngine()
    portfolio_manager = PortfolioManager(config)
    execution_handler = ExecutionHandler(config, data_handler.exchange)
    
    trader = Trader(config, data_handler, strategy_engine, sentiment_analyzer, portfolio_manager, execution_handler)
    trader.run()

