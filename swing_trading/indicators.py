import pandas as pd
import pandas_ta as ta

def prepare_dataframe(ohlcv: list) -> pd.DataFrame:
    """
    Converts raw OHLCV data from CCXT into a standardized Pandas DataFrame.

    Args:
        ohlcv: A list of lists containing OHLCV data from CCXT.
               [[timestamp, open, high, low, close, volume], ...]

    Returns:
        A Pandas DataFrame with appropriate column names and a datetime index.
    """
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def add_ma_crossover(df: pd.DataFrame, short_window: int = 50, long_window: int = 200) -> pd.DataFrame:
    """
    Calculates and adds short and long-period Simple Moving Averages (SMA).

    Args:
        df: The OHLCV DataFrame.
        short_window: The lookback period for the short SMA.
        long_window: The lookback period for the long SMA.

    Returns:
        The DataFrame with 'SMA_short' and 'SMA_long' columns added.
    """
    df.ta.sma(length=short_window, append=True, col_names=(f'SMA_{short_window}'))
    df.ta.sma(length=long_window, append=True, col_names=(f'SMA_{long_window}'))
    return df

def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculates and adds the Relative Strength Index (RSI).

    Args:
        df: The OHLCV DataFrame.
        period: The lookback period for the RSI calculation.

    Returns:
        The DataFrame with the 'RSI' column added.
    """
    df.ta.rsi(length=period, append=True, col_names=(f'RSI_{period}'))
    return df

def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculates and adds the Moving Average Convergence Divergence (MACD).

    Args:
        df: The OHLCV DataFrame.
        fast: The fast period for the EMA.
        slow: The slow period for the EMA.
        signal: The signal period for the EMA of the MACD line.

    Returns:
        The DataFrame with MACD, MACD Histogram, and MACD Signal columns.
    """
    df.ta.macd(fast=fast, slow=slow, signal=signal, append=True)
    return df

def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """
    Calculates and adds Bollinger Bands (upper, middle, lower).

    Args:
        df: The OHLCV DataFrame.
        period: The lookback period for the moving average.
        std_dev: The number of standard deviations for the bands.

    Returns:
        The DataFrame with Bollinger Band columns added.
    """
    df.ta.bbands(length=period, std=std_dev, append=True)
    return df

def calculate_fibonacci_retracement(df: pd.DataFrame) -> dict:
    """
    Calculates Fibonacci retracement levels based on the highest high and lowest low.

    Args:
        df: The OHLCV DataFrame for the period of interest.

    Returns:
        A dictionary containing the price at each Fibonacci level.
    """
    high_price = df['high'].max()
    low_price = df['low'].min()
    price_diff = high_price - low_price

    levels = {
        'level_0.0': high_price,
        'level_23.6': high_price - price_diff * 0.236,
        'level_38.2': high_price - price_diff * 0.382,
        'level_50.0': high_price - price_diff * 0.5,
        'level_61.8': high_price - price_diff * 0.618,
        'level_78.6': high_price - price_diff * 0.786,
        'level_100.0': low_price,
    }
    return levels

if __name__ == '__main__':
    # Example usage with sample data mimicking CCXT's fetch_ohlcv output
    # [[timestamp, open, high, low, close, volume], ...]
    sample_ohlcv = [
        [1727740800000, 100, 102, 98, 101, 1000],
        [1727827200000, 101, 105, 100, 104, 1200],
        [1727913600000, 104, 110, 103, 109, 1500],
        [1728000000000, 109, 112, 107, 108, 1300],
        [1728086400000, 108, 115, 108, 114, 1800],
        [1728172800000, 114, 114, 110, 111, 1600],
        [1728259200000, 111, 113, 109, 112, 1400]
    ]

    # 1. Prepare the DataFrame
    my_df = prepare_dataframe(sample_ohlcv)
    print("--- Initial DataFrame ---")
    print(my_df.head())

    # 2. Add indicators (using shorter periods for small sample)
    my_df = add_ma_crossover(my_df, short_window=2, long_window=4)
    my_df = add_rsi(my_df, period=3)
    my_df = add_macd(my_df, fast=2, slow=4, signal=2)
    my_df = add_bollinger_bands(my_df, period=3, std_dev=2)

    print("\n--- DataFrame with Indicators ---")
    print(my_df)

    # 3. Calculate Fibonacci Retracement levels
    fib_levels = calculate_fibonacci_retracement(my_df)
    print("\n--- Fibonacci Retracement Levels ---")
    for level, price in fib_levels.items():
        print(f"{level}: ${price:.2f}")