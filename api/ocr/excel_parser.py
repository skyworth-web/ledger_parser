import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import json
import numpy as np
from api.ocr.utils.validate_and_fix import validate_and_fix
from api.ocr.utils.export_excel import export_to_excel
from datetime import datetime

load_dotenv()
# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def excel_to_csv_text(file_path):
    try:
        df = pd.read_excel(file_path)
        return df.to_csv(index=False)
    except Exception as e:
        print(f"Failed to read Excel: {e}")
        return ""

def parse_excel_with_openai(csv_text):
    """Use OpenAI to parse Excel CSV text into structured JSON"""

    system_prompt = """
You are a bank statement parser. Extract structured financial data from the CSV below.

Return a JSON object with:
    - Account: [Full account name]
    - Ledger: [Bank name]
    - "opening_balance": null if there is no opening balance field or previous balance field in the image
    - "closing_balance": float
    - "transactions": [ 
        {
            "date": "YYYY-MM-DD",
            "description": "text",
            "debit": float (0.00),
            "credit": float (0.00),
            "balance": float (don't calculate)
        }
    Handle multi-line entries and currency symbols."""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": csv_text}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def process_excel_bank_statement(file_path):
    csv_text = excel_to_csv_text(file_path)
    if not csv_text:
        return pd.DataFrame()

    parsed = parse_excel_with_openai(csv_text)

    return parsed

def excel_parser(file_path):
    parsed_data = process_excel_bank_statement(file_path)

    all_transactions = []
    opening_balance = None
    closing_balance = None
    account_name = None
    ledger_name = None
    output_path = ''

    current_time = datetime.now()
    time_str = current_time.strftime("_%Y%m%d_%H%M%S")
    output_path = './data/output/' + os.path.splitext(file_path.name)[0] + time_str + '.xlsx'

    if isinstance(parsed_data, dict):
        all_transactions.extend(parsed_data.get("transactions", []))

        # Balances
        opening_balance = parsed_data.get("opening_balance")
        closing_balance = parsed_data.get("closing_balance")
        account_name = parsed_data.get('Account')
        ledger_name = parsed_data.get('Ledger')

    df = pd.DataFrame(all_transactions) if all_transactions else pd.DataFrame()


    if not opening_balance:
        if df['balance'].iloc[0]:
            opening_balance = df['balance'].iloc[0] + df['debit'].iloc[0] - df['credit'].iloc[0]
        else:
            opening_balance = 0

    df = validate_and_fix(ledger_name, opening_balance, df)
    if not df.empty:
        df = validate_and_fix(ledger_name, opening_balance, df)
        export_to_excel(
            df,
            output_path=output_path,
            account=account_name,
            ledger=ledger_name,
            opening_balance=opening_balance,
            closing_balance=closing_balance
        )
    else:
        print("No transactions found in the document")

    return output_path