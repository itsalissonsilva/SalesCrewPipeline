# sales_ai/tools.py
import json
from typing import Any, Optional
from crewai.tools import tool
from .core import _load_df, _parse_to_instruction, _run_sales_instruction

@tool("Simple Instruction Validator")
def simple_validator(question: Optional[str] = None, instruction: Any = None) -> str:
    """
    Build or pass through a compact JSON instruction for querying sales.csv.

    Args:
        question: Natural-language question (used to infer defaults if no instruction provided).
        instruction: A dict or JSON string like:
            {"operation":"aggregate","group_by":"product_id","metric":"actual_quantity","agg_func":"sum"}

    Returns:
        A compact JSON string representing the instruction, or an error string.
    """
    try:
        df = _load_df()
        cols = set(df.columns)
    except Exception as e:
        return f"Error: cannot load CSV -> {e}"

    parsed = _parse_to_instruction(instruction, {})
    if isinstance(parsed, dict) and parsed.get("operation"):
        return json.dumps(parsed, separators=(",", ":"))

    q = (question or "").lower()
    group_by = "location" if ("location" in q and "location" in cols) else ("product_id" if "product_id" in cols else "product_id")

    if any(k in q for k in ["revenue", "price", "amount", "$"]):
        metric = "actual_price" if "actual_price" in cols else "actual_price"
    else:
        metric = "actual_quantity" if "actual_quantity" in cols else "actual_quantity"

    instr = {"operation": "aggregate", "group_by": group_by, "metric": metric, "agg_func": "sum"}
    return json.dumps(instr, separators=(",", ":"))

@tool("Sales Data Query Tool")
def sales_data_tool(instruction: Any = None, **kwargs) -> str:
    """
    Execute a JSON instruction against sales.csv.

    Supported operations:
      - filter:
        {"operation":"filter","condition":"location == 'New York'"}
      - aggregate:
        {"operation":"aggregate","group_by":"product_id","metric":"actual_quantity","agg_func":"sum"}
      - filter_sum:
        {"operation":"filter_sum","condition":"date >= '2023-01-01'","metric":"actual_price"}

    Args:
        instruction: dict or JSON string. You can also pass flat kwargs like
                     operation/group_by/metric/agg_func/condition.

    Returns:
        Raw string of tool output (table/series/number) or an error string.
    """
    try:
        instr = _parse_to_instruction(instruction, kwargs)
        if not isinstance(instr, dict):
            return 'Error: expected JSON like {"operation": "...", ...}.'
        return _run_sales_instruction(instr)
    except Exception as e:
        return f"Error executing instruction: {e}"

