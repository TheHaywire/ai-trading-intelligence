"""Financial calculation utilities."""

from typing import Optional


def calculate_position_value(
    lots: float,
    contract_size: float,
    price: float,
) -> float:
    """
    Calculate notional position value.

    Args:
        lots: Position size in lots
        contract_size: Contract size (e.g., 100,000 for standard FX lot)
        price: Current price

    Returns:
        Notional value in account currency
    """
    return lots * contract_size * price


def calculate_pip_value(
    lots: float,
    contract_size: float,
    pip_size: float,
    conversion_rate: float = 1.0,
) -> float:
    """
    Calculate the monetary value of one pip.

    Args:
        lots: Position size in lots
        contract_size: Contract size
        pip_size: Size of one pip (e.g., 0.0001 for most FX pairs)
        conversion_rate: Rate to convert to account currency

    Returns:
        Value of one pip in account currency
    """
    return lots * contract_size * pip_size * conversion_rate


def calculate_risk_amount(
    lots: float,
    entry_price: float,
    stop_loss: float,
    pip_value: float,
) -> float:
    """
    Calculate the risk amount for a position.

    Args:
        lots: Position size in lots
        entry_price: Entry price
        stop_loss: Stop loss price
        pip_value: Value of one pip

    Returns:
        Risk amount in account currency
    """
    price_diff = abs(entry_price - stop_loss)
    return price_diff * pip_value / (pip_value / lots)


def calculate_risk_percent(
    risk_amount: float,
    balance: float,
) -> float:
    """
    Calculate risk as a percentage of balance.

    Args:
        risk_amount: Risk amount in account currency
        balance: Account balance

    Returns:
        Risk percentage (0-100)
    """
    return (risk_amount / balance) * 100.0 if balance > 0 else 0.0


def calculate_lot_size_for_risk(
    balance: float,
    risk_percent: float,
    stop_distance_pips: float,
    pip_value_per_lot: float,
) -> float:
    """
    Calculate lot size to achieve target risk percentage.

    Args:
        balance: Account balance
        risk_percent: Desired risk percentage (0-100)
        stop_distance_pips: Distance to stop loss in pips
        pip_value_per_lot: Value of one pip for 1 standard lot

    Returns:
        Lot size to achieve target risk
    """
    risk_amount = balance * (risk_percent / 100.0)
    if stop_distance_pips == 0 or pip_value_per_lot == 0:
        return 0.0
    return risk_amount / (stop_distance_pips * pip_value_per_lot)


def calculate_margin_required(
    lots: float,
    contract_size: float,
    price: float,
    leverage: int,
) -> float:
    """
    Calculate margin required for a position.

    Args:
        lots: Position size in lots
        contract_size: Contract size
        price: Current price
        leverage: Account leverage

    Returns:
        Margin required in account currency
    """
    notional = calculate_position_value(lots, contract_size, price)
    return notional / leverage if leverage > 0 else notional


def calculate_drawdown_percent(
    starting_balance: float,
    current_equity: float,
) -> float:
    """
    Calculate drawdown percentage.

    Args:
        starting_balance: Initial balance
        current_equity: Current equity

    Returns:
        Drawdown percentage (positive value for losses)
    """
    if starting_balance == 0:
        return 0.0
    loss = starting_balance - current_equity
    return (loss / starting_balance) * 100.0


def calculate_profit_percent(
    starting_balance: float,
    current_equity: float,
) -> float:
    """
    Calculate profit percentage.

    Args:
        starting_balance: Initial balance
        current_equity: Current equity

    Returns:
        Profit percentage (can be negative for losses)
    """
    if starting_balance == 0:
        return 0.0
    gain = current_equity - starting_balance
    return (gain / starting_balance) * 100.0


def normalize_lot_size(
    lots: float,
    min_lot: float = 0.01,
    max_lot: float = 100.0,
    step: float = 0.01,
) -> float:
    """
    Normalize lot size to broker's constraints.

    Args:
        lots: Desired lot size
        min_lot: Minimum allowed lot size
        max_lot: Maximum allowed lot size
        step: Lot size step (increment)

    Returns:
        Normalized lot size
    """
    # Clamp to min/max
    lots = max(min_lot, min(max_lot, lots))

    # Round to step
    steps = round(lots / step)
    return steps * step
