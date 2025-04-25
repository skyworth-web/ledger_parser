import os
import torch
torch.classes.__path__ = []

from datetime import datetime
import tempfile
from openai import OpenAI
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from dotenv import load_dotenv
import pandas as pd
import json
import numpy as np
from api.ocr.utils.validate_and_fix import validate_and_fix
from api.ocr.utils.export_excel import export_to_excel

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_with_doctr(file_bytes, file_extension):
    """Extract text using Doctrine OCR from bytes"""
    model = ocr_predictor(pretrained=True)
    
    # Save bytes to a temporary file
    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    try:
        if file_extension.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            doc = DocumentFile.from_images(tmp_path)
        elif file_extension.lower() == '.pdf':
            doc = DocumentFile.from_pdf(tmp_path)
        else:
            raise ValueError("Unsupported file format")
        
        result = model(doc)
        return result.render()
    finally:
        # Clean up the temporary file
        os.unlink(tmp_path)

def parse_with_openai(text):
    """Use OpenAI to extract transaction table"""
    system_prompt = """
    Extract transactions into JSON array with:
    - Account: [Full account name]
    - Ledger: [Bank name]
    - "opening_balance": null if there is no "opening balance" field or "previous balance" field in the image
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
            {"role": "user", "content": text}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def process_statements(file_bytes, file_extension):
    try:
        text = extract_text_with_doctr(file_bytes, file_extension)
        if not text.strip():
            print("No text found in file")
            return None
        return parse_with_openai(text)              
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

def image_parser(uploaded_file):
    all_transactions = []
    opening_balance = None
    closing_balance = None
    account_name = None
    ledger_name = None
    output_path = ''

    current_time = datetime.now()
    time_str = current_time.strftime("_%Y%m%d_%H%M%S")
    output_path = './data/output/' + os.path.splitext(uploaded_file.name)[0] + time_str + '.xlsx'
    # Get file extension
    file_extension = os.path.splitext(uploaded_file.name)[1]
    
    # Read file bytes
    file_bytes = uploaded_file.read()
    
    parsed_data = process_statements(file_bytes, file_extension)

    if parsed_data and isinstance(parsed_data, dict):
        all_transactions.extend(parsed_data.get("transactions", []))
        opening_balance = parsed_data.get("opening_balance")
        closing_balance = parsed_data.get("closing_balance")
        account_name = parsed_data.get('Account')
        ledger_name = parsed_data.get('Ledger')

    df = pd.DataFrame(all_transactions) if all_transactions else pd.DataFrame()

    if not opening_balance:
        if not df.empty and 'balance' in df.columns and df['balance'].iloc[0]:
            opening_balance = df['balance'].iloc[0] + df['debit'].iloc[0] - df['credit'].iloc[0]
        else:
            opening_balance = 0
    
    if not df.empty:
        df = validate_and_fix(ledger_name, opening_balance, df)
        closing_balance = df['balance'].iloc[-1]
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