import streamlit as st
import pandas as pd
from typing import Dict
from portfolio_engine import (
    AssetAllocation,
    PortfolioMetrics,
    calculate_portfolio_metrics,
    compound_growth_projection,
    monte_carlo_simulation,
    generate_rebalancing_recommendations,
)

# Configure Streamlit page
st.set_page_config(
    page_title="Algorithmic Investment & Retirement Simulator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = {}
if "active_scenario_name" not in st.session_state:
    st.session_state.active_scenario_name = "Baseline"

def format_currency(val: float) -> str:
    return f"${val:,.2f}"

def format_percent(val: float) -> str:
    return f"{val * 100:.2f}%"

# Sidebar Inputs
st.sidebar.header("Portfolio Parameters")

with st.sidebar.expander("Asset Allocation Weights", expanded=True):
    stocks_pct = st.slider("Stocks (%)", 0, 100, 60, step=5)
    bonds_pct = st.slider("Bonds (%)", 0, 100, 20, step=5)
    real_estate_pct = st.slider("Real Estate (%)", 0, 100, 10, step=5)
    cash_pct = st.slider("Cash (%)", 0, 100, 10, step=5)

    # Normalize weights
    total_weight = stocks_pct + bonds_pct + real_estate_pct + cash_pct
    if total_weight > 0:
        s_w = stocks_pct / total_weight
        b_w = bonds_pct / total_weight
        re_w = real_estate_pct / total_weight
        c_w = cash_pct / total_weight
    else:
        s_w, b_w, re_w, c_w = 0.25, 0.25, 0.25, 0.25

    allocation = AssetAllocation(stocks=s_w, bonds=b_w, real_estate=re_w, cash=c_w)
    try:
        allocation.validate()
    except ValueError as e:
        st.sidebar.error(str(e))

st.sidebar.subheader("Financial Inputs")
initial_balance = st.sidebar.number_input("Initial Portfolio Value ($", value=100000.0, step=10000.0)
monthly_contribution = st.sidebar.number_input("Monthly Contribution ($", value=1000.0, step=100.0)
years = st.sidebar.slider("Investment Horizon (Years)", 1, 50, 25)

st.sidebar.subheader("Economic Assumptions")
risk_free_rate = st.sidebar.slider("Risk-Free Rate (%)", 0.0, 10.0, 3.0, step=0.25) / 100.0
annual_inflation = st.sidebar.slider("Annual Inflation (%)", -2.0, 10.0, 2.5, step=0.25) / 100.0
adjust_for_inflation = st.sidebar.checkbox("Adjust Projections for Inflation", value=True)

st.sidebar.subheader("Asset Class Assumptions")
stock_ret = st.sidebar.slider("Stocks Expected Return (%)", 0.0, 20.0, 9.0, step=0.5) / 100.0
bond_ret = st.sidebar.slider("Bonds Expected Return (%)", 0.0, 15.0, 4.5, step=0.5) / 100.0
re_ret = st.sidebar.slider("Real Estate Expected Return (%)", 0.0, 15.0, 7.0, step=0.5) / 100.0
cash_ret = st.sidebar.slider("Cash Expected Return (%)", 0.0, 10.0, 1.5, step=0.5) / 100.0

stock_vol = st.sidebar.slider("Stocks Volatility (%)", 1.0, 40.0, 16.0, step=0.5) / 100.0
bond_vol = st.sidebar.slider("Bonds Volatility (%)", 0.5, 20.0, 6.0, step=0.5) / 100.0
re_vol = st.sidebar.slider("Real Estate Volatility (%)", 1.0, 30.0, 12.0, step=0.5) / 100.0
cash_vol = st.sidebar.slider("Cash Volatility (%)", 0.0, 5.0, 1.0, step=0.25) / 100.0

expected_returns = {"stocks": stock_ret, "bonds": bond_ret, "real_estate": re_ret, "cash": cash_ret}
volatilities = {"stocks": stock_vol, "bonds": bond_vol, "real_estate": re_vol, "cash": cash_vol}

# Standard simplified correlation matrix
correlation_matrix = {
    "stocks": {"stocks": 1.0, "bonds": 0.1, "real_estate": 0.6, "cash": 0.0},
    "bonds": {"stocks": 0.1, "bonds": 1.0, "real_estate": 0.2, "cash": 0.1},
    "real_estate": {"stocks": 0.6, "bonds": 0.2, "real_estate": 1.0, "cash": 0.0},
    "cash": {"stocks": 0.0, "bonds": 0.1, "real_estate": 0.0, "cash": 1.0},
}

# Compute Metrics
metrics = calculate_portfolio_metrics(
    allocation=allocation,
    expected_returns=expected_returns,
    volatilities=volatilities,
    correlation_matrix=correlation_matrix,
    risk_free_rate=risk_free_rate,
)

# Main UI Header
st.title("Algorithmic Investment & Retirement Simulator")
st.markdown(
    "Evaluate multi-asset compound growth, Monte Carlo probabilistic wealth percentiles, "
    "Sharpe-optimized asset allocations, and automated portfolio rebalancing." 
)

# st.metric Cards Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Expected Return (Ann.)", value=format_percent(metrics.expected_return))
with col2:
    st.metric(label="Portfolio Volatility", value=format_percent(metrics.volatility))
with col3:
    st.metric(label="Sharpe Ratio", value=f"{metrics.sharpe_ratio:.2f}")
with col4:
    st.metric(label="Effective Diversification", value=f"{metrics.diversification_score:.2f}")

st.divider()

# Tabs for Deep Dive
tab1, tab2, tab3, tab4 = st.tabs([
    "Growth Projections", 
    "Monte Carlo Simulation", 
    "Rebalancing Tool", 
    "Scenario Manager"
])

with tab1:
    st.subheader("Deterministic Wealth Accumulation")
    growth_data = compound_growth_projection(
        initial_balance=initial_balance,
        monthly_contribution=monthly_contribution,
        annual_return=metrics.expected_return,
        annual_inflation=annual_inflation,
        years=years,
        adjust_for_inflation=adjust_for_inflation,
    )
    growth_df = pd.DataFrame(growth_data)
    bal_col = "real_balance" if adjust_for_inflation else "nominal_balance"
    growth_df["Balance"] = growth_df[bal_col]
    growth_df["TotalContributions"] = growth_df["total_contributions"]
    growth_df["InterestEarned"] = growth_df["Balance"] - growth_df["TotalContributions"]
    growth_df["Year"] = growth_df["year"]

    final_row = growth_df.iloc[-1]
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Final Total Balance", format_currency(final_row["Balance"]))
    col_b.metric("Total Contributions", format_currency(final_row["TotalContributions"]))
    col_c.metric("Total Interest Earned", format_currency(final_row["InterestEarned"]))

    st.line_chart(growth_df.set_index("Year")[["Balance", "TotalContributions"]])

    with st.expander("View Full Projection Table"):
        st.dataframe(growth_df, use_container_width=True)

with tab2:
    st.subheader("Monte Carlo Probabilistic Projections")
    st.markdown("Simulates potential market trajectories incorporating return volatility.")

    col_mc1, col_mc2 = st.columns(2)
    with col_mc1:
        num_sims = st.slider("Number of Simulations", 100, 1000, 500, step=100)
    with col_mc2:
        mc_seed = st.number_input("Random Seed (for reproducibility)", value=42, step=1)

    with st.spinner("Running Monte Carlo simulations..."):
        mc_raw = monte_carlo_simulation(
            initial_balance=initial_balance,
            monthly_contribution=monthly_contribution,
            annual_return=metrics.expected_return,
            volatility=metrics.volatility,
            annual_inflation=annual_inflation,
            years=years,
            num_simulations=num_sims,
            seed=int(mc_seed),
        )

    val_key = "real" if adjust_for_inflation else "nominal"
    mc_df = pd.DataFrame({
        "Year": [p["year"] for p in mc_raw["p50"]],
        "P10": [p[val_key] for p in mc_raw["p10"]],
        "P50": [p[val_key] for p in mc_raw["p50"]],
        "P90": [p[val_key] for p in mc_raw["p90"]],
    })

    final_mc = mc_df.iloc[-1]
    p10 = final_mc["P10"]
    p50 = final_mc["P50"]
    p90 = final_mc["P90"]

    mc_c1, mc_c2, mc_c3 = st.columns(3)
    mc_c1.metric("10th Percentile (Conservative)", format_currency(p10))
    mc_c2.metric("50th Percentile (Median)", format_currency(p50))
    mc_c3.metric("90th Percentile (Optimistic)", format_currency(p90))

    st.line_chart(mc_df.set_index("Year")[["P10", "P50", "P90"]])

    with st.expander("View Monte Carlo Percentiles Table"):
        st.dataframe(mc_df, use_container_width=True)

with tab3:
    st.subheader("Portfolio Rebalancing Recommendations")
    st.markdown("Enter your current actual asset dollar values to check drift against target weights.")

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        cur_stocks = st.number_input("Current Stocks ($)", value=60000.0, step=1000.0)
    with col_r2:
        cur_bonds = st.number_input("Current Bonds ($)", value=25000.0, step=1000.0)
    with col_r3:
        cur_re = st.number_input("Current Real Estate ($)", value=10000.0, step=1000.0)
    with col_r4:
        cur_cash = st.number_input("Current Cash ($)", value=5000.0, step=1000.0)

    current_portfolio = {
        "stocks": cur_stocks,
        "bonds": cur_bonds,
        "real_estate": cur_re,
        "cash": cur_cash,
    }
    current_total = sum(current_portfolio.values())
    tolerance = st.slider("Drift Tolerance Threshold (%)", 1.0, 15.0, 5.0, step=0.5) / 100.0

    if current_total > 0:
        cur_alloc = AssetAllocation(
            stocks=cur_stocks,
            bonds=cur_bonds,
            real_estate=cur_re,
            cash=cur_cash,
        )
        reb_recs = generate_rebalancing_recommendations(
            current_allocation=cur_alloc,
            target_allocation=allocation,
            current_total_value=current_total,
            tolerance_threshold=tolerance,
        )

        st.metric("Total Portfolio Value", format_currency(current_total))
        st.write(f"**Rebalancing Required:** {'Yes ⚠️' if reb_recs['needs_rebalancing'] else 'No ✅'}")

        breakdown_df = pd.DataFrame.from_dict(reb_recs["recommendations"], orient="index")
        breakdown_df.index.name = "Asset Class"
        st.dataframe(breakdown_df.reset_index(), use_container_width=True)
    else:
        st.warning("Current portfolio total value must be greater than zero.")

with tab4:
    st.subheader("Scenario Manager")
    st.markdown("Save current slider parameters as a named scenario and compare against baseline.")

    scenario_name = st.text_input("Scenario Name", value="Aggressive Growth")
    if st.button("Save Current Scenario"):
        st.session_state.saved_scenarios[scenario_name] = {
            "allocation": allocation.to_dict(),
            "initial_balance": initial_balance,
            "monthly_contribution": monthly_contribution,
            "years": years,
            "expected_return": metrics.expected_return,
            "volatility": metrics.volatility,
            "sharpe_ratio": metrics.sharpe_ratio,
            "diversification_score": metrics.diversification_score,
        }
        st.success(f"Scenario '{scenario_name}' saved successfully!")

    if st.session_state.saved_scenarios:
        st.write("### Saved Scenarios")
        scen_summary = []
        for name, data in st.session_state.saved_scenarios.items():
            scen_summary.append({
                "Name": name,
                "Initial Balance": format_currency(data["initial_balance"]),
                "Monthly Contrib": format_currency(data["monthly_contribution"]),
                "Years": data["years"],
                "Exp. Return": format_percent(data["expected_return"]),
                "Sharpe": f"{data['sharpe_ratio']:.2f}",
                "Diversification": f"{data.get('diversification_score', 1.0):.2f}"
            })
        st.dataframe(pd.DataFrame(scen_summary), use_container_width=True)

        to_delete = st.selectbox("Select Scenario to Delete", [""] + list(st.session_state.saved_scenarios.keys()))
        if to_delete and st.button("Delete Scenario"):
            del st.session_state.saved_scenarios[to_delete]
            st.success(f"Deleted '{to_delete}'.")
            st.experimental_rerun()
    else:
        st.info("No saved scenarios yet. Configure inputs and save your first scenario.")
