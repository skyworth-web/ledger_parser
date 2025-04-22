# pages/3_⚙️_Settings.py
import streamlit as st

def main():
    st.title("Settings ⚙️")
    
    with st.form("app_settings"):
        st.subheader("Theme Configuration")
        theme = st.selectbox("Color Theme", 
            ["Light", "Dark", "System Default"])
        
        st.subheader("Data Preferences")
        cache_enabled = st.checkbox("Enable Data Caching")
        page_transitions = st.checkbox("Enable Page Transitions", True)
        
        if st.form_submit_button("Save Preferences"):
            st.session_state.theme = theme
            st.session_state.cache_enabled = cache_enabled
            st.session_state.page_transitions = page_transitions
            st.success("Preferences saved!")

if __name__ == "__main__":
    main()