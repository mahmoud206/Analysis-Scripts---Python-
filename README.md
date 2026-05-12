# Section Reactivation Analysis

A time-series and cohort-based analytical script designed to identify declining, dormant, or high-potential sections in sales/inventory data. It computes trend metrics, retention ratios, and generates a composite reactivation score to prioritize business interventions.

This script is part of the **Analysis Scripts** repository, which houses reusable analytical tools for data processing, statistical modeling, and business intelligence workflows.

## 📦 Requirements
- Python 3.8+
- `pandas`, `numpy`, `scipy`, `openpyxl`

## 🚀 Usage
1. Ensure your working directory contains a pandas DataFrame `df` with the following columns:
   - `Section` (categorical/str)
   - `Date` (datetime)
   - `First_Inv_Date` (datetime)
   - `bal Qty` (numeric)
   - `Margin_%_2025` (numeric)
2. Run the script. It will output `Sections_Reactivation_Analysis_Final.xlsx` sorted by reactivation priority.
3. Sections with less than 18 months of history are automatically excluded to maintain statistical reliability.

## 📐 Mathematical & Statistical Framework

### 1. Ordinary Least Squares (OLS) Linear Regression
The script fits a simple linear regression model $y = mx + c$ to the monthly quantity series, where $x$ represents sequential month indices and $y$ is the observed quantity.
- **Slope ($m$):** Represents the average monthly change in quantity. A negative slope indicates a consistent downward trend across the entire observation window.
- **Coefficient of Determination ($R^2$):** Measures the proportion of variance in the dependent variable that is predictable from the independent variable. Values near 1 indicate a strong, stable trend (linear behavior), while values near 0 suggest high volatility or random noise.

### 2. Cohort-Based Retention & Decline Analysis
Compares the average monthly quantity during the first 12 months of activity against the most recent 12 months, mimicking standard customer/product cohort retention metrics:
$$ \text{Retention Ratio} = \frac{\bar{Q}_{\text{Last 12M}}}{\bar{Q}_{\text{First 12M}}} $$
$$ \text{Decline \%} = \left( \frac{\bar{Q}_{\text{Last 12M}} - \bar{Q}_{\text{First 12M}}}{\bar{Q}_{\text{First 12M}}} \right) \times 100 $$
This isolates long-term structural degradation from short-term seasonality or supply chain fluctuations.

### 3. Rolling Momentum Calculation
Momentum is computed as the percentage change between two consecutive 6-month rolling windows:
$$ \text{Momentum} = \left( \frac{\bar{Q}_{\text{Recent 6M}} - \bar{Q}_{\text{Prev 6M}}}{\bar{Q}_{\text{Prev 6M}}} \right) \times 100 $$
Derived from time-series forecasting and financial technical analysis, this metric detects recent inflection points and acceleration before they are diluted in yearly averages.

### 4. Multi-Criteria Heuristic Scoring
The `Reactivation_Score` is a weighted index combining statistical signals with business thresholds:
- **Historical Baseline:** Rewards sections with strong initial market traction.
- **Trend Direction & Severity:** Assigns higher priority to steep, consistent declines (negative slope + high decline %).
- **Profitability Filter:** Ensures only economically viable sections are prioritized for reactivation.
- **Recency & Dormancy Signals:** Adjusts for recent sales velocity and flags zero-activity periods.
- **Data Completeness Penalty:** Reduces confidence in sections with missing early history to avoid biased trend estimation.

## 📊 Output Columns
| Column | Description |
|--------|-------------|
| `Section` | Unique section identifier |
| `History_Flag` | `Complete` or `Missing Early History` |
| `Age_Months` | Total months since first recorded activity |
| `First_12M_Avg` / `Last_12M_Avg` | Average monthly quantity for initial vs recent year |
| `Retention_Ratio` | Last 12M avg divided by First 12M avg |
| `Decline_%` | Percentage drop from initial to recent year |
| `Slope_All_Years` | Monthly trend rate (OLS linear regression) |
| `R2` | Model fit quality for the linear trend |
| `Recent_6M_Momentum_%` | Short-term acceleration indicator |
| `Sales_2024` / `Sales_2025` | Yearly aggregated quantities |
| `Profitable_2025` | Boolean flag (`Margin_%_2025 > 0`) |
| `Dead_Section` | `True` if last 3 consecutive months show zero activity |
| `Reactivation_Score` | Composite priority index (higher = stronger candidate) |
| `Status` | Categorized health state (`Healthy`, `Slow Decline`, `Strong Decline`, `Critical Decline`, `Dead Section`) |

## 📝 Notes
- Missing months in the raw data are reindexed and filled with zeros to maintain a continuous time series, which is required for accurate regression and rolling window calculations.
- All percentage metrics are clamped to `NaN` when baselines are zero to prevent division errors and misinterpretation.
