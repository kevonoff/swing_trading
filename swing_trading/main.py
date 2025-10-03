import ccxt
import os
import time
import pandas as pd
import sys

from config import ConfigurationManager
from sentiment import SentimentAnalyzer
from swing_trading.data_handler import StrategyEngine
from data_handler import DataHandler
from portfolio_manager import PortfolioManager
from execution_handler import ExecutionHandler
from backtester import Backtester

# ==============================================================================
# MAIN TRADER APPLICATION
# ==============================================================================
class Trader:
    def __init__(self, config: ConfigurationManager):
        self.config = config
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
        print("Starting Trader application in LIVE/DRY-RUN mode...")
        while True:
            try:
                # 1. Fetch data
                ohlcv_data = self.data_handler.fetch_ohlcv()
                if ohlcv_data.empty:
                    time.sleep(60)
                    continue

                # 2. Get strategy config and add indicators
                strategy_config = self._get_strategy_config_from_manager()
                ohlcv_data_with_indicators = self.strategy_engine.add_indicators(ohlcv_data.copy(), strategy_config)

                # 3. Check for stop-loss
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

                # 4. Generate Signal
                current_sentiment = self.sentiment_analyzer.analyze()
                signal_details = self.strategy_engine.generate_signal(ohlcv_data_with_indicators, strategy_config, current_sentiment)
                signal = signal_details.get('signal')

                # 5. Act on signal
                if signal == 'buy' and not self.in_position:
                    self.stop_loss_price = signal_details.get('stop_loss')
                    if not self.stop_loss_price:
                        print("Strategy did not provide a stop-loss. Aborting trade.")
                        continue
                    
                    current_price = latest_candle['close']
                    print(f"Buy signal detected. Entry: ${current_price:.2f}, Stop-Loss: ${self.stop_loss_price:.2f}")
                    
                    position_size = self.portfolio_manager.calculate_position_size(current_price, self.stop_loss_price)
                    
                    if position_size > 0:
                        order_result = self.execution_handler.execute_order('buy', position_size, self.config.symbol)
                        if order_result:
                            self.in_position = True
                            self.entry_price = current_price

                elif signal == 'sell' and self.in_position:
                    print("Sell signal detected. Closing position.")
                    exit_price = latest_candle['close']
                    order_result = self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
                    if order_result:
                        self.portfolio_manager.update_balance_after_trade(exit_price, self.entry_price, self.portfolio_manager.last_position_size)
                        self.in_position = False
                        self.stop_loss_price = None
                        self.entry_price = 0.0
                else:
                    status = "In Position" if self.in_position else "Awaiting Signal"
                    print(f"Signal: Hold. Current status: {status}. Portfolio Balance: ${self.portfolio_manager.balance:.2f}")

            except Exception as e:
                print(f"An unexpected error occurred in the main loop: {e}")

            print("\n" + "="*50 + "\n")
            time.sleep(3600)

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================
if __name__ == '__main__':
    load_dotenv()
    config = ConfigurationManager()

    # Allow running the backtester from the command line
    if len(sys.argv) > 1 and sys.argv[1] == 'backtest':
        strategy_name = config.active_strategy
        if strategy_name == 'SENTIMENT_MOMENTUM':
            strategy_conf = {
                "name": strategy_name,
                "params": {
                    "short_window": config.sm_short_window,
                    "long_window": config.sm_long_window,
                    "atr_period": config.sm_atr_period,
                    "atr_multiplier": config.sm_atr_multiplier
                }
            }
            # Example: python main.py backtest 2023-01-01
            start_date_str = sys.argv[2] if len(sys.argv) > 2 else "2023-01-01"
            backtester = Backtester(config, strategy_conf, start_date_str)
            backtester.run()
        else:
            print(f"Backtesting for strategy '{strategy_name}' not implemented.")
    else:
        trader = Trader(config)
        trader.run()
