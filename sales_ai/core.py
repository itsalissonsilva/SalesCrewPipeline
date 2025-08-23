import os, re, json
from typing import Any, Dict, Optional
import pandas as pd

# Default CSV path (override with SALES_CSV in .env if you want)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.getenv("SALES_CSV") or os.path.join(PROJECT_ROOT, "data", "sales.csv")

ALIAS_MAP = {
    "local": "location",
    "produto": "product_id",
    "produto_id": "product_id",
    "productid": "product_id",
    "actualquantity": "actual_quantity",
    "plannedquantity": "planned_quantity",
    "plannedprice": "planned_price",
    "actualprice": "actual_price",
    "promotiontype": "promotion_type",
    "servicelevel": "service_level",
}

def _load_df() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"sales.csv not found at {CSV_PATH}")
    try:
        df = pd.read_csv(CSV_PATH, sep=None, engine="python")
    except Exception:
        df = pd.read_csv(CSV_PATH, sep=";")
    if len(df.columns) == 1 and ";" in df.columns[0]:
        df = pd.read_csv(CSV_PATH, sep=";")
    cols = df.columns.astype(str)
    cols = cols.str.replace(r"([a-z0-9])([A-Z])", r"\1_\2", regex=True)
    cols = cols.str.replace(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", regex=True)
    cols = cols.str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_")
    df.columns = cols
    return df.rename(columns=ALIAS_MAP)

def _parse_to_instruction(instruction: Optional[Any], kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if isinstance(instruction, dict):
        return instruction
    if isinstance(instruction, str):
        m = re.search(r"\{.*\}", instruction.strip(), re.S)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                if "instruction" in parsed:
                    inner = parsed["instruction"]
                    if isinstance(inner, dict): return inner
                    if isinstance(inner, str):
                        try: return json.loads(inner)
                        except json.JSONDecodeError: pass
                return parsed
    keys = ("operation", "group_by", "metric", "agg_func", "condition")
    flat = {k: kwargs.get(k) for k in keys if kwargs.get(k) is not None}
    if flat: return flat
    if "instruction" in kwargs and kwargs["instruction"] is not None:
        return _parse_to_instruction(kwargs["instruction"], {})
    return None

def _run_sales_instruction(instr: dict) -> str:
    df = _load_df()
    op = (instr.get("operation") or "").strip().lower()
    if not op: return "Error: missing 'operation' in instruction."

    if op == "filter":
        condition = instr.get("condition")
        if not condition: return "Error: 'filter' requires 'condition'."
        try: res = df.query(condition)
        except Exception as e: return f"Error in filter condition: {e}"
        return res.to_string(index=False) if not res.empty else "No rows matched."

    if op == "aggregate":
        group_by, metric = instr.get("group_by"), instr.get("metric")
        agg = (instr.get("agg_func") or "sum").lower()
        if not group_by or not metric:
            return "Error: 'aggregate' requires 'group_by' and 'metric'."
        if group_by not in df.columns: return f"Error: unknown group_by column '{group_by}'."
        if metric not in df.columns: return f"Error: unknown metric column '{metric}'."
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        group = df.groupby(group_by, dropna=False)[metric]
        try:
            if agg == "sum": result = group.sum()
            elif agg == "mean": result = group.mean()
            elif agg == "count": result = group.count()
            else: return f"Unsupported aggregation: {agg}"
        except Exception as e:
            return f"Error during aggregation: {e}"
        return result.sort_values(ascending=False).to_string()

    if op == "filter_sum":
        condition, metric = instr.get("condition"), instr.get("metric")
        if not condition or not metric:
            return "Error: 'filter_sum' requires 'condition' and 'metric'."
        if metric not in df.columns: return f"Error: unknown metric column '{metric}'."
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        try: value = df.query(condition)[metric].sum()
        except Exception as e: return f"Error in filter_sum: {e}"
        return str(value)

    return f"Unsupported operation: {op}"
