import streamlit as st
import pandas as pd
from io import BytesIO

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

def edit_dataframe():
    st.write("Current Data:")
    
    # Enable dynamic rows and editing
    edited_df = st.data_editor(
        st.session_state.df,
        num_rows="dynamic",  # ← Allows adding rows by scrolling
        height=400,
        use_container_width=True
    )
    return edited_df

# Streamlit app setup
st.set_page_config(page_title="Excel Editor", layout="centered")
st.title("📊 Excel File Editor")

# Column management controls
col1, col2 = st.columns(2)
with col1:
    if st.button("➕ Add Column"):
        st.session_state.df[f"New_{len(st.session_state.df.columns)}"] = ""
with col2:
    if st.button("🗑️ Remove Last Column") and not st.session_state.df.empty:
        st.session_state.df = st.session_state.df.iloc[:, :-1]

# File upload handling
uploaded_file = st.file_uploader("Upload Excel File", type=["xls", "xlsx"])
if uploaded_file:
    st.session_state.df = pd.read_excel(uploaded_file)
    edited_df = edit_dataframe()
    
    # Save/download logic
    if st.button("💾 Save and Download"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Sheet1')
        st.download_button(
            label="⬇️ Download Edited File",
            data=output.getvalue(),
            file_name="edited_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
