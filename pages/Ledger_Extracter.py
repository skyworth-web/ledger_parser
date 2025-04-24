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

            full_df = pd.read_excel(st.session_state.output_path, header=None)
            table_start_idx = full_df[0].astype(str).str.lower().eq("date").idxmax()
            metadata = full_df.iloc[:table_start_idx].copy()
            table = pd.read_excel(st.session_state.output_path, skiprows=table_start_idx)

            if "date" in table.columns:
                table["date"] = pd.to_datetime(table["date"], errors='coerce')

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
            st.session_state.metadata.to_excel(writer, index=False, header=False)
            st.session_state.df.to_excel(writer, index=False, startrow=len(st.session_state.metadata))
        st.session_state.last_saved_df = st.session_state.df.copy()
        st.success("✅ Changes saved successfully!")
        st.session_state.editor_key += 1
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")

def recalculate_balance(df, opening_balance=None):
    df = df.copy()
    if opening_balance is None:
        try:
            # Try to get from metadata if exists
            opening_balance = float(
                df.loc[0, "balance"]
                if "balance" in df.columns
                else 0
            )
        except:
            opening_balance = 0

    df["balance"] = opening_balance
    for i in range(len(df)):
        debit = df.at[i, "debit"] if "debit" in df.columns else 0
        credit = df.at[i, "credit"] if "credit" in df.columns else 0

        debit = float(debit) if pd.notna(debit) else 0
        credit = float(credit) if pd.notna(credit) else 0

        if i == 0:
            df.at[i, "balance"] = opening_balance + credit - debit
        else:
            df.at[i, "balance"] = df.at[i-1, "balance"] + credit - debit
    
    print("====> recalculted balance", df)
    return df


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

    if st.session_state.processed:
        st.subheader("🧾 Metadata")

        meta_df = st.session_state.metadata.copy()

        # Ensure exactly 2 columns, and convert both to strings
        meta_df = meta_df.iloc[:, :2]
        meta_df.columns = ["Field", "Value"]
        meta_df = meta_df.astype(str)  # <- Force both columns to string type

        meta_edited = st.data_editor(
            meta_df,
            key=f"meta_editor_{st.session_state.editor_key}",
            column_config={
                "Field": st.column_config.TextColumn("Field"),
                "Value": st.column_config.TextColumn("Value"),  # Editable now
            },
            use_container_width=True,
            num_rows="dynamic"
        )

        st.session_state.metadata = meta_edited


        # === Editable Transactions Section ===
        st.subheader("📊 Edit Transactions")

        # Always use current working df
        working_df = st.session_state.df.copy()

        # Try to get opening balance from metadata
        opening_balance = None
        if st.session_state.metadata is not None:
            meta_df = st.session_state.metadata
            try:
                meta_df.columns = ["Field", "Value"]
                opening_balance_row = meta_df[meta_df["Field"].str.lower().str.contains("opening balance")]
                if not opening_balance_row.empty:
                    opening_balance = float(opening_balance_row["Value"].values[0])
            except:
                opening_balance = None

        # Recalculate balance before editing
        working_df = recalculate_balance(working_df, opening_balance=opening_balance)

        # Define column configs
        column_config = {}
        for col in working_df.columns:
            dtype = working_df[col].dtype
            if pd.api.types.is_datetime64_any_dtype(dtype):
                column_config[col] = st.column_config.DateColumn(col, format="YYYY-MM-DD", required=False)
            elif pd.api.types.is_numeric_dtype(dtype):
                if col.lower() == "amount":
                    column_config[col] = st.column_config.NumberColumn(col, format="$%.2f")
                else:
                    column_config[col] = st.column_config.NumberColumn(col, format="%.2f")
            else:
                column_config[col] = st.column_config.TextColumn(col)

        # Disable editing of balance column (optional)
        if "balance" in column_config:
            column_config["balance"] = st.column_config.NumberColumn("Balance", format="%.2f", disabled=True)

        # Show editable table (no balance yet)
        editable_columns = [col for col in working_df.columns if col.lower() not in ["balance"]]
        editable_df = working_df[editable_columns].copy()

        edited_df = st.data_editor(
            editable_df,
            num_rows="dynamic",
            use_container_width=True,
            height=500,
            key=f"editor_{st.session_state.editor_key}",
            column_config={col: column_config[col] for col in editable_columns}
        )

        # Detect if anything changed from previous
        if not edited_df.equals(st.session_state.df[editable_columns]):
            # Copy edited values into df
            for col in editable_columns:
                st.session_state.df[col] = edited_df[col]

            # Recalculate balance
            st.session_state.df = recalculate_balance(st.session_state.df, opening_balance=opening_balance)
            st.success("✅ Balance recalculated after edit.")

        # Show updated table with balance
        st.dataframe(st.session_state.df, use_container_width=True)



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
                for key in ['processed', 'output_path', 'df', 'uploaded_file', 'last_saved_df', 'metadata']:
                    st.session_state[key] = None
                st.session_state.editor_key = 0
                st.rerun()

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
