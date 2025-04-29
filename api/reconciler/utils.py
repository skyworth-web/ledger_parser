import math
import pandas as pd
from datetime import datetime, date
from config_utils import load_config

config = load_config()
amount_tolerance = config.get("match_tolerance", 0.01)

def process_date_cell(date_value):
    print("Processing date cell...")
    """
    Convert various input date formats into an actual Python date object
    (not datetime). If not parseable, return None.
    """
    if date_value is None:
        return None

    # If it's already a datetime or date, convert to date
    if isinstance(date_value, (datetime, date)):
        return date_value if isinstance(date_value, date) else date_value.date()

    # If it's a string, try to parse with pandas
    if isinstance(date_value, str):
        try:
            parsed = pd.to_datetime(date_value, errors="raise")
            return parsed.date()  # Return just the date (no time)
        except:
            return None

    return None

def compare_values(a, b, tolerance = amount_tolerance):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) < tolerance

def mark_match(df1, df2, i, j, remark, unmatched_df1, unmatched_df2, data_start_row,
               matched_rows1, matched_rows2, fuzzy_rows1, fuzzy_rows2):
    df1.at[i, "Remarks"] = remark
    df2.at[j, "Remarks"] = remark
    r1 = i + data_start_row
    r2 = j + data_start_row
    if remark == "Matched":
        matched_rows1.append(r1)
        matched_rows2.append(r2)
    elif remark == "Matched but check date":
        fuzzy_rows1.append(r1)
        fuzzy_rows2.append(r2)
    unmatched_df1.discard(i)
    unmatched_df2.discard(j)

def round_half_up(n):
    if n is None:
        return None
    if isinstance(n, (int, float)):
        return math.floor(n + 0.5) if n >= 0 else math.ceil(n - 0.5)
    return n

def calculate_closing_balance(df):
    print("Calculating closing balance...")
    df_filled = df.fillna(0)
    sum_debit = df_filled["debit"].sum()
    sum_credit = df_filled["credit"].sum()
    if sum_credit > sum_debit:
        closing_debit = sum_credit - sum_debit
        closing_credit = 0
    else:
        closing_debit = 0
        closing_credit = sum_debit - sum_credit
    return closing_debit, closing_credit
