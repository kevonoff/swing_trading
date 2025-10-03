from config import ConfigurationManager

class PortfolioManager:
    """
    Manages the portfolio's state, including balance, open positions, and risk.
    """
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.balance = self.config.capital_base
        self.current_position = None # Will hold details of the open trade

    def update_balance(self, pnl: float):
        """
        Updates the portfolio balance with the profit or loss from a closed trade.
        """
        self.balance += pnl
        print(f"Portfolio updated. PnL: ${pnl:.2f}, New Balance: ${self.balance:.2f}")

    def calculate_position_size(self, current_price: float, stop_loss_price: float) -> float:
        """
        Calculates the position size in the base currency (e.g., BTC).
        """
        risk_per_trade_decimal = self.config.risk_per_trade_percent / 100
        capital_to_risk = self.balance * risk_per_trade_decimal
        
        stop_loss_distance = current_price - stop_loss_price

        # --- BUG FIX ---
        # Prevent a ZeroDivisionError in the unlikely event price equals stop-loss.
        if stop_loss_distance <= 0:
            print(f"Warning: Stop loss ({stop_loss_price}) is not below the current price ({current_price}). Cannot calculate position size.")
            return 0.0
        # --- END BUG FIX ---

        position_size_usd = capital_to_risk / (stop_loss_distance / current_price)
        position_size_asset = position_size_usd / current_price
        
        return position_size_asset

    def open_position(self, symbol: str, size: float, entry_price: float, stop_loss: float):
        """
        Records the details of a new open position.
        """
        self.current_position = {
            "symbol": symbol,
            "size": size,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
        }
        print(f"Position opened: {size:.6f} {symbol} at ${entry_price:.2f} with stop-loss at ${stop_loss:.2f}")

    def close_position(self, exit_price: float):
        """
        Closes the current position and calculates the Profit and Loss (PnL).
        """
        if not self.current_position:
            return

        entry_price = self.current_position['entry_price']
        size = self.current_position['size']
        
        pnl = (exit_price - entry_price) * size
        self.update_balance(pnl)
        
        self.current_position = None
        print(f"Position closed at ${exit_price:.2f}")

