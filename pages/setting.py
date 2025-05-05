import streamlit as st
import json
from pathlib import Path

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("config.json not found!")
        return None

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)

def config_editor_page():
    st.title("Configuration Editor")
    
    config = load_config()
    if not config:
        return

    with st.expander("Matching Parameters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            config['match_tolerance'] = st.number_input(
                "Match Tolerance",
                min_value=0.0,
                max_value=1.0,
                value=config['match_tolerance'],
                step=0.01,
                help="Threshold for direct match comparisons"
            )
            
            config['fuzzy_date_range'] = st.number_input(
                "Fuzzy Date Range (days)",
                min_value=0,
                max_value=30,
                value=config['fuzzy_date_range'],
                step=1
            )

        with col2:
            config['rounding_tolerance'] = st.number_input(
                "Rounding Tolerance",
                min_value=0.0,
                max_value=1.0,
                value=config['rounding_tolerance'],
                step=0.1
            )
            
            config['rounding_date_range'] = st.number_input(
                "Rounding Date Range (days)",
                min_value=0,
                max_value=30,
                value=config['rounding_date_range'],
                step=1
            )

    with st.expander("Advanced Settings"):
        config['split_match_date_range'] = st.number_input(
            "Split Match Date Range (days)",
            min_value=0,
            max_value=30,
            value=config['split_match_date_range'],
            step=1
        )

        st.markdown("**Feature Toggles**")
        config['enable_exact_match'] = st.checkbox(
            "Enable Exact Match",
            value=config['enable_exact_match']
        )
        config['enable_fuzzy_match'] = st.checkbox(
            "Enable Fuzzy Match",
            value=config['enable_fuzzy_match']
        )
        config['enable_rounding_match'] = st.checkbox(
            "Enable Rounding Match",
            value=config['enable_rounding_match']
        )
        config['enable_split_match'] = st.checkbox(
            "Enable Split Match",
            value=config['enable_split_match']
        )

    if st.button("Save Configuration"):
        save_config(config)
        st.success("Configuration saved successfully!")
        st.rerun()

if __name__ == "__main__":
    config_editor_page()