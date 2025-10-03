import time
import sys

from config import ConfigurationManager
from sentiment import SentimentEngine
from strategy_engine import StrategyEngine
from data_handler import DataHandler
from portfolio_manager import PortfolioManager
from execution_handler import ExecutionHandler
from backtester import Backtester

class Trader:
    """
    The main class that orchestrates the live trading bot.
    """
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.data_handler = DataHandler(self.config)
        self.portfolio_manager = PortfolioManager(self.config)
        self.execution_handler = ExecutionHandler(self.config, self.data_handler.exchange)
        self.sentiment_analyzer = SentimentEngine()
        self.strategy_engine = StrategyEngine()
        
        # State tracking
        self.in_position = False
        self.stop_loss_price = None
        self.entry_price = 0.0

    def _get_strategy_config_from_manager(self) -> dict:
        """
        Constructs the strategy configuration dictionary based on the active strategy
        set in the ConfigurationManager.
        """
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
        # Future strategies would be added here as 'elif' blocks
        else:
            raise ValueError(f"Strategy '{strategy_name}' not recognized in Trader.")

    def run(self):
        """
        The main trading loop for live or dry-run mode.
        """
        print("Starting Trader application in LIVE/DRY-RUN mode...")
        while True:
            try:
                # 1. Fetch latest market data
                ohlcv_data = self.data_handler.fetch_ohlcv()
                if ohlcv_data.empty:
                    time.sleep(60) # Wait a minute if data fetch fails
                    continue

                # 2. Get the active strategy configuration
                strategy_config = self._get_strategy_config_from_manager()
                
                # 3. Add indicators to data
                ohlcv_data_with_indicators = self.strategy_engine.add_indicators(ohlcv_data.copy(), strategy_config)
                latest_candle = ohlcv_data_with_indicators.iloc[-1]

                # 4. Check for stop-loss trigger (highest priority)
                if self.in_position and latest_candle['close'] <= self.stop_loss_price:
                    print(f"!!! STOP-LOSS TRIGGERED at ${self.stop_loss_price:.2f} !!!")
                    exit_price = latest_candle['close']
                    order_result = self.execution_handler.execute_order('sell', self.portfolio_manager.last_position_size, self.config.symbol)
                    if order_result:
                        self.portfolio_manager.update_balance_after_trade(exit_price, self.entry_price, self.portfolio_manager.last_position_size)
                        self.in_position = False
                        self.stop_loss_price = None
                        self.entry_price = 0.0
                    continue # Restart the loop

                # 5. Get signals and sentiment
                current_sentiment = self.sentiment_analyzer.analyze()
                signal_details = self.strategy_engine.generate_signal(ohlcv_data_with_indicators, strategy_config, current_sentiment)
                signal = signal_details.get('signal')

                # 6. Act on signals
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
            time.sleep(3600) # Wait for the next candle

if __name__ == '__main__':
    config = ConfigurationManager()

    # --- Command-line argument to switch between live trading and backtesting ---
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
            # Allow specifying a start date from the command line, e.g., "python main.py backtest 2023-01-01"
            start_date_str = sys.argv[2] if len(sys.argv) > 2 else "2023-01-01"
            backtester = Backtester(config, strategy_conf, start_date_str)
            backtester.run()
        else:
            print(f"Backtesting for strategy '{strategy_name}' not implemented.")
    else:
        trader = Trader(config)
        trader.run()

