import pandas as pd
import pandas_ta as ta

class StrategyEngine:
    """
    The central engine for generating trading signals based on various strategies.
    It takes raw data, adds the necessary indicators, and applies strategy rules.
    """

    def add_indicators(self, ohlcv_df: pd.DataFrame, strategy_config: dict) -> pd.DataFrame:
        """
        Adds the required technical indicators to the DataFrame based on the strategy.
        """
        strategy_name = strategy_config.get("name")
        params = strategy_config.get("params", {})

        if strategy_name == 'SENTIMENT_MOMENTUM':
            # Add Simple Moving Averages (SMA)
            ohlcv_df['SMA_short'] = ta.sma(ohlcv_df['close'], length=params.get('short_window', 10))
            ohlcv_df['SMA_long'] = ta.sma(ohlcv_df['close'], length=params.get('long_window', 30))
            # Add Average True Range (ATR) for volatility and stop-loss
            ohlcv_df['ATR'] = ta.atr(ohlcv_df['high'], ohlcv_df['low'], ohlcv_df['close'], length=params.get('atr_period', 14))
        
        # Future strategies like 'MEAN_REVERSION' would add their indicators here
        # elif strategy_name == 'MEAN_REVERSION':
        #     bbands = ta.bbands(ohlcv_df['close'], length=params.get('bb_window', 20))
        #     ohlcv_df = ohlcv_df.join(bbands)

        ohlcv_df.dropna(inplace=True)
        
        # --- BUG FIX ---
        # If all rows were dropped, return the empty dataframe to prevent a crash.
        if ohlcv_df.empty:
            print("Warning: DataFrame is empty after adding indicators and dropping NaNs. Check indicator periods vs. data length.")
        # --- END BUG FIX ---
        
        return ohlcv_df

    def generate_signal(self, ohlcv_df_with_indicators: pd.DataFrame, strategy_config: dict, sentiment: dict) -> dict:
        """
        Generates a trading signal ('buy', 'sell', 'hold') based on the strategy logic.
        """
        # --- BUG FIX ---
        # If the dataframe is empty from the previous step, we can't generate a signal.
        if ohlcv_df_with_indicators.empty:
            return {"signal": "hold", "stop_loss": None}
        # --- END BUG FIX ---

        strategy_name = strategy_config.get("name")
        params = strategy_config.get("params", {})
        latest_candle = ohlcv_df_with_indicators.iloc[-1]
        
        signal_details = {"signal": "hold", "stop_loss": None}

        if strategy_name == 'SENTIMENT_MOMENTUM':
            # --- Entry Signal ---
            # Condition 1: Short-term SMA crosses above long-term SMA (Golden Cross)
            sma_cross_bullish = latest_candle['SMA_short'] > latest_candle['SMA_long']
            
            # Condition 2: Market sentiment is not negative
            sentiment_is_not_bearish = sentiment.get('sentiment_score', 0) >= -0.05
            
            if sma_cross_bullish and sentiment_is_not_bearish:
                signal_details["signal"] = "buy"
                # --- Stop-Loss Calculation ---
                # Place the stop-loss below the recent low, adjusted by ATR
                atr_value = latest_candle['ATR']
                stop_loss_price = latest_candle['low'] - (atr_value * params.get('atr_multiplier', 2.0))
                signal_details["stop_loss"] = stop_loss_price
                return signal_details

            # --- Exit Signal ---
            # Condition: Short-term SMA crosses below long-term SMA (Death Cross)
            sma_cross_bearish = latest_candle['SMA_short'] < latest_candle['SMA_long']
            if sma_cross_bearish:
                signal_details["signal"] = "sell"
                return signal_details
        
        return signal_details

