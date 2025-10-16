"""Hierarchical Risk Parity portfolio allocation with correlation guards."""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from src.core.positions import PositionManager

logger = logging.getLogger(__name__)


class PortfolioAllocator:
    """
    HRP-based portfolio allocation with correlation clamps and currency exposure caps.

    Implements:
    - Hierarchical Risk Parity for optimal risk distribution
    - Correlation clamp (reduce risk if |rho| > threshold)
    - Per-currency exposure caps
    """

    def __init__(
        self,
        position_manager: PositionManager,
        max_corr_abs: float = 0.8,
        per_currency_risk_cap_pct: float = 6.0,
        lookback_days: int = 90,
        fallback_days: int = 30,
    ):
        """
        Initialize portfolio allocator.

        Args:
            position_manager: Position manager instance
            max_corr_abs: Maximum absolute correlation before scaling
            per_currency_risk_cap_pct: Max concurrent risk per currency
            lookback_days: Primary lookback for correlation matrix
            fallback_days: Fallback lookback if insufficient data
        """
        self.position_manager = position_manager
        self.max_corr_abs = max_corr_abs
        self.per_currency_risk_cap_pct = per_currency_risk_cap_pct
        self.lookback_days = lookback_days
        self.fallback_days = fallback_days

        # Price history for correlation calculation
        self.price_history: Dict[str, List[Tuple[float, float]]] = {}  # symbol -> [(timestamp, price)]

        logger.info(
            f"Portfolio allocator initialized: max_corr={max_corr_abs}, "
            f"currency_cap={per_currency_risk_cap_pct}%"
        )

    def calculate_correlation_matrix(
        self,
        symbols: List[str],
    ) -> Optional[np.ndarray]:
        """
        Calculate correlation matrix for symbols.

        Args:
            symbols: List of symbols

        Returns:
            Correlation matrix or None if insufficient data
        """
        if len(symbols) < 2:
            return None

        # Get returns for each symbol
        returns_dict = {}

        for symbol in symbols:
            if symbol not in self.price_history or len(self.price_history[symbol]) < self.fallback_days:
                # Insufficient data
                continue

            prices = [p[1] for p in self.price_history[symbol][-self.lookback_days:]]
            returns = np.diff(np.log(prices))
            returns_dict[symbol] = returns

        if len(returns_dict) < 2:
            return None

        # Align returns (use shortest length)
        min_len = min(len(r) for r in returns_dict.values())
        returns_df = pd.DataFrame({s: r[-min_len:] for s, r in returns_dict.items()})

        # Calculate correlation matrix
        corr_matrix = returns_df.corr().values

        return corr_matrix

    def hierarchical_risk_parity(
        self,
        symbols: List[str],
        corr_matrix: np.ndarray,
    ) -> Dict[str, float]:
        """
        Calculate HRP weights for symbols.

        Args:
            symbols: List of symbols
            corr_matrix: Correlation matrix

        Returns:
            Dictionary mapping symbol to weight (0-1)
        """
        if corr_matrix is None or len(symbols) != corr_matrix.shape[0]:
            # Equal weight fallback
            equal_weight = 1.0 / len(symbols) if symbols else 0.0
            return {s: equal_weight for s in symbols}

        # Convert correlation to distance
        dist_matrix = np.sqrt(0.5 * (1 - corr_matrix))
        np.fill_diagonal(dist_matrix, 0)

        # Hierarchical clustering
        condensed_dist = squareform(dist_matrix)
        linkage_matrix = linkage(condensed_dist, method="single")

        # Get quasi-diagonalization order
        sorted_idx = self._get_quasi_diag(linkage_matrix)

        # Recursive bisection for weights
        weights = np.ones(len(symbols))
        weights = self._recursive_bisection(weights, sorted_idx, corr_matrix)

        # Normalize
        weights = weights / weights.sum()

        return {symbols[i]: weights[i] for i in range(len(symbols))}

    def _get_quasi_diag(self, linkage_matrix: np.ndarray) -> List[int]:
        """Get quasi-diagonal order from linkage matrix."""
        sorted_idx = []
        self._get_quasi_diag_recursive(linkage_matrix, sorted_idx, [len(linkage_matrix) + 1])
        return sorted_idx

    def _get_quasi_diag_recursive(
        self,
        linkage_matrix: np.ndarray,
        sorted_idx: List[int],
        cluster_idx: List[int],
    ) -> None:
        """Recursive helper for quasi-diagonalization."""
        while cluster_idx:
            cluster = cluster_idx.pop(0)
            if cluster < len(linkage_matrix) + 1:
                sorted_idx.append(cluster)
            else:
                cluster_children = linkage_matrix[cluster - len(linkage_matrix) - 1, :2].astype(int)
                cluster_idx.extend([cluster_children[0], cluster_children[1]])

    def _recursive_bisection(
        self,
        weights: np.ndarray,
        sorted_idx: List[int],
        corr_matrix: np.ndarray,
    ) -> np.ndarray:
        """Recursive bisection to calculate weights."""
        if len(sorted_idx) == 1:
            return weights

        # Split into two clusters
        mid = len(sorted_idx) // 2
        left_idx = sorted_idx[:mid]
        right_idx = sorted_idx[mid:]

        # Calculate cluster variances
        left_var = self._cluster_variance(left_idx, corr_matrix)
        right_var = self._cluster_variance(right_idx, corr_matrix)

        # Allocate weights inversely proportional to variance
        total_var = left_var + right_var
        if total_var > 0:
            left_weight = 1.0 - (left_var / total_var)
            right_weight = 1.0 - (right_var / total_var)
        else:
            left_weight = right_weight = 0.5

        # Normalize
        total_weight = left_weight + right_weight
        if total_weight > 0:
            left_weight /= total_weight
            right_weight /= total_weight

        # Apply weights and recurse
        weights[left_idx] *= left_weight
        weights[right_idx] *= right_weight

        if len(left_idx) > 1:
            weights = self._recursive_bisection(weights, left_idx, corr_matrix)
        if len(right_idx) > 1:
            weights = self._recursive_bisection(weights, right_idx, corr_matrix)

        return weights

    def _cluster_variance(self, cluster_idx: List[int], corr_matrix: np.ndarray) -> float:
        """Calculate variance for a cluster of assets."""
        if len(cluster_idx) == 0:
            return 0.0

        cluster_corr = corr_matrix[np.ix_(cluster_idx, cluster_idx)]
        # Assume equal variance for simplicity
        cluster_var = cluster_corr.sum() / len(cluster_idx)

        return max(cluster_var, 0.0)

    def check_correlation_clamp(
        self,
        symbol: str,
        open_symbols: List[str],
    ) -> Tuple[bool, float, str]:
        """
        Check if new symbol should be correlation-clamped.

        Args:
            symbol: Symbol to check
            open_symbols: Currently open symbols

        Returns:
            (should_clamp, scale_factor, reason)
        """
        if not open_symbols:
            return False, 1.0, "No open positions"

        symbols_to_check = [symbol] + open_symbols
        corr_matrix = self.calculate_correlation_matrix(symbols_to_check)

        if corr_matrix is None:
            return False, 1.0, "Insufficient correlation data"

        # Check correlation with existing positions
        new_symbol_idx = 0
        max_corr = 0.0

        for i in range(1, len(symbols_to_check)):
            corr = abs(corr_matrix[new_symbol_idx, i])
            if corr > max_corr:
                max_corr = corr

        if max_corr > self.max_corr_abs:
            # Scale risk to 50% if highly correlated
            return True, 0.5, f"|rho|={max_corr:.2f} > {self.max_corr_abs}"

        return False, 1.0, f"Max |rho|={max_corr:.2f} OK"

    def check_currency_exposure_cap(
        self,
        symbol: str,
        proposed_risk_pct: float,
        balance: float,
    ) -> Tuple[bool, str]:
        """
        Check if adding position would exceed per-currency risk cap.

        Args:
            symbol: Symbol to check
            proposed_risk_pct: Proposed risk percentage
            balance: Account balance

        Returns:
            (approved, reason)
        """
        # Extract currencies from symbol
        currencies = self._get_symbol_currencies(symbol)

        # Get current currency exposures
        current_exposure = self._calculate_currency_exposure()

        # Check if adding this would exceed caps
        proposed_risk_amount = balance * (proposed_risk_pct / 100.0)

        for currency in currencies:
            current = current_exposure.get(currency, 0.0)
            projected = current + proposed_risk_amount
            projected_pct = (projected / balance) * 100.0

            if projected_pct > self.per_currency_risk_cap_pct:
                return (
                    False,
                    f"{currency} exposure {projected_pct:.1f}% > cap {self.per_currency_risk_cap_pct:.1f}%",
                )

        return True, "Currency exposure within caps"

    def _get_symbol_currencies(self, symbol: str) -> List[str]:
        """Extract currencies from symbol."""
        symbol = symbol.upper()

        # FX pairs
        if len(symbol) == 6:
            return [symbol[:3], symbol[3:]]

        # Indices, commodities
        if symbol.startswith("US") or symbol.startswith("XAU") or symbol.startswith("XAG"):
            return ["USD"]
        if symbol.startswith("UK") or symbol.startswith("FTSE"):
            return ["GBP"]
        if symbol.startswith("DE") or symbol.startswith("DAX") or symbol.startswith("EU"):
            return ["EUR"]
        if symbol.startswith("JP"):
            return ["JPY"]

        return []

    def _calculate_currency_exposure(self) -> Dict[str, float]:
        """Calculate current risk exposure by currency."""
        exposure = {}

        for idea in self.position_manager.get_all_open_ideas():
            currencies = self._get_symbol_currencies(idea.symbol)
            for currency in currencies:
                exposure[currency] = exposure.get(currency, 0.0) + idea.risk_amount

        return exposure

    def update_price_history(self, symbol: str, price: float, timestamp: float) -> None:
        """
        Update price history for correlation calculations.

        Args:
            symbol: Symbol
            price: Current price
            timestamp: Timestamp
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append((timestamp, price))

        # Keep only recent history
        max_points = self.lookback_days * 24  # Hourly data
        if len(self.price_history[symbol]) > max_points:
            self.price_history[symbol] = self.price_history[symbol][-max_points:]

    def get_summary(self) -> Dict:
        """Get portfolio allocator summary."""
        open_ideas = self.position_manager.get_all_open_ideas()
        symbols = list(set(idea.symbol for idea in open_ideas))

        currency_exposure = self._calculate_currency_exposure()

        return {
            "symbols_tracked": len(self.price_history),
            "open_symbols": len(symbols),
            "currency_exposure": currency_exposure,
            "max_corr_threshold": self.max_corr_abs,
            "per_currency_cap_pct": self.per_currency_risk_cap_pct,
        }
