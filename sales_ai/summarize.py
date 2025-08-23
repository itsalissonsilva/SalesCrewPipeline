# sales_ai/summarize.py
def summarize(tool_output: str) -> str:
    """
    Very small heuristic summarizer that:
    - if it's a Pandas Series string, picks top item
    - otherwise returns the first ~500 chars as a concise blurb
    """
    txt = (tool_output or "").strip()
    if not txt:
        return "No result."

    # Detect a Series-like output (two columns, value sorted desc)
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    if len(lines) >= 1 and " " not in lines[0].strip() and ":" not in lines[0]:
        # Try to parse "key   value" style
        try:
            pairs = []
            for ln in lines:
                parts = [p for p in ln.split() if p.strip()]
                if len(parts) >= 2:
                    key = " ".join(parts[:-1])
                    val = parts[-1]
                    pairs.append((key, float(val.replace(",",""))))
            if pairs:
                top_key, top_val = pairs[0]
                return f"Top item: {top_key} with {top_val:.2f}."
        except Exception:
            pass

    # Fallback: blurb
    return (txt[:500] + ("…" if len(txt) > 500 else ""))
