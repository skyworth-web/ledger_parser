import os
import streamlit as st
import pandas as pd
from api.ocr.excel_parser import excel_parser
from api.ocr.image_parser import image_parser

# Set page config
st.set_page_config(page_title="Bank Statement Editor", layout="centered")
st.title("🏦 Bank Statement Editor")

def initialize_session():
    if 'processed' not in st.session_state:
        st.session_state.processed = False
    if 'output_path' not in st.session_state:
        st.session_state.output_path = None
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'editor_key' not in st.session_state:
        st.session_state.editor_key = 0
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'last_saved_df' not in st.session_state:
        st.session_state.last_saved_df = None
    if 'metadata' not in st.session_state:
        st.session_state.metadata = None


def process_file():
    if st.session_state.uploaded_file is None:
        st.warning("No file uploaded!")
        return False

    try:
        with st.spinner("🔍 Extracting and analyzing..."):
            file_name = st.session_state.uploaded_file.name
            if file_name.endswith((".xlsx", ".xls")):
                st.session_state.output_path = excel_parser(st.session_state.uploaded_file)
            elif file_name.endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp")):
                st.session_state.output_path = image_parser(st.session_state.uploaded_file)
            else:
                st.error("Unsupported file type.")
                return False

            if not os.path.exists(st.session_state.output_path):
                st.error("Output file was not created successfully")
                return False

            # Load entire file (no header yet)
            full_df = pd.read_excel(st.session_state.output_path, header=None)

            # Find where transaction table starts (look for "date" in first col)
            table_start_idx = full_df[0].astype(str).str.lower().eq("date").idxmax()

            # Split into metadata + data table
            metadata = full_df.iloc[:table_start_idx]
            table = pd.read_excel(st.session_state.output_path, skiprows=table_start_idx)

            if "date" in table.columns:
                table["date"] = pd.to_datetime(table["date"], errors='coerce')

            # Save both parts
            st.session_state.metadata = metadata
            st.session_state.df = table
            st.session_state.last_saved_df = table.copy()
            st.session_state.processed = True
            st.session_state.editor_key += 1

            st.success("File processed successfully!")
            return True

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return False


def save_changes():
    try:
        with pd.ExcelWriter(st.session_state.output_path, engine='openpyxl') as writer:
            # Write metadata
            st.session_state.metadata.to_excel(writer, index=False, header=False)
            # Write edited table just below it
            st.session_state.df.to_excel(writer, index=False, startrow=len(st.session_state.metadata))
        st.session_state.last_saved_df = st.session_state.df.copy()
        st.success("✅ Changes saved successfully!")
        st.session_state.editor_key += 1
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")


def main():
    initialize_session()

    uploaded_file = st.file_uploader(
        "Upload PDF, Image, or Excel",
        type=["pdf", "png", "jpg", "jpeg", "webp", "xls", "xlsx"],
        key="file_uploader"
    )

    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file

    if st.session_state.uploaded_file:
        if st.button("🔍 Extract Data", type="primary"):
            if process_file():
                st.rerun()

    if st.session_state.processed and st.session_state.df is not None:
        st.subheader("Edit Transactions")

        with st.form("edit_form", clear_on_submit=False):
            # Automatically make all columns editable
            column_config = {}
            for col in st.session_state.df.columns:
                dtype = st.session_state.df[col].dtype

                if pd.api.types.is_datetime64_any_dtype(dtype):
                    column_config[col] = st.column_config.DateColumn(col, format="YYYY-MM-DD", required=False)
                elif pd.api.types.is_numeric_dtype(dtype):
                    column_config[col] = st.column_config.NumberColumn(col, format="%.2f")
                else:
                    column_config[col] = st.column_config.TextColumn(col)


            # Apply special formatting if certain columns exist
            if "date" in column_config:
                column_config["date"] = st.column_config.DateColumn("Date", required=False)
            if "amount" in column_config:
                column_config["amount"] = st.column_config.NumberColumn("Amount", format="$%.2f")

            edited_df = st.data_editor(
                st.session_state.df,
                num_rows="dynamic",
                use_container_width=True,
                height=500,
                key=f"editor_{st.session_state.editor_key}",
                column_config=column_config
            )

            submitted = st.form_submit_button("✅ Apply Changes")
            if submitted:
                st.session_state.df = edited_df
                st.success("Changes applied to table.")

        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Save Changes", help="Save changes to original file"):
                save_changes()
        with col2:
            if st.button("🔄 Reset to Last Saved", help="Discard unsaved changes"):
                st.session_state.df = st.session_state.last_saved_df.copy()
                st.session_state.editor_key += 1
                st.rerun()
        with col3:
            if st.button("✖️ New File", help="Start over with a new file"):
                for key in ['processed', 'output_path', 'df', 'uploaded_file', 'last_saved_df']:
                    st.session_state[key] = None
                st.session_state.editor_key = 0
                st.rerun()

        # File info and download
        st.divider()
        st.caption(f"Editing: {os.path.basename(st.session_state.output_path)}")
        with open(st.session_state.output_path, "rb") as f:
            st.download_button(
                "⬇️ Download Current Version",
                data=f,
                file_name=f"edited_{os.path.basename(st.session_state.output_path)}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
