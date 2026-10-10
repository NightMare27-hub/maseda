"""
Core financial logic engine for the Algorithmic Investment Portfolio and Retirement Simulator.
Provides pure functions and data structures for compound growth, asset allocation metrics,
Monte Carlo simulations, and rebalancing recommendations.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class AssetAllocation:
    """Represents portfolio asset allocation percentages."""
    stocks: float  # e.g., 60.0 for 60%
    bonds: float   # e.g., 25.0 for 25%
    real_estate: float = 0.0  # e.g., 10.0 for 10%
    cash: float = 5.0        # e.g., 5.0 for 5%

    def validate(self) -> bool:
        """Validates that allocations sum approximately to 100% and are non-negative."""
        if self.stocks < 0 or self.bonds < 0 or self.real_estate < 0 or self.cash < 0:
            return False
        total = self.stocks + self.bonds + self.real_estate + self.cash
        return math.isclose(total, 100.0, abs_tol=1e-2)

    def to_dict(self) -> Dict[str, float]:
        """Converts allocation to a dictionary of fractional weights."""
        total = self.stocks + self.bonds + self.real_estate + self.cash
        if total <= 0:
            return {"stocks": 0.0, "bonds": 0.0, "real_estate": 0.0, "cash": 0.0}
        return {
            "stocks": self.stocks / total,
            "bonds": self.bonds / total,
            "real_estate": self.real_estate / total,
            "cash": self.cash / total,
        }


@dataclass
class PortfolioMetrics:
    """Calculated metrics for an asset allocation."""
    expected_return: float  # Annualized expected return (fraction, e.g., 0.08 for 8%)
    volatility: float       # Annualized standard deviation (fraction, e.g., 0.15 for 15%)
    sharpe_ratio: float     # Sharpe ratio based on risk-free rate
    diversification_score: float = 1.0  # Effective number of assets (inverse Herfindahl index)


def calculate_portfolio_metrics(
    allocation: AssetAllocation,
    expected_returns: Dict[str, float] = None,
    volatilities: Dict[str, float] = None,
    correlation_matrix: Dict[str, Dict[str, float]] = None,
    risk_free_rate: float = 0.02
) -> PortfolioMetrics:
    """
    Calculates weighted expected return, portfolio volatility (standard deviation),
    and Sharpe ratio given asset allocation and historical/assumed asset class parameters.
    """
    if expected_returns is None:
        expected_returns = {
            "stocks": 0.095,
            "bonds": 0.045,
            "real_estate": 0.075,
            "cash": 0.025
        }
    
    if volatilities is None:
        volatilities = {
            "stocks": 0.16,
            "bonds": 0.06,
            "real_estate": 0.12,
            "cash": 0.01
        }

    if correlation_matrix is None:
        # Default realistic asset correlation matrix
        correlation_matrix = {
            "stocks":      {"stocks": 1.0, "bonds": 0.2, "real_estate": 0.6, "cash": 0.0},
            "bonds":       {"stocks": 0.2, "bonds": 1.0, "real_estate": 0.1, "cash": 0.0},
            "real_estate": {"stocks": 0.6, "bonds": 0.1, "real_estate": 1.0, "cash": 0.0},
            "cash":        {"stocks": 0.0, "bonds": 0.0, "real_estate": 0.0, "cash": 1.0}
        }

    weights = allocation.to_dict()
    assets = ["stocks", "bonds", "real_estate", "cash"]

    # Calculate weighted expected return
    exp_return = sum(weights[asset] * expected_returns.get(asset, 0.0) for asset in assets)

    # Calculate portfolio variance
    portfolio_variance = 0.0
    for i, asset_i in enumerate(assets):
        for j, asset_j in enumerate(assets):
            w_i = weights[asset_i]
            w_j = weights[asset_j]
            vol_i = volatilities.get(asset_i, 0.0)
            vol_j = volatilities.get(asset_j, 0.0)
            corr = correlation_matrix.get(asset_i, {}).get(asset_j, 0.0)
            if i == j:
                corr = 1.0
            portfolio_variance += w_i * w_j * vol_i * vol_j * corr

    portfolio_volatility = math.sqrt(max(0.0, portfolio_variance))

    # Sharpe Ratio calculation
    if portfolio_volatility > 0:
        sharpe = (exp_return - risk_free_rate) / portfolio_volatility
    else:
        sharpe = 0.0

    # Effective diversification (inverse Herfindahl-Hirschman Index: 1 / sum(w^2))
    sum_sq_w = sum(w ** 2 for w in weights.values())
    div_score = round(1.0 / sum_sq_w, 2) if sum_sq_w > 0 else 1.0

    return PortfolioMetrics(
        expected_return=exp_return,
        volatility=portfolio_volatility,
        sharpe_ratio=sharpe,
        diversification_score=div_score,
    )


def compound_growth_projection(
    initial_balance: float,
    monthly_contribution: float,
    annual_return: float,
    annual_inflation: float,
    years: int,
    adjust_for_inflation: bool = True
) -> List[Dict[str, float]]:
    """
    Computes month-by-month compound growth with monthly contributions and inflation adjustment.
    
    Returns a list of dictionaries with keys: 
    'month', 'nominal_balance', 'real_balance', 'total_contributions'
    """
    monthly_return = (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
    monthly_inflation = (1.0 + annual_inflation) ** (1.0 / 12.0) - 1.0
    
    projection = []
    current_nominal = float(initial_balance)
    total_contributed = float(initial_balance)
    
    total_months = years * 12
    for m in range(total_months + 1):
        if m > 0:
            current_nominal = current_nominal * (1.0 + monthly_return) + monthly_contribution
            total_contributed += monthly_contribution
        
        if adjust_for_inflation and m > 0:
            # Deflate back to present value dollars using cumulative monthly inflation
            discount_factor = (1.0 + monthly_inflation) ** m
            current_real = current_nominal / discount_factor
        elif adjust_for_inflation and m == 0:
            current_real = current_nominal
        else:
            current_real = current_nominal  # Nominal mode

        projection.append({
            "month": m,
            "year": round(m / 12.0, 2),
            "nominal_balance": round(current_nominal, 2),
            "real_balance": round(current_real, 2),
            "total_contributions": round(total_contributed, 2)
        })
        
    return projection


def monte_carlo_simulation(
    initial_balance: float,
    monthly_contribution: float,
    annual_return: float,
    volatility: float,
    annual_inflation: float,
    years: int,
    num_simulations: int = 500,
    seed: int = None
) -> Dict[str, List[Dict[str, float]]]:
    """
    Runs Monte Carlo wealth projections across percentiles (10th, 50th median, 90th).
    Uses geometric Brownian motion approximation on a monthly timestep.
    """
    if seed is not None:
        random.seed(seed)
        
    total_months = years * 12
    monthly_mu = annual_return / 12.0
    monthly_sigma = volatility / math.sqrt(12.0)
    monthly_inflation = annual_inflation / 12.0

    # Store all simulation paths: list of lists (simulations x months)
    all_paths = []
    
    for _ in range(num_simulations):
        path = [float(initial_balance)]
        current = float(initial_balance)
        for m in range(1, total_months + 1):
            # Normal random shock for monthly return
            shock = random.gauss(0.0, 1.0)
            # It is standard to adjust drift by -0.5 * sigma^2 for geometric brownian motion
            monthly_r = monthly_mu - 0.5 * (monthly_sigma ** 2) + monthly_sigma * shock
            current = current * math.exp(monthly_r) + monthly_contribution
            path.append(current)
        all_paths.append(path)

    # Calculate percentiles for each month
    percentile_10 = []
    percentile_50 = []
    percentile_90 = []

    for m in range(total_months + 1):
        month_values = sorted([path[m] for path in all_paths])
        n_vals = len(month_values)
        
        idx_10 = int(0.10 * n_vals)
        idx_50 = int(0.50 * n_vals)
        idx_90 = int(0.90 * n_vals)
        
        val_10 = month_values[idx_10]
        val_50 = month_values[idx_50]
        val_90 = month_values[idx_90]
        
        # Adjust for inflation to get real purchasing power percentiles
        discount = (1.0 + monthly_inflation) ** m
        
        percentile_10.append({
            "month": m,
            "year": round(m / 12.0, 2),
            "nominal": round(val_10, 2),
            "real": round(val_10 / discount, 2)
        })
        percentile_50.append({
            "month": m,
            "year": round(m / 12.0, 2),
            "nominal": round(val_50, 2),
            "real": round(val_50 / discount, 2)
        })
        percentile_90.append({
            "month": m,
            "year": round(m / 12.0, 2),
            "nominal": round(val_90, 2),
            "real": round(val_90 / discount, 2)
        })

    return {
        "p10": percentile_10,
        "p50": percentile_50,
        "p90": percentile_90
    }


def generate_rebalancing_recommendations(
    current_allocation: AssetAllocation,
    target_allocation: AssetAllocation,
    current_total_value: float,
    tolerance_threshold: float = 0.05
) -> Dict[str, any]:
    """
    Generates portfolio rebalancing recommendations by comparing current holdings
    against target allocations within a given tolerance threshold (e.g., 5%).
    """
    curr_dict = current_allocation.to_dict()
    target_dict = target_allocation.to_dict()
    
    actions = {}
    needs_rebalancing = False
    
    for asset in ["stocks", "bonds", "real_estate", "cash"]:
        curr_weight = curr_dict.get(asset, 0.0)
        target_weight = target_dict.get(asset, 0.0)
        diff = curr_weight - target_weight
        
        if abs(diff) > tolerance_threshold:
            needs_rebalancing = True
            
        dollar_diff = diff * current_total_value
        
        if dollar_diff > 0:
            action_str = f"Sell ${abs(dollar_diff):,.2f} ({abs(diff)*100:.1f}%)"
        elif dollar_diff < 0:
            action_str = f"Buy ${abs(dollar_diff):,.2f} ({abs(diff)*100:.1f}%)"
        else:
            action_str = "Balanced"
            
        actions[asset] = {
            "current_weight": round(curr_weight * 100, 2),
            "target_weight": round(target_weight * 100, 2),
            "difference_pct": round(diff * 100, 2),
            "dollar_adjustment": round(dollar_diff, 2),
            "action": action_str
        }

    return {
        "needs_rebalancing": needs_rebalancing,
        "tolerance_threshold_pct": tolerance_threshold * 100,
        "recommendations": actions
    }
