import pandas as pd
import numpy as np
from scipy.stats import linregress

df.columns = df.columns.str.strip()
df['Date'] = pd.to_datetime(df['Date'])
df['First_Inv_Date'] = pd.to_datetime(df['First_Inv_Date'])

monthly_sales = (
    df.groupby(['Section', pd.Grouper(key='Date', freq='MS')])['bal Qty']
    .sum().reset_index()
)

global_first_date = monthly_sales['Date'].min()
global_last_date = monthly_sales['Date'].max()

results = []

for section in monthly_sales['Section'].unique():
    sec_df = monthly_sales[monthly_sales['Section'] == section].copy().sort_values('Date')
    
    first_inv = df.loc[df['Section'] == section, 'First_Inv_Date'].min()
    if pd.isna(first_inv):
        first_inv = sec_df['Date'].min()
    first_inv = first_inv.to_period('M').to_timestamp()
    
    history_flag = 'Missing Early History' if first_inv < global_first_date else 'Complete'
    
    full_range = pd.date_range(start=max(first_inv, global_first_date), end=global_last_date, freq='MS')
    sec_df = sec_df.set_index('Date').reindex(full_range)
    sec_df.index.name = 'Date'
    sec_df['bal Qty'] = pd.to_numeric(sec_df['bal Qty'], errors='coerce').fillna(0)
    sec_df['Section'] = section
    sec_df = sec_df.reset_index()
    
    actual_start = sec_df['Date'].min()
    age_months = (global_last_date.year - actual_start.year) * 12 + (global_last_date.month - actual_start.month)
    if age_months < 18:
        continue
        
    first_12m_end = actual_start + pd.DateOffset(months=12)
    first_avg = sec_df[(sec_df['Date'] >= actual_start) & (sec_df['Date'] < first_12m_end)]['bal Qty'].mean()
    
    last_12m_start = global_last_date - pd.DateOffset(months=11)
    last_avg = sec_df[sec_df['Date'] >= last_12m_start]['bal Qty'].mean()
    
    retention_ratio = last_avg / first_avg if first_avg > 0 else np.nan
    decline_pct = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else np.nan
    
    x = np.arange(len(sec_df))
    slope, _, r_value, _, _ = linregress(x, sec_df['bal Qty'].values)
    r2 = r_value ** 2
    
    recent_6m_avg = sec_df.tail(6)['bal Qty'].mean()
    prev_6m_avg = sec_df.iloc[-12:-6]['bal Qty'].mean()
    recent_momentum = ((recent_6m_avg - prev_6m_avg) / prev_6m_avg * 100) if prev_6m_avg > 0 else np.nan
    
    recent_6m_total = sec_df.tail(6)['bal Qty'].sum()
    sales_2024 = sec_df[sec_df['Date'].dt.year == 2024]['bal Qty'].sum()
    sales_2025 = sec_df[sec_df['Date'].dt.year == 2025]['bal Qty'].sum()
    
    dead_section = (sec_df.tail(3)['bal Qty'] == 0).all()
    profitable_2025 = df.loc[df['Section'] == section, 'Margin_%_2025'].max() > 0
    
    score = 0
    if first_avg >= 1000: score += 30
    elif first_avg >= 500: score += 20
    
    if not np.isnan(decline_pct):
        if decline_pct <= -70: score += 30
        elif decline_pct <= -40: score += 20
        
    if slope < 0: score += 20
    if profitable_2025: score += 20
    if recent_momentum > 30: score += 10
    if recent_6m_total > 100: score += 10
    if dead_section: score -= 10
    if history_flag != 'Complete': score -= 15
    
    if dead_section:
        status = 'Dead Section'
    elif not np.isnan(decline_pct) and decline_pct <= -70 and slope < 0:
        status = 'Critical Decline'
    elif not np.isnan(decline_pct) and decline_pct <= -40:
        status = 'Strong Decline'
    elif slope < 0:
        status = 'Slow Decline'
    else:
        status = 'Healthy'
        
    results.append({
        'Section': section,
        'First_Inv_Date': first_inv,
        'History_Flag': history_flag,
        'Age_Months': age_months,
        'First_12M_Avg': round(first_avg, 2),
        'Last_12M_Avg': round(last_avg, 2),
        'Retention_Ratio': round(retention_ratio, 2),
        'Decline_%': round(decline_pct, 2),
        'Slope_All_Years': round(slope, 2),
        'R2': round(r2, 3),
        'Recent_6M_Momentum_%': round(recent_momentum, 2),
        'Recent_6M_Total': round(recent_6m_total, 2),
        'Sales_2024': round(sales_2024, 2),
        'Sales_2025': round(sales_2025, 2),
        'Margin_%_2025': round(df.loc[df['Section'] == section, 'Margin_%_2025'].max(), 2),
        'Profitable_2025': profitable_2025,
        'Dead_Section': dead_section,
        'Reactivation_Score': score,
        'Status': status
    })

results_df = pd.DataFrame(results).sort_values(
    by=['Reactivation_Score', 'Decline_%'],
    ascending=[False, True]
)

results_df.to_excel('Sections_Reactivation_Analysis_Final.xlsx', index=False)
print(results_df.head(20))
