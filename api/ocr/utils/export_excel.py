import pandas as pd
import xlsxwriter

def export_to_excel(df, output_path, account=None, ledger=None, opening_balance=None, closing_balance=None):
    print("===== here is export to excel")
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Statement")
        writer.sheets["Statement"] = worksheet

        #  Header Info (write manually)
        worksheet.write("A1", "Account:")
        worksheet.write("B1", account or "N/A")

        worksheet.write("A2", "Ledger:")
        worksheet.write("B2", ledger or "N/A")

        worksheet.write("A3", "Opening Balance:")
        worksheet.write("B3", opening_balance if opening_balance is not None else "N/A")

        worksheet.write("A4", "Closing Balance:")
        worksheet.write("B4", closing_balance if closing_balance is not None else "N/A")

        #  Write DataFrame below the header (start at row 6 = index 5)
        df_start_row = 4
        df.to_excel(writer, sheet_name="Statement", startrow=df_start_row, index=False)

        print(f"Excel file saved to: {output_path}")
