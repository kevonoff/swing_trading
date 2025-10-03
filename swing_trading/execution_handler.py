from config import ConfigurationManager

class PortfolioManager:
    """
    Manages the portfolio's state, including balance, P&L, and position sizing.
    """
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.balance = self.config.capital_base
        self.initial_balance = self.config.capital_base
        self.last_position_size = 0.0
        self.realized_pnl = 0.0

    def calculate_position_size(self, entry_price: float, stop_loss_price: float):
        """
        Calculates the position size based on a fixed percentage of the total balance.
        """
        if stop_loss_price >= entry_price:
            print("Error: Stop-loss price must be below entry price. Cannot calculate position size.")
            return 0.0

        risk_amount_dollars = self.balance * (self.config.risk_per_trade_percent / 100.0)
        risk_per_coin_dollars = entry_price - stop_loss_price
        
        if risk_per_coin_dollars <= 0:
            return 0.0

        position_size = risk_amount_dollars / risk_per_coin_dollars
        print(f"Calculated Position Size ({self.config.symbol.split('/')[0]}): {position_size:.6f} for a risk of ${risk_amount_dollars:.2f}")
        self.last_position_size = position_size
        return position_size

    def update_balance_after_trade(self, exit_price: float, entry_price: float, position_size: float):
        """ 
        Updates the balance after closing a position and prints trade summary. 
        """
        pnl = (exit_price - entry_price) * position_size
        self.balance += pnl
        self.realized_pnl += pnl
        print("=" * 20 + " TRADE CLOSED " + "=" * 20)
        print(f"  P&L for this trade: ${pnl:.2f}")
        print(f"  New Portfolio Balance: ${self.balance:.2f}")
        print(f"  Total Realized P&L: ${self.realized_pnl:.2f}")
        print("=" * 54)
