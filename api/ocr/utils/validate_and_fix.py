import pandas as pd

def validate_and_fix(ledger_name: str, opening_balance: float, df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    
    # Case 1: Handle missing balances
    if df['balance'].isna().any():
        return _fix_missing_balances(df, opening_balance)
    
    # Case 2: Check if balances already correct
    calculated_final_balance = opening_balance + df['credit'].sum() - df['debit'].sum()
    if abs(calculated_final_balance - df['balance'].iloc[-1]) < 1e-9:  # Floating point comparison
        return df
    
    # Case 3: Handle shifted balances
    if (abs(opening_balance - df['balance'].iloc[0]) < 1e-9 and 
        ((df['credit'] != 0) & (df['debit'] != 0)).any()):
        return _fix_shifted_balances(df, ledger_name)
    
    # Case 4: Recalculate transactions to match balances
    return _recalculate_transactions(df, opening_balance)


def _fix_missing_balances(df: pd.DataFrame, opening_balance: float) -> pd.DataFrame:
    """Calculate missing balances based on opening balance and transactions"""
    df = df.copy()
    df.loc[df.index[0], 'balance'] = opening_balance + df['credit'].iloc[0] - df['debit'].iloc[0]
    
    for i in range(1, len(df)):
        df.loc[df.index[i], 'balance'] = (
            df['balance'].iloc[i-1] + df['credit'].iloc[i] - df['debit'].iloc[i]
        )
    
    return df


def _fix_shifted_balances(df: pd.DataFrame, ledger_name: str) -> pd.DataFrame:
    """Fix cases where balances are offset by one row"""
    df = df.copy()
    
    if "Emirates NBD" in ledger_name:
        df[['credit', 'debit']] = df[['debit', 'credit']].values
    
    df['balance'] = df['balance'].shift(-1)
    df.loc[df.index[-1], 'balance'] = (
        df['balance'].iloc[-2] + df['credit'].iloc[-1] - df['debit'].iloc[-1]
    )
    
    return df


def _recalculate_transactions(df: pd.DataFrame, opening_balance: float) -> pd.DataFrame:
    """Recalculate credit/debit amounts to match existing balances"""
    df = df.copy()
    
    # Fix first row
    balance_diff = opening_balance - df['balance'].iloc[0]
    if balance_diff > 0:
        df.loc[df.index[0], 'debit'] = balance_diff
        df.loc[df.index[0], 'credit'] = 0
    else:
        df.loc[df.index[0], 'credit'] = abs(balance_diff)
        df.loc[df.index[0], 'debit'] = 0
    
    # Fix subsequent rows
    for i in range(1, len(df)):
        balance_diff = df['balance'].iloc[i-1] - df['balance'].iloc[i]
        if balance_diff > 0:
            df.loc[df.index[i], 'debit'] = balance_diff
            df.loc[df.index[i], 'credit'] = 0
        else:
            df.loc[df.index[i], 'credit'] = abs(balance_diff)
            df.loc[df.index[i], 'debit'] = 0
    
    return df