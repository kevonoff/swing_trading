import time
import argparse
from config import ConfigurationManager
from data_handler import DataHandler
from strategy_engine import StrategyEngine
from portfolio_manager import PortfolioManager
from execution_handler import ExecutionHandler
from backtester import Backtester

class SentimentAnalyzer:
    """
    The main class that orchestrates the entire trading process.
    """
    def __init__(self, run_backtest=False):
        self.config = ConfigurationManager()
        self.data_handler = DataHandler(self.config)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.strategy_engine = StrategyEngine()
        self.portfolio_manager = PortfolioManager(self.config)
        self.execution_handler = ExecutionHandler(self.config)
        
        self.in_position = False
        self.current_position = None

        if run_backtest:
            self.run_backtest()
        else:
            self.run_live()

    def run_live(self):
        """Main loop for the live trading bot."""
        print("Starting live trading bot...")
        while True:
            try:
                # 1. Fetch latest market data
                market_data = self.data_handler.fetch_latest_data()
                if market_data.empty:
                    print("Could not fetch market data. Waiting for next cycle.")
                    time.sleep(3600)
                    continue

                current_price = market_data.iloc[-1]['close']

                # 2. Check stop-loss
                if self.in_position:
                    if current_price <= self.current_position['stop_loss']:
                        print(f"Stop-loss triggered at {current_price}. Selling position.")
                        self.execution_handler.execute_sell(self.current_position)
                        self.portfolio_manager.record_trade_close(
                            self.current_position,
                            exit_price=current_price
                        )
                        self.in_position = False
                        self.current_position = None
                        print("-" * 50)
                
                # 3. Get strategy signal
                strategy_config = self.config.get_strategy_config()
                trade_signal = self.strategy_engine.generate_signal(market_data.copy(), strategy_config)

                # 4. Get sentiment analysis
                # --- FIX ---
                sentiment_data = self.sentiment_analyzer.get_current_market_sentiment()
                # --- END FIX ---
                sentiment_score = sentiment_data['sentiment_score']
                
                print(f"Current Price: {current_price} | Signal: {trade_signal.signal} | Sentiment: {sentiment_score:.2f}")

                # 5. Execute based on signal and sentiment
                if trade_signal.signal == 'BUY' and not self.in_position:
                    if sentiment_score >= 0.5: # Only buy if sentiment is not negative
                        print("Buy signal received with positive sentiment. Executing trade.")
                        trade = self.portfolio_manager.calculate_position_size(trade_signal)
                        self.execution_handler.execute_buy(trade)
                        self.in_position = True
                        self.current_position = trade
                    else:
                        print("Buy signal received, but sentiment is negative. Holding.")
                
                elif trade_signal.signal == 'SELL' and self.in_position:
                    print("Sell signal received. Closing position.")
                    self.execution_handler.execute_sell(self.current_position)
                    self.portfolio_manager.record_trade_close(
                        self.current_position,
                        exit_price=current_price
                    )
                    self.in_position = False
                    self.current_position = None
                
                print(f"Current Portfolio Balance: ${self.portfolio_manager.get_balance():.2f}")
                print("-" * 50)
                
            except Exception as e:
                print(f"An unexpected error occurred in the main loop: {e}")
            
            # Wait for the next candle
            print("Waiting for the next 1-hour candle...")
            time.sleep(3600)

    def run_backtest(self):
        """Initializes and runs the backtester."""
        print("Initializing backtester...")
        backtester = Backtester(
            config=self.config,
            data_handler=self.data_handler,
            strategy_engine=self.strategy_engine,
            portfolio_manager=self.portfolio_manager
        )
        backtester.run()