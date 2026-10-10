import pytest
import math
from portfolio_engine import (
    AssetAllocation,
    PortfolioMetrics,
    calculate_portfolio_metrics,
    compound_growth_projection,
    monte_carlo_simulation,
    generate_rebalancing_recommendations
)

def test_asset_allocation_validation_success():
    allocation = AssetAllocation(stocks=50.0, bonds=30.0, real_estate=10.0, cash=10.0)
    assert allocation.validate() is True

def test_asset_allocation_validation_failure_sum():
    allocation = AssetAllocation(stocks=50.0, bonds=50.0, real_estate=10.0, cash=10.0)
    assert allocation.validate() is False

def test_asset_allocation_validation_failure_negative():
    allocation = AssetAllocation(stocks=-10.0, bonds=70.0, real_estate=20.0, cash=20.0)
    assert allocation.validate() is False

def test_asset_allocation_to_dict():
    allocation = AssetAllocation(stocks=40.0, bonds=40.0, real_estate=10.0, cash=10.0)
    d = allocation.to_dict()
    assert d == {'stocks': 0.4, 'bonds': 0.4, 'real_estate': 0.1, 'cash': 0.1}

def test_calculate_portfolio_metrics():
    allocation = AssetAllocation(stocks=50.0, bonds=50.0, real_estate=0.0, cash=0.0)
    expected_returns = {'stocks': 0.10, 'bonds': 0.04, 'real_estate': 0.08, 'cash': 0.01}
    volatilities = {'stocks': 0.15, 'bonds': 0.05, 'real_estate': 0.10, 'cash': 0.01}
    correlation_matrix = {
        'stocks': {'stocks': 1.0, 'bonds': 0.2, 'real_estate': 0.5, 'cash': 0.0},
        'bonds': {'stocks': 0.2, 'bonds': 1.0, 'real_estate': 0.1, 'cash': 0.0},
        'real_estate': {'stocks': 0.5, 'bonds': 0.1, 'real_estate': 1.0, 'cash': 0.0},
        'cash': {'stocks': 0.0, 'bonds': 0.0, 'real_estate': 0.0, 'cash': 1.0}
    }
    risk_free_rate = 0.02
    
    metrics = calculate_portfolio_metrics(allocation, expected_returns, volatilities, correlation_matrix, risk_free_rate)
    
    assert isinstance(metrics, PortfolioMetrics)
    assert metrics.expected_return == pytest.approx(0.07)
    assert metrics.volatility > 0.0
    assert isinstance(metrics.sharpe_ratio, float)

def test_compound_growth_projection_basic():
    initial_balance = 10000.0
    monthly_contribution = 500.0
    annual_return = 0.08
    annual_inflation = 0.03
    years = 10
    
    projection = compound_growth_projection(
        initial_balance, monthly_contribution, annual_return, annual_inflation, years, adjust_for_inflation=True
    )
    
    assert len(projection) == (years * 12) + 1
    assert projection[0]['nominal_balance'] == 10000.0
    assert projection[-1]['nominal_balance'] > projection[0]['nominal_balance']
    assert projection[-1]['real_balance'] < projection[-1]['nominal_balance']

def test_compound_growth_zero_return():
    initial_balance = 5000.0
    monthly_contribution = 100.0
    annual_return = 0.0
    annual_inflation = 0.0
    years = 5
    
    projection = compound_growth_projection(
        initial_balance, monthly_contribution, annual_return, annual_inflation, years, adjust_for_inflation=True
    )
    
    expected_final = 5000.0 + (100.0 * 12 * 5)
    assert projection[-1]['nominal_balance'] == expected_final
    assert projection[-1]['real_balance'] == expected_final

def test_compound_growth_negative_inflation():
    initial_balance = 10000.0
    monthly_contribution = 0.0
    annual_return = 0.05
    annual_inflation = -0.02
    years = 2
    
    projection = compound_growth_projection(
        initial_balance, monthly_contribution, annual_return, annual_inflation, years, adjust_for_inflation=True
    )
    
    assert projection[-1]['real_balance'] >= projection[-1]['nominal_balance']

def test_monte_carlo_simulation():
    initial_balance = 10000.0
    monthly_contribution = 200.0
    annual_return = 0.07
    volatility = 0.12
    annual_inflation = 0.02
    years = 5
    num_simulations = 50
    seed = 42
    
    percentiles = monte_carlo_simulation(
        initial_balance, monthly_contribution, annual_return, volatility, 
        annual_inflation, years, num_simulations, seed
    )
    
    assert 'p10' in percentiles
    assert 'p50' in percentiles
    assert 'p90' in percentiles
    assert len(percentiles['p50']) == (years * 12) + 1
    
    # Check percentile ordering at final month: nominal p90 >= p50 >= p10
    for i in range(len(percentiles['p50'])):
        assert percentiles['p90'][i]['nominal'] >= percentiles['p50'][i]['nominal']
        assert percentiles['p50'][i]['nominal'] >= percentiles['p10'][i]['nominal']

def test_generate_rebalancing_recommendations():
    current_allocation = AssetAllocation(stocks=70.0, bonds=20.0, real_estate=5.0, cash=5.0)
    target_allocation = AssetAllocation(stocks=50.0, bonds=40.0, real_estate=5.0, cash=5.0)
    current_total_value = 100000.0
    tolerance_threshold = 0.05
    
    recs = generate_rebalancing_recommendations(
        current_allocation, target_allocation, current_total_value, tolerance_threshold
    )
    
    assert 'recommendations' in recs
    stocks_rec = recs['recommendations']['stocks']
    assert stocks_rec['difference_pct'] == pytest.approx(20.0)
    assert stocks_rec['dollar_adjustment'] == pytest.approx(20000.0)
    
    bonds_rec = recs['recommendations']['bonds']
    assert bonds_rec['difference_pct'] == pytest.approx(-20.0)
    assert bonds_rec['dollar_adjustment'] == pytest.approx(-20000.0)

def test_generate_rebalancing_within_tolerance():
    current_allocation = AssetAllocation(stocks=51.0, bonds=39.0, real_estate=5.0, cash=5.0)
    target_allocation = AssetAllocation(stocks=50.0, bonds=40.0, real_estate=5.0, cash=5.0)
    current_total_value = 100000.0
    tolerance_threshold = 0.05
    
    recs = generate_rebalancing_recommendations(
        current_allocation, target_allocation, current_total_value, tolerance_threshold
    )
    
    assert recs['needs_rebalancing'] is False
