import ccxt
import os
import time
import pandas as pd
from config import ConfigurationManager
from sentiment import SentimentAnalyzer
from strategy_engine import StrategyEngine

# ==============================================================================
# DATA HANDLER
# ==============================================================================pip
class DataHandler:
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
            return df
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            return pd.DataFrame()

# ==============================================================================
# PORTFOLIO & RISK MANAGER
# ==============================================================================
class PortfolioManager:
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.balance = self.config.capital_base
        self.last_position_size = 0.0
        self.realized_pnl = 0.0

    def calculate_position_size(self, entry_price: float, stop_loss_price: float):
        risk_amount_dollars = self.balance * (self.config.risk_per_trade_percent / 100.0)
        risk_per_coin_dollars = entry_price - stop_loss_price
        
        if risk_per_coin_dollars <= 0:
            print("Error: Stop-loss price must be below entry price. Cannot calculate position size.")
            return 0.0

        position_size = risk_amount_dollars / risk_per_coin_dollars
        print(f"Calculated Position Size (BTC): {position_size:.6f}")
        self.last_position_size = position_size
        return position_size

    def update_balance_after_trade(self, exit_price: float, entry_price: float, position_size: float):
        """ Updates the balance after closing a position. """
        pnl = (exit_price - entry_price) * position_size
        self.balance += pnl
        self.realized_pnl += pnl
        print("=" * 20 + " TRADE CLOSED " + "=" * 20)
        print(f"P&L for this trade: ${pnl:.2f}")
        print(f"New Portfolio Balance: ${self.balance:.2f}")
        print(f"Total Realized P&L: ${self.realized_pnl:.2f}")

# ==============================================================================
# EXECUTION HANDLER
# ==============================================================================
class ExecutionHandler:
    def __init__(self, config: ConfigurationManager, exchange):
        self.config = config
        self.exchange = exchange

    def execute_order(self, order_type: str, amount: float, symbol: str):
        print("-" * 20 + " EXECUTION " + "-" * 20)
        print(f"Requesting to {order_type.upper()} {amount:.6f} {symbol}")
        
        if self.config.dry_run:
            print("--- DRY RUN MODE ---")
            print(f"Order would be sent to the exchange.")
            return True # Simulate successful order
        else:
            try:
                # TODO: Implement actual order execution logic
                print("--- LIVE MODE ---")
                print("Live order execution not yet implemented.")
                return True # Placeholder for actual execution result
            except Exception as e:
                print(f"An error occurred during order execution: {e}")
                return False

# ==============================================================================
# MAIN TRADER APPLICATION
# ==============================================================================
class Trader:
    def __init__(self):
        self.config = ConfigurationManager()
        self.data_handler = DataHandler(self.config)
        self.portfolio_manager = PortfolioManager(self.config)
        self.execution_handler = ExecutionHandler(self.config, self.data_handler.exchange)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.strategy_engine = StrategyEngine()
        
        self.in_position = False
        self.stop_loss_price = None
        self.entry_price = 0.0

    def _get_strategy_config_from_manager(self) -> dict:
        """ Constructs the strategy 'request object' from the main config. """
        strategy_name = self.config.active_strategy
        if strategy_name == 'SENTIMENT_MOMENTUM':
            return {
                "name": strategy_name,
                "params": {
                    "short_window": self.config.sm_short_window,
                    "long_window": self.config.sm_long_window,
                    "atr_period": self.config.sm_atr_period,
                    "atr_multiplier": self.config.sm_atr_multiplier
                }
            }
        # Add other strategies here...
        else:
            raise ValueError(f"Strategy '{strategy_name}' not recognized in Trader.")

    def run(self):
        print("Starting Trader application...")
        while True:
            try:
                # 1. Fetch data
                ohlcv_data = self.data_handler.fetch_ohlcv()
                if ohlcv_data.empty:
                    time.sleep(60)
                    continue

                # 2. Get strategy config
                strategy_config = self._get_strategy_config_from_manager()
                
                # 3. Add indicators to data
                ohlcv_data_with_indicators = self.strategy_engine.add_indicators(ohlcv_data, strategy_config)

                # 4. Check for stop-loss
                latest_candle = ohlcv_data_with_indicators.iloc[-1]
                if self.in_position and latest_candle['close'] <= self.stop_loss_price:
                    print(f"!!! STOP-LOSS TRIGGERED at ${self.stop_loss_price:.2f} !!!")
                    exit_price = latest_candle['close']
                    order_result = self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
                    if order_result:
                        self.portfolio_manager.update_balance_after_trade(exit_price, self.entry_price, self.portfolio_manager.last_position_size)
                        self.in_position = False
                        self.stop_loss_price = None
                        self.entry_price = 0.0
                    continue

                # 5. Generate Signal
                current_sentiment = self.sentiment_analyzer.analyze()
                signal_details = self.strategy_engine.generate_signal(ohlcv_data_with_indicators, strategy_config, current_sentiment)
                signal = signal_details.get('signal')

                # 6. Act on signal
                if signal == 'buy' and not self.in_position:
                    # The Strategy Engine now provides the stop-loss price
                    self.stop_loss_price = signal_details.get('stop_loss')
                    if not self.stop_loss_price:
                        print("Strategy did not provide a stop-loss. Aborting trade.")
                        continue
                    
                    current_price = latest_candle['close']
                    print(f"Buy signal detected. Entry: ${current_price:.2f}, Stop-Loss: ${self.stop_loss_price:.2f}")
                    
                    position_size = self.portfolio_manager.calculate_position_size(current_price, self.stop_loss_price)
                    
                    if position_size > 0:
                        order_result = self.execution_handler.execute_order('buy', position_size, self.config.symbol)
                        # Only update state if the order was successful
                        if order_result:
                            self.in_position = True
                            self.entry_price = current_price # Record entry price

                elif signal == 'sell' and self.in_position:
                    print("Sell signal detected. Closing position.")
                    exit_price = latest_candle['close']
                    order_result = self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
                    if order_result:
                        self.portfolio_manager.update_balance_after_trade(exit_price, self.entry_price, self.portfolio_manager.last_position_size)
                        self.in_position = False
                        self.stop_loss_price = None
                        self.entry_price = 0.0

                else: # signal == 'hold'
                    status = "In Position" if self.in_position else "Awaiting Signal"
                    print(f"Signal: Hold. Current status: {status}. Portfolio Balance: ${self.portfolio_manager.balance:.2f}")

            except Exception as e:
                print(f"An unexpected error occurred in the main loop: {e}")

            print("\n" + "="*50 + "\n")
            time.sleep(3600) # Wait for the next candle
