# app.py
import streamlit as st

st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💹",
    layout="centered",
    menu_items={
        'Get Help': 'https://your-help-site.com',
        'Report a bug': "mailto:support@yourcompany.com"
    }
)

with st.sidebar:
    st.header("Quick Access")
    if st.button("Clear Cache", help="Reset all temporary data"):
        st.cache_data.clear()
        st.success("Cache cleared!")
    st.divider()