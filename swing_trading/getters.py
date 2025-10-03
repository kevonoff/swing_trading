import ccxt
from typing import List, Dict, Optional, Any

class CCTXClient:
    """
    A generic Python client that encapsulates basic public API functionality
    for any CCXT-supported cryptocurrency exchange.

    This client handles the exchange instantiation and provides wrappers 
    for common market data retrieval methods.
    """

    def __init__(self, exchange_id: str, config: Optional[Dict] = None):
        """
        Initializes the client with a specific exchange.

        Args:
            exchange_id (str): The ID of the exchange (e.g., 'binance', 'kraken').
            config (dict, optional): Configuration options for the exchange
                                     (e.g., {'rateLimit': 1000}). Defaults to None.
        """
        if exchange_id not in ccxt.exchanges:
            raise ValueError(f"Exchange ID '{exchange_id}' is not supported by CCXT.")
        
        # Get the exchange class from ccxt module
        exchange_class = getattr(ccxt, exchange_id)
        
        # Instantiate the exchange
        self.exchange = exchange_class(config if config is not None else {})
        
        print(f"Initialized client for exchange: {self.exchange.name}")

    def get_markets(self) -> Dict[str, Any]:
        """
        Retrieves the list of all available markets/trading pairs from the exchange.
        
        Returns:
            dict: A dictionary of markets indexed by symbol (e.g., 'BTC/USDT').
        """
        # Load markets, this is often required before other calls
        try:
            return self.exchange.load_markets()
        except ccxt.NetworkError as e:
            print(f"Network error: {e}")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred while loading markets: {e}")
            return {}


    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches the current price ticker for a single symbol.

        Args:
            symbol (str): The unified market symbol (e.g., 'BTC/USDT').

        Returns:
            dict: The standardized ticker data.
        """
        try:
            return self.exchange.fetch_ticker(symbol)
        except ccxt.ExchangeError as e:
            print(f"Exchange error fetching ticker for {symbol}: {e}")
            return {}
        except Exception as e:
            print(f"An error occurred: {e}")
            return {}


    def fetch_order_book(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetches the order book (bids and asks) for a market.

        Args:
            symbol (str): The unified market symbol (e.g., 'BTC/USDT').
            limit (int, optional): The maximum number of bids and asks to return.

        Returns:
            dict: The standardized order book data.
        """
        try:
            return self.exchange.fetch_order_book(symbol, limit=limit)
        except Exception as e:
            print(f"An error occurred while fetching order book: {e}")
            return {}

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: Optional[int] = None) -> List[List]:
        """
        Fetches Open, High, Low, Close, Volume (OHLCV) candlestick data.

        Args:
            symbol (str): The unified market symbol (e.g., 'BTC/USDT').
            timeframe (str): The duration of candles (e.g., '1m', '5m', '1h', '1d').
            limit (int, optional): The number of candles to return.

        Returns:
            list: A list of OHLCV arrays: [[timestamp, open, high, low, close, volume], ...].
        """
        try:
            # Note: CCXT timestamps are in milliseconds
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            print(f"An error occurred while fetching OHLCV: {e}")
            return []
        