import os
import tempfile
import streamlit as st
import pandas as pd
from api.reconciler.main_processor import reconcile_statement

# Configure output directory
OUTPUT_DIR = os.path.abspath("./data/output/reconciled")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location and return path"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded_file.getbuffer())
            return tmp.name
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")
        return None

def display_results(output_path):
    """Display results section with preview and download"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Preview of Reconciled Data")
        display_excel(output_path)
    
    with col2:
        st.subheader("Download")
        with open(output_path, "rb") as f:
            st.download_button(
                label="⬇️ Full Report",
                data=f,
                file_name=os.path.basename(output_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
def display_excel(file_path):
    """Display Excel file content in Streamlit with type handling"""
    try:
        # Read with type conversion
        df = pd.read_excel(
            file_path,
            dtype={
                'date': 'datetime64[ns]',
                'description': 'string',
                'debit': 'float64',
                'credit': 'float64',
                'Remarks': 'string'
            }
        )
        
        # Clean up any unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Format datetime columns
        if 'date' in df.columns:
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        # Convert all columns to string type for safe display
        display_df = df.astype('string').fillna('')
        
        st.dataframe(display_df, height=500, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error displaying file: {str(e)}")
        
def dual_ledger_page():
    st.title("Dual Ledger Reconciliation 🔄")
    
    # Initialize session state
    if 'reconciled' not in st.session_state:
        st.session_state.reconciled = {
            'processed': False,
            'output_path': None,
            'file1': None,
            'file2': None
        }
    
    # File upload section
    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Upload First Ledger", type=["xlsx", "xls"])
    with col2:
        file2 = st.file_uploader("Upload Second Ledger", type=["xlsx", "xls"])
    
    # Process files button
    process_btn = st.button("🔍 Start Reconciliation", 
                          disabled=not (file1 and file2),
                          type="primary")
    
    if process_btn:
        with st.spinner("🧠 Processing ledgers..."):
            try:
                # Save files
                file1_path = save_uploaded_file(file1)
                file2_path = save_uploaded_file(file2)
                
                if not all([file1_path, file2_path]):
                    st.error("Failed to process uploaded files")
                    return
                
                # Run reconciliation
                output_path = reconcile_statement(file1_path, file2_path)
                
                if output_path and os.path.exists(output_path):
                    st.session_state.reconciled = {
                        'processed': True,
                        'output_path': output_path,
                        'file1': file1.name,
                        'file2': file2.name
                    }
                    st.success("✅ Reconciliation completed!")
                else:
                    st.error("❌ Reconciliation failed")
                
                # Cleanup temp files
                os.remove(file1_path)
                os.remove(file2_path)
                
            except Exception as e:
                st.error(f"Processing error: {str(e)}")
                st.session_state.reconciled['processed'] = False

    # Display results if available
    if st.session_state.reconciled['processed']:
        st.subheader("Results")
        st.markdown(f"""
        - **First Ledger:** `{st.session_state.reconciled['file1']}`
        - **Second Ledger:** `{st.session_state.reconciled['file2']}`
        - **Output File:** `{os.path.basename(st.session_state.reconciled['output_path'])}`
        """)
        
        display_results(st.session_state.reconciled['output_path'])
        
    # Reset button
    if st.session_state.reconciled['processed']:
        if st.button("🔄 Start New Reconciliation"):
            st.session_state.reconciled = {
                'processed': False,
                'output_path': None,
                'file1': None,
                'file2': None
            }
            st.rerun()

if __name__ == "__main__":
    dual_ledger_page()