import os
import streamlit as st
import pandas as pd
from api.ocr.excel_parser import excel_parser
from api.ocr.image_parser import image_parser

st.set_page_config(page_title="Bank Statement Editor", layout="centered")
st.title("f3e6 Bank Statement Editor")

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
    if 'last_opening_balance' not in st.session_state:
        st.session_state.last_opening_balance = None

def recalculate_balance(df, opening_balance=0):
    df = df.copy()
    if not all(col in df.columns for col in ['debit', 'credit']):
        return df
    df[['debit', 'credit']] = df[['debit', 'credit']].fillna(0)
    df['balance'] = opening_balance + (df['credit'] - df['debit']).cumsum()
    return df

def update_closing_balance_in_metadata(new_closing_balance):
    if st.session_state.metadata is not None:
        try:
            mask = st.session_state.metadata['Field'].str.lower().str.contains('closing balance', na=False)
            if mask.any():
                idx = mask.idxmax()
                st.session_state.metadata.at[idx, 'Value'] = f"{new_closing_balance:.2f}"
            else:
                st.session_state.metadata = pd.concat([
                    st.session_state.metadata,
                    pd.DataFrame([["Closing Balance", f"{new_closing_balance:.2f}"]], columns=['Field', 'Value'])
                ], ignore_index=True)
        except Exception as e:
            st.error(f"Error updating closing balance: {e}")

def process_file():
    if st.session_state.uploaded_file is None:
        st.warning("No file uploaded!")
        return False

    try:
        with st.spinner("🔍 Extracting and analyzing..."):
            file_name = st.session_state.uploaded_file.name
            if file_name.lower().endswith((".xlsx", ".xls")):
                st.session_state.output_path = excel_parser(st.session_state.uploaded_file)
            elif file_name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp")):
                st.session_state.output_path = image_parser(st.session_state.uploaded_file)
            else:
                st.error("Unsupported file type.")
                return False

            if not os.path.exists(st.session_state.output_path):
                st.error("Output file was not created successfully")
                return False

            full_df = pd.read_excel(st.session_state.output_path, header=None)
            date_mask = full_df[0].astype(str).str.lower().eq("date")
            if not date_mask.any():
                st.error("Could not detect 'date' header row in the file.")
                return False
            table_start_idx = date_mask.idxmax()

            metadata = full_df.iloc[:table_start_idx, :2].copy()
            metadata.columns = [0, 1]
            table = pd.read_excel(st.session_state.output_path, skiprows=table_start_idx)
            if 'date' in table.columns:
                table['date'] = pd.to_datetime(table['date'], errors='coerce')

            opening_balance = 0
            try:
                ob = metadata[metadata[0].astype(str).str.lower().str.contains('opening balance', na=False)][1]
                if not ob.empty:
                    opening_balance = float(ob.values[0])
            except:
                pass

            table = recalculate_balance(table, opening_balance)
            meta_df = metadata.copy().astype(str)
            meta_df.columns = ['Field', 'Value']
            closing = table['balance'].iloc[-1]
            meta_df.loc[meta_df['Field'].str.lower().str.contains('closing balance', na=False), 'Value'] = f"{closing:.2f}"

            st.session_state.metadata = meta_df
            st.session_state.df = table
            st.session_state.last_saved_df = table.copy()
            st.session_state.last_opening_balance = opening_balance
            st.session_state.processed = True
            st.session_state.editor_key += 1
            st.success("File processed successfully!")
            return True
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return False

def save_changes():
    try:
        df_to_save = st.session_state.df.copy()
        if 'date' in df_to_save.columns:
            df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d')

        with pd.ExcelWriter(st.session_state.output_path, engine='openpyxl') as writer:
            st.session_state.metadata.to_excel(writer, index=False, header=False)
            pd.DataFrame([[]]).to_excel(writer, index=False, header=False, startrow=len(st.session_state.metadata))
            df_to_save.to_excel(writer, index=False, startrow=len(st.session_state.metadata) + 1)

        st.session_state.last_saved_df = st.session_state.df.copy()
        st.success("✅ Changes saved successfully!")
        st.session_state.editor_key += 1
    except Exception as e:
        st.error(f"Error saving file: {e}")

