import streamlit as st
import pandas as pd
import plotly.express as px

# ========== Page Configuration ==========
st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💹",
    layout="centered",
    menu_items={
        'Get Help': 'https://your-help-site.com',
        'Report a bug': "mailto:support@yourcompany.com"
    }
)

# ========== Custom CSS ==========
st.markdown("""
<style>
  .main {background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);}
  .st-emotion-cache-6qob1r {background: rgba(255,255,255,0.9)!important;}
  .metric-card {padding: 1.5rem; 
              border-radius: 12px;
              background: white;
              box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
  .header-font {font-family: 'Segoe UI', sans-serif;
              color: #2b3b4e;
              font-weight: 600;}
  .chart-container {border-radius: 16px;
                  background: white;
                  padding: 1rem;
                  margin: 1rem 0;}
</style>
""", unsafe_allow_html=True)

# ========== Sidebar ==========
with st.sidebar:
    # Branding Section
    st.markdown("""
    <div style='padding: 1rem; border-bottom: 1px solid #eee; margin-bottom: 1.5rem;'>
        <h2 style='color: #4a90e2; margin: 0;'>💰 FinVision</h2>
        <p style='color: #6c757d; margin: 0; font-size: 0.9rem;'>Financial Analytics Suite</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("📊 New Report", use_container_width=True):
            pass
    
    st.divider()
    
    # Date Filter
    st.date_input("Select Date Range", 
                 value=(pd.to_datetime("2025-04-01"), pd.to_datetime("2025-04-24")),
                 key="date_filter")

# ========== Main Content ==========
# Hero Section
st.markdown("<h1 class='header-font'>Financial Overview 💹</h1>", unsafe_allow_html=True)

# Key Metrics
metric_cols = st.columns(4)
with metric_cols[0]:
    st.markdown("""
    <div class='metric-card'>
        <p style='color:#6c757d; margin:0;'>Total Assets</p>
        <h2 style='color:#2b3b4e; margin:0;'>$542K</h2>
        <p style='color:#28a745; margin:0; font-size:0.9rem;'>↑ 12% MoM</p>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[1]:
    st.markdown("""
    <div class='metric-card'>
        <p style='color:#6c757d; margin:0;'>Liabilities</p>
        <h2 style='color:#2b3b4e; margin:0;'>$128K</h2>
        <p style='color:#dc3545; margin:0; font-size:0.9rem;'>↓ 4% MoM</p>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[2]:
    st.markdown("""
    <div class='metric-card'>
        <p style='color:#6c757d; margin:0;'>Net Worth</p>
        <h2 style='color:#2b3b4e; margin:0;'>$414K</h2>
        <p style='color:#28a745; margin:0; font-size:0.9rem;'>↑ 8.6% MoM</p>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[3]:
    st.markdown("""
    <div class='metric-card'>
        <p style='color:#6c757d; margin:0;'>ROI</p>
        <h2 style='color:#2b3b4e; margin:0;'>14.2%</h2>
        <p style='color:#ffc107; margin:0; font-size:0.9rem;'>→ Stable</p>
    </div>
    """, unsafe_allow_html=True)

# Main Chart
with st.container():
    st.markdown("<h3 class='header-font'>Portfolio Performance</h3>", unsafe_allow_html=True)
    chart_data = pd.DataFrame({
        'Date': pd.date_range(start='2025-01-01', periods=120),
        'Value': [100 + x**1.5 + x*2 for x in range(120)]
    })
    fig = px.area(chart_data, x='Date', y='Value', 
                 color_discrete_sequence=['#4a90e2'])
    fig.update_layout(margin=dict(t=30, b=30),
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

# Data Section
tab1, tab2 = st.tabs(["📑 Recent Transactions", "📊 Spending Categories"])

with tab1:
    transactions = pd.DataFrame({
        'Date': ['2025-04-23', '2025-04-22', '2025-04-21'],
        'Description': ['Tech Investment', 'Dividend Payment', 'Market Research'],
        'Amount': ['+$15,000', '+$2,400', '-$1,200'],
        'Category': ['Investment', 'Income', 'Expense']
    })
    st.dataframe(transactions.style.applymap(lambda x: 'color: #28a745' if '+' in x else 'color: #dc3545', 
                                           subset=['Amount']),
               use_container_width=True,
               hide_index=True)

with tab2:
    col1, col2 = st.columns([2,3])
    with col1:
        categories = pd.DataFrame({
            'Category': ['Investments', 'Salary', 'Dividends', 'Expenses'],
            'Percentage': [45, 35, 15, 5]
        })
        st.dataframe(categories.style.format({'Percentage': '{:.0f}%'}),
                   use_container_width=True)
    with col2:
        fig = px.pie(categories, names='Category', values='Percentage',
                    color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)