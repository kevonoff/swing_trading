import pandas as pd
import pandas_ta as ta

class StrategyEngine:
    """
    A generic engine to handle various trading strategies.
    It calculates indicators and generates signals based on a
    dynamic strategy configuration object.
    """

    def calculate_indicators(self, ohlcv_df: pd.DataFrame, strategy_config: dict) -> pd.DataFrame:
        """
        Calculates and appends the necessary technical indicators to the dataframe
        based on the provided strategy configuration.
        """
        strategy_name = strategy_config.get('name')
        params = strategy_config.get('params', {})
        print(f"Calculating indicators for strategy: {strategy_name}...")

        if strategy_name == 'SENTIMENT_MOMENTUM':
            ohlcv_df.ta.atr(length=params.get('atr_period', 14), append=True)
            ohlcv_df['short_sma'] = ohlcv_df['close'].rolling(window=params.get('short_window', 10)).mean()
            ohlcv_df['long_sma'] = ohlcv_df['close'].rolling(window=params.get('long_window', 30)).mean()

        elif strategy_name == 'MEAN_REVERSION':
            # Example of calculating indicators for a different strategy
            # ohlcv_df.ta.bbands(length=params.get('bollinger_period', 20), append=True)
            # ohlcv_df.ta.rsi(length=params.get('rsi_period', 14), append=True)
            pass

        elif strategy_name == 'BREAKOUT':
            # Example of calculating indicators for another strategy
            # ohlcv_df.ta.donchian(lower_length=params.get('donchian_period', 20), upper_length=params.get('donchian_period', 20), append=True)
            pass
        
        return ohlcv_df

    def generate_signal(self, ohlcv_df: pd.DataFrame, strategy_config: dict, sentiment: str = 'neutral') -> str:
        """
        Main signal dispatcher. It routes to the correct strategy logic
        based on the strategy configuration object.
        """
        strategy_name = strategy_config.get('name')
        params = strategy_config.get('params', {})

        if strategy_name == 'SENTIMENT_MOMENTUM':
            return self._generate_sentiment_momentum_signal(ohlcv_df, params, sentiment)
        elif strategy_name == 'MEAN_REVERSION':
            return self._generate_mean_reversion_signal(ohlcv_df, params)
        elif strategy_name == 'BREAKOUT':
            return self._generate_breakout_signal(ohlcv_df, params)
        else:
            print(f"Warning: Strategy '{strategy_name}' not recognized.")
            return 'hold'

    def _generate_sentiment_momentum_signal(self, ohlcv_df: pd.DataFrame, params: dict, sentiment: str) -> str:
        """ Logic for the Sentiment Momentum Crossover strategy. """
        print("Analyzing with Sentiment Momentum strategy...")
        latest = ohlcv_df.iloc[-1]
        previous = ohlcv_df.iloc[-2]

        # Check if required columns exist
        if 'short_sma' not in latest or 'long_sma' not in latest:
            return 'hold'

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
    
    def _generate_mean_reversion_signal(self, ohlcv_df: pd.DataFrame, params: dict) -> str:
        """ Placeholder for Mean Reversion logic. """
        print("Analyzing with Mean Reversion strategy (Placeholder)...")
        # Example logic: Buy if price touches lower Bollinger Band and RSI is oversold.
        return 'hold'
        
    def _generate_breakout_signal(self, ohlcv_df: pd.DataFrame, params: dict) -> str:
        """ Placeholder for Breakout logic. """
        print("Analyzing with Breakout strategy (Placeholder)...")
        # Example logic: Buy if price breaks above the upper Donchian Channel on high volume.
        return 'hold'