def main():
    initialize_session()
    uploaded = st.file_uploader("Upload PDF, Image, or Excel", type=["pdf", "png", "jpg", "jpeg", "webp", "xls", "xlsx"], key="file_uploader")
    if uploaded:
        st.session_state.uploaded_file = uploaded
    if st.session_state.uploaded_file and st.button("🔍 Extract Data"):
        if process_file(): st.rerun()

    if st.session_state.processed:
        st.subheader("🧾 Metadata")
        meta = st.session_state.metadata.copy()
        edited_meta = st.data_editor(meta, key=f"meta_{st.session_state.editor_key}", use_container_width=True, num_rows="dynamic",
                                     column_config={"Field": st.column_config.TextColumn("Field"), "Value": st.column_config.TextColumn("Value")})

        # Check manual edit of opening balance
        try:
            ob_mask = edited_meta["Field"].str.lower().str.contains("opening balance", na=False)
            if ob_mask.any():
                idx = ob_mask.idxmax()
                new_ob_val = float(edited_meta.at[idx, "Value"])
                if new_ob_val != st.session_state.last_opening_balance:
                    st.session_state.df = recalculate_balance(st.session_state.df, new_ob_val)
                    st.session_state.last_opening_balance = new_ob_val
                    update_closing_balance_in_metadata(st.session_state.df["balance"].iloc[-1])
                    edited_meta.at[idx, "Value"] = f"{new_ob_val:.2f}"
                    st.session_state.metadata = edited_meta
                    st.session_state.editor_key += 1
                    st.rerun()
        except Exception as e:
            st.warning("Opening Balance must be a number.")

        if "metadata" in st.session_state:
            st.session_state.metadata = edited_meta

        # Negate Button
        if st.button("⇄️ Negate Opening Balance"):
            mask = edited_meta["Field"].str.lower().str.contains("opening balance", na=False)
            if mask.any():
                idx = mask.idxmax()
                val = float(edited_meta.at[idx, "Value"] or 0)
                edited_meta.at[idx, "Value"] = f"{(-val):.2f}"
                st.session_state.metadata = edited_meta
                st.session_state.df = recalculate_balance(st.session_state.df, -val)
                update_closing_balance_in_metadata(st.session_state.df['balance'].iloc[-1])
                st.session_state.last_opening_balance = -val
                st.session_state.editor_key += 1
                st.rerun()

        # Transactions
        st.subheader("📊 Edit Transactions")
        df = st.session_state.df.copy()
        if st.session_state.last_opening_balance is not None:
            df = recalculate_balance(df, st.session_state.last_opening_balance)
            st.session_state.df = df

        cfg = {}
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c].dtype): cfg[c] = st.column_config.DateColumn(c)
            elif pd.api.types.is_numeric_dtype(df[c].dtype): cfg[c] = st.column_config.NumberColumn(c, format="%.2f", disabled=(c == "balance"))
            else: cfg[c] = st.column_config.TextColumn(c)

        edited_tbl = st.data_editor(df, key=f"tbl_{st.session_state.editor_key}", column_config=cfg, use_container_width=True, num_rows="dynamic", height=400)

        ed_cols = [c for c in df.columns if c != "balance"]
        if not edited_tbl[ed_cols].equals(st.session_state.df[ed_cols]):
            for c in ed_cols:
                st.session_state.df[c] = edited_tbl[c]
            st.session_state.df = recalculate_balance(st.session_state.df, st.session_state.last_opening_balance)
            update_closing_balance_in_metadata(st.session_state.df['balance'].iloc[-1])
            st.session_state.editor_key += 1
            st.rerun()

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📂 Save Changes"):
                save_changes()
        with c2:
            if st.button("🔄 Reset"):
                st.session_state.df = st.session_state.last_saved_df.copy()
                st.session_state.editor_key += 1
                st.rerun()
        with c3:
            if st.button("✖️ New File"):
                for k in ['processed', 'output_path', 'df', 'uploaded_file', 'last_saved_df', 'metadata', 'last_opening_balance']:
                    st.session_state.pop(k, None)
                st.session_state.editor_key = 0
                st.rerun()

        st.divider()
        st.caption(f"Editing: {os.path.basename(st.session_state.output_path)}")
        with open(st.session_state.output_path, 'rb') as f:
            st.download_button("⬇️ Download Current Version", data=f, file_name=f"edited_{os.path.basename(st.session_state.output_path)}", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
