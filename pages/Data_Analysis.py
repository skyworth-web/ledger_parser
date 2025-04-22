import os
import streamlit as st
import pandas as pd
from api.ocr.excel_parser import excel_parser
from api.ocr.image_parser import image_parser

# Set page config
st.set_page_config(page_title="Bank Statement Parser", layout="centered")
st.title("🏦 Bank Statement Editor")

def main():
    # Initialize session state
    if 'output_path' not in st.session_state:
        st.session_state.output_path = None
    if 'df' not in st.session_state:
        st.session_state.df = None
    
    uploaded_file = st.file_uploader("Upload PDF, Image, or Excel", 
                                   type=["pdf", "png", "jpg", "jpeg", "webp", "xls", "xlsx"])
    
    if uploaded_file and st.session_state.df is None:
        with st.spinner("🔍 Extracting and analyzing..."):
            try:
                # Process file and get output path
                if uploaded_file.name.endswith((".xlsx", ".xls")):
                    st.session_state.output_path = excel_parser(uploaded_file)
                else:
                    st.session_state.output_path = image_parser(uploaded_file)
                
                if not os.path.exists(st.session_state.output_path):
                    st.error("Output file was not created successfully")
                    return
                
                # Load the processed file into a DataFrame
                st.session_state.df = pd.read_excel(st.session_state.output_path)
                st.success("File processed successfully!")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    if st.session_state.df is not None:
        # Edit the DataFrame directly in Streamlit
        st.subheader("Edit Transactions")
        
        # Create an editable dataframe
        edited_df = st.data_editor(
            st.session_state.df,
            num_rows="dynamic",  # Allow adding/deleting rows
            use_container_width=True,
            height=500,
            key="data_editor"
        )
        
        # Update session state with edited dataframe
        st.session_state.df = edited_df
        
        # Save changes button
        if st.button("💾 Save Changes"):
            st.session_state.df.to_excel(st.session_state.output_path, index=False)
            st.success(f"Changes saved to: {st.session_state.output_path}")
        
        # Download edited file
        with open(st.session_state.output_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Edited File",
                data=f,
                file_name=os.path.basename(st.session_state.output_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Display the current file path
        st.info(f"Current file location: {st.session_state.output_path}")
        
        # Reset button
        if st.button("🔄 Process New File"):
            st.session_state.output_path = None
            st.session_state.df = None
            st.rerun()

if __name__ == "__main__":
    main()