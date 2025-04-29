import logging
import pandas as pd
from api.reconciler.utils import compare_values, mark_match, round_half_up
from api.reconciler.config_utils import load_config

config = load_config()
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

AMOUNT_TOLERANCE = 0.01
ROUNDING_TOLERANCE = 0.5

def find_exact_matches(df1, df2, unmatched_df1, unmatched_df2, data_start_row,
                      matched_rows1, matched_rows2, fuzzy_rows1, fuzzy_rows2, config=config):
    exact_count = 0
    exact_candidates = []
    if not config.get("enable_exact_match", True):
        return 0

    tolerance = config.get("match_tolerance", 0.01)
    for i in unmatched_df1:
        for j in unmatched_df2:
            # debit in df1 matches credit in df2 or vice versa
            if ((compare_values(df1.at[i, "debit"], df2.at[j, "credit"], tolerance) and
                 compare_values(df1.at[i, "credit"], df2.at[j, "debit"], tolerance)) or
                (compare_values(df1.at[i, "debit"], df2.at[j, "debit"], tolerance) and
                 compare_values(df1.at[i, "credit"], df2.at[j, "credit"], tolerance))):

                date1 = df1.at[i, "date"]
                date2 = df2.at[j, "date"]
                if pd.isna(date1) or pd.isna(date2):
                    date_match = False
                else:
                    if isinstance(date1, str):
                        try:
                            date1 = pd.to_datetime(date1)
                        except:
                            pass
                    if isinstance(date2, str):
                        try:
                            date2 = pd.to_datetime(date2)
                        except:
                            pass
                    if isinstance(date1, pd.Timestamp) and isinstance(date2, pd.Timestamp):
                        date_match = date1.date() == date2.date()
                    else:
                        date_match = (date1 == date2)
                if date_match:
                    exact_candidates.append((i, j))

    for i, j in exact_candidates:
        if i in unmatched_df1 and j in unmatched_df2:
            mark_match(df1, df2, i, j, "Matched",
                       unmatched_df1, unmatched_df2,
                       data_start_row, matched_rows1, matched_rows2,
                       fuzzy_rows1, fuzzy_rows2)
            exact_count += 1
    logger.info(f"Found {exact_count} exact matches.")
    return exact_count

def find_fuzzy_matches(df1, df2, unmatched_df1, unmatched_df2, data_start_row,
                      matched_rows1, matched_rows2, fuzzy_rows1, fuzzy_rows2, config):
    if not config.get("enable_fuzzy_match", True):
        return 0

    fuzzy_count = 0
    fuzzy_candidates = []

    # Use user-defined date range
    max_date_diff = config.get("fuzzy_date_range", 7)
    amount_tolerance = config.get("match_tolerance", 0.01)

    for i in unmatched_df1:
        for j in unmatched_df2:
            if ((compare_values(df1.at[i, "debit"], df2.at[j, "credit"], amount_tolerance) and
                 compare_values(df1.at[i, "credit"], df2.at[j, "debit"], amount_tolerance)) or
                (compare_values(df1.at[i, "debit"], df2.at[j, "debit"], amount_tolerance) and
                 compare_values(df1.at[i, "credit"], df2.at[j, "credit"], amount_tolerance))):

                date1 = df1.at[i, "date"]
                date2 = df2.at[j, "date"]

                if pd.isna(date1) or pd.isna(date2):
                    continue

                try:
                    date1 = pd.to_datetime(date1)
                    date2 = pd.to_datetime(date2)
                except:
                    continue

                if isinstance(date1, pd.Timestamp) and isinstance(date2, pd.Timestamp):
                    date_diff = abs((date1 - date2).days)
                    if 1 <= date_diff <= max_date_diff:
                        fuzzy_candidates.append((i, j, date_diff))

    fuzzy_candidates.sort(key=lambda x: x[2])

    for i, j, _ in fuzzy_candidates:
        if i in unmatched_df1 and j in unmatched_df2:
            mark_match(df1, df2, i, j, "Matched but check date",
                       unmatched_df1, unmatched_df2,
                       data_start_row, matched_rows1, matched_rows2,
                       fuzzy_rows1, fuzzy_rows2)
            fuzzy_count += 1

    logger.info(f"Found {fuzzy_count} fuzzy matches.")
    return fuzzy_count


def subset_sum(candidates, target, tolerance):
    if abs(target) < tolerance:
        return []
    for i, (idx, value) in enumerate(candidates):
        if abs(value - target) < tolerance:
            return [idx]
    if len(candidates) >= 2:
        for i, (idx_i, val_i) in enumerate(candidates):
            for j, (idx_j, val_j) in enumerate(candidates[i+1:], i+1):
                if abs((val_i + val_j) - target) < tolerance:
                    return [idx_i, idx_j]
    n = len(candidates)
    if n <= 10:
        for mask in range(1, 1 << n):
            indices = []
            values_sum = 0
            for bit in range(n):
                if mask & (1 << bit):
                    indices.append(candidates[bit][0])
                    values_sum += candidates[bit][1]
            if abs(values_sum - target) < tolerance:
                return indices
    return None

def find_split_transactions(df_source, df_target, unmatched_source, unmatched_target,
                           data_start_row, split_rows_source, split_rows_target, config):
    if not config.get("enable_split_match", True):
        return 0

    split_count = 0
    date_range = config.get("split_match_date_range", 3)
    amount_tolerance = config.get("match_tolerance", 0.01)

    for i in list(unmatched_source):
        if i not in unmatched_source:
            continue

        row = df_source.loc[i]
        if row["debit"] > 0 and row["credit"] == 0:
            req = row["debit"]
            sign = "credit"
        elif row["credit"] > 0 and row["debit"] == 0:
            req = row["credit"]
            sign = "debit"
        else:
            continue

        tdate = pd.to_datetime(row["date"], errors="coerce")
        if tdate is pd.NaT:
            continue

        candidates = []
        for j in unmatched_target:
            target_row = df_target.loc[j]
            if target_row[sign] <= 0:
                continue

            target_date = pd.to_datetime(target_row["date"], errors="coerce")
            if target_date is pd.NaT:
                continue

            if abs((tdate - target_date).days) <= date_range:
                candidates.append((j, target_row[sign]))

        chosen = subset_sum(candidates, req, tolerance=amount_tolerance)
        if chosen:
            df_source.at[i, "Remarks"] = "Split Transaction"
            split_rows_source.append(i + data_start_row)
            for j in chosen:
                df_target.at[j, "Remarks"] = "Split Transaction"
                split_rows_target.append(j + data_start_row)
                unmatched_target.discard(j)
            unmatched_source.discard(i)
            split_count += 1

    logger.info(f"Found {split_count} split transactions.")
    return split_count


def find_rounding_errors(df1, df2, unmatched_df1, unmatched_df2,
                        data_start_row, rounding_rows1, rounding_rows2, config):
    if not config.get("enable_rounding_match", True):
        return 0

    rounding_count = 0
    tolerance = config.get("rounding_tolerance", 0.5)
    date_diff = config.get("rounding_date_range", 2)

    for i in list(unmatched_df1):
        for j in list(unmatched_df2):
            date1 = df1.at[i, "date"]
            date2 = df2.at[j, "date"]

            try:
                date1 = pd.to_datetime(date1)
                date2 = pd.to_datetime(date2)
            except:
                continue

            if abs((date1 - date2).days) > date_diff:
                continue

            debit1 = df1.at[i, "debit"]
            credit1 = df1.at[i, "credit"]
            debit2 = df2.at[j, "debit"]
            credit2 = df2.at[j, "credit"]

            # Match debit vs credit (and vice versa)
            for x, y in [(debit1, credit2), (credit1, debit2)]:
                if x > 0 and y > 0 and abs(x - y) < tolerance and round_half_up(x) == round_half_up(y):
                    msg = f"Rounding Error: {x:.2f} vs {y:.2f}"
                    df1.at[i, "Remarks"] = msg
                    df2.at[j, "Remarks"] = msg
                    rounding_rows1.append(i + data_start_row)
                    rounding_rows2.append(j + data_start_row)
                    unmatched_df1.discard(i)
                    unmatched_df2.discard(j)
                    rounding_count += 1
                    break

    logger.info(f"Found {rounding_count} rounding errors.")
    return rounding_count
