import pandas as pd
import numpy as np
from config import ConfigurationManager
from data_handler import DataHandler
from strategy_engine import StrategyEngine
from portfolio_manager import PortfolioManager

class Backtester:
    """
    Simulates a trading strategy on historical data to evaluate performance.
    """
    def __init__(self, config: ConfigurationManager, strategy_config: dict, start_date: str):
        self.config = config
        self.strategy_config = strategy_config
        self.start_date = start_date
        
        self.data_handler = DataHandler(config)
        self.strategy_engine = StrategyEngine()
        # Use a fresh PortfolioManager instance for each backtest run
        self.portfolio_manager = PortfolioManager(config)
        
        self.trades = []
        
    def run(self):
        """
        Executes the backtest from start to finish.
        """
        print("\n" + "="*25 + " BACKTESTING " + "="*25)
        print(f"Strategy: {self.strategy_config['name']}")
        print(f"Timeframe: {self.config.timeframe}")
        print(f"Start Date: {self.start_date}")
        print("="*63 + "\n")

        # 1. Fetch historical data
        historical_data = self.data_handler.fetch_historical_data(self.start_date)
        if historical_data.empty:
            print("Could not fetch historical data. Aborting backtest.")
            return
            
        # 2. Add technical indicators to the entire dataset
        data_with_indicators = self.strategy_engine.add_indicators(historical_data, self.strategy_config)

        # 3. Loop through the data and simulate trading
        in_position = False
        entry_price = 0.0
        stop_loss_price = None
        position_size = 0.0
        entry_time = None

        for i, row in data_with_indicators.iterrows():
            # NOTE: For backtesting, we mock the sentiment. A future enhancement could be
            # to use a historical sentiment data source.
            mock_sentiment = {'sentiment_score': 0.1, 'sentiment_label': 'NEUTRAL'}

            # Check for stop-loss first
            if in_position and row['close'] <= stop_loss_price:
                exit_price = row['close']
                self.portfolio_manager.update_balance_after_trade(exit_price, entry_price, position_size)
                self.trades.append({'entry_date': entry_time, 'exit_date': row['timestamp'], 'pnl': (exit_price - entry_price) * position_size})
                in_position = False
                continue

            # Generate signal based on data up to the current point
            signal_details = self.strategy_engine.generate_signal(data_with_indicators.iloc[:i+1], self.strategy_config, mock_sentiment)
            signal = signal_details.get('signal')

            # Act on the signal
            if signal == 'buy' and not in_position:
                entry_price = row['close']
                entry_time = row['timestamp']
                stop_loss_price = signal_details.get('stop_loss')
                if not stop_loss_price: continue

                position_size = self.portfolio_manager.calculate_position_size(entry_price, stop_loss_price)
                if position_size > 0:
                    in_position = True

            elif signal == 'sell' and in_position:
                exit_price = row['close']
                self.portfolio_manager.update_balance_after_trade(exit_price, entry_price, position_size)
                self.trades.append({'entry_date': entry_time, 'exit_date': row['timestamp'], 'pnl': (exit_price - entry_price) * position_size})
                in_position = False

        # 4. Generate a final report
        self._generate_report()

    def _generate_report(self):
        """
        Calculates and prints key performance metrics of the backtest.
        """
        print("\n" + "="*25 + " BACKTEST REPORT " + "="*24)
        if not self.trades:
            print("No trades were executed during the backtest period.")
            return

        pnl_values = [trade['pnl'] for trade in self.trades]
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]

        total_return = (self.portfolio_manager.balance / self.portfolio_manager.initial_balance - 1) * 100
        num_trades = len(self.trades)
        win_rate = (len(wins) / num_trades) * 100 if num_trades > 0 else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        reward_risk_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf
        
        print(f"  Ending Balance:       ${self.portfolio_manager.balance:,.2f}")
        print(f"  Total Return:         {total_return:.2f}%")
        print(f"  Total Trades:         {num_trades}")
        print(f"  Win Rate:             {win_rate:.2f}%")
        print(f"  Average Win:          ${avg_win:,.2f}")
        print(f"  Average Loss:         ${avg_loss:,.2f}")
        print(f"  Reward/Risk Ratio:    {reward_risk_ratio:.2f}")
        print("="*63 + "\n")

