# sales_ai/crewapp.py
import os
import re
import json
import sys
from typing import Tuple

from crewai import Agent, Task, Crew, Process
from .tools import simple_validator, sales_data_tool
from .summarize import summarize


def make_agents() -> Tuple[Agent, Agent, Agent]:
    """Create the three agents used in the pipeline."""
    validator = Agent(
        role="Validator",
        goal="Turn the user's question into a single valid instruction JSON.",
        backstory="You output only compact JSON for the tool to run.",
        tools=[simple_validator],
        allow_delegation=False,
        verbose=True,  # logs to terminal
    )
    data_analyst = Agent(
        role="Data Analyst",
        goal="CALL the Sales Data Query Tool using the validated instruction and return raw output.",
        backstory="You execute the tool; no extra commentary.",
        tools=[sales_data_tool],
        allow_delegation=False,
        verbose=True,  # logs to terminal
    )
    insights_agent = Agent(
        role="Business Insights Specialist",
        goal="Summarize tool results into a crisp business insight.",
        backstory="You make numbers meaningful.",
        allow_delegation=False,
        verbose=True,  # logs to terminal
    )
    return validator, data_analyst, insights_agent


def create_tasks(question: str, validator: Agent, data_analyst: Agent, insights_agent: Agent):
    """(Optional) One-crew, three-task setup. Not used by answer_question, kept for compatibility."""
    validate = Task(
        description=(
            f"User question: '{question}'.\n"
            "Use Simple Instruction Validator. Return ONLY a compact JSON instruction string for Sales Data Query Tool."
        ),
        expected_output="A single compact JSON object string.",
        agent=validator,
    )
    analysis = Task(
        description=(
            "Take the validator's JSON output and CALL Sales Data Query Tool with it. "
            "Return only the raw tool output."
        ),
        expected_output="Raw tool output containing the relevant data.",
        agent=data_analyst,
        context=[validate],
    )
    reporting = Task(
        description=(
            "Interpret the previous tool result and summarize plainly. "
            "If it’s a series of totals, identify the top item explicitly."
        ),
        expected_output="A clear, concise summary for the user.",
        agent=insights_agent,
        context=[analysis],
    )
    return [validate, analysis, reporting]


def run_offline(question: str):
    """Offline utility: lets you test without an API key."""
    from .core import _run_sales_instruction

    print("⚠️  OPENAI_API_KEY not set. Running OFFLINE.")
    q = question.lower().strip()

    if "which product sold the most" in q:
        instr = {
            "operation": "aggregate",
            "group_by": "product_id",
            "metric": "actual_quantity",
            "agg_func": "sum",
        }
        print(_run_sales_instruction(instr))
        return

    if "which location had the highest sales" in q or "highest sales volume" in q:
        instr = {
            "operation": "aggregate",
            "group_by": "location",
            "metric": "actual_quantity",
            "agg_func": "sum",
        }
        print(_run_sales_instruction(instr))
        return

    print(
        '\nOffline mode accepts direct JSON. Example:\n'
        '{"operation":"aggregate","group_by":"product_id","metric":"actual_quantity","agg_func":"sum"}\n'
    )
    raw = input("JSON instruction:\n> ").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        print('Error: expected a JSON like {"operation":...}.')
        return
    instr = json.loads(m.group(0))
    print(_run_sales_instruction(instr))


def answer_question(question: str) -> dict:
    """
    Run the existing three agents step-by-step so we can capture intermediates
    and still get real CrewAI logs in the terminal (verbose=True).
    Returns a dict used by the API/UI: {mode, validator, tool_output, insights}
    """
    print("\n=== Sales AI Pipeline ===", file=sys.stdout)
    print(f"[INPUT] {question}", file=sys.stdout)

    # OFFLINE path (no API key): deterministic tools + heuristic summary
    if not os.getenv("OPENAI_API_KEY"):
        validator_out = simple_validator.run(question=question, instruction=None)
        print("[VALIDATOR]", validator_out, file=sys.stdout)

        data_out = sales_data_tool.run(instruction=validator_out)
        preview = (data_out[:500] + ("..." if len(data_out) > 500 else ""))
        print("[DATA TOOL] (first 500 chars)\n", preview, file=sys.stdout)

        insights_out = summarize(data_out)
        print("[INSIGHTS]", insights_out, file=sys.stdout)
        print("=== End ===\n", file=sys.stdout)

        return {
            "mode": "offline",
            "validator": validator_out,
            "tool_output": data_out,
            "insights": insights_out,
        }

    # ONLINE path: use your three agents so CrewAI logs appear in terminal
    validator, data_analyst, insights_agent = make_agents()

    # 1) Validator agent -> compact JSON
    validate_task = Task(
        description=(
            f"User question: '{question}'.\n"
            "Use Simple Instruction Validator. Return ONLY a compact JSON instruction string."
        ),
        expected_output="A single compact JSON object string.",
        agent=validator,
    )
    crew1 = Crew(
        agents=[validator],
        tasks=[validate_task],
        process=Process.sequential,
        verbose=True,   # Crew/agent logs printed to terminal
    )
    validator_out = str(crew1.kickoff()).strip()
    print("[VALIDATOR RESULT]", validator_out, file=sys.stdout)

    # 2) Data Analyst agent -> raw tool output
    analysis_task = Task(
        description=(
            "Take the validator's JSON instruction below and CALL Sales Data Query Tool with it. "
            "Return only the raw tool output.\n\n"
            f"INSTRUCTION:\n{validator_out}"
        ),
        expected_output="Raw tool output containing the relevant data.",
        agent=data_analyst,
    )
    crew2 = Crew(
        agents=[data_analyst],
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True,
    )
    data_out = str(crew2.kickoff())
    preview = (data_out[:500] + ("..." if len(data_out) > 500 else ""))
    print("[DATA TOOL RESULT] (first 500 chars)\n", preview, file=sys.stdout)

    # 3) Business Insights Specialist -> long business summary
    reporting_task = Task(
        description=(
            "Interpret the previous tool result and summarize plainly for a business user. "
            "If it's a ranking or totals, identify the top item explicitly and include numbers. "
            "Aim for 2–5 concise bullets or a short paragraph.\n\n"
            f"TOOL RESULT:\n{data_out}"
        ),
        expected_output="A clear summary (2–5 bullets or short paragraph).",
        agent=insights_agent,
    )
    crew3 = Crew(
        agents=[insights_agent],
        tasks=[reporting_task],
        process=Process.sequential,
        verbose=True,
    )
    insights_out = str(crew3.kickoff())
    print("[INSIGHTS RESULT]", insights_out, file=sys.stdout)
    print("=== End ===\n", file=sys.stdout)

    return {
        "mode": "online",
        "validator": validator_out,
        "tool_output": data_out,
        "insights": insights_out,
    }


def main():
    """CLI entrypoint."""
    print("🤖 CrewAI Sales Data Analyzer")
    question = input("Ask your question:\n> ").strip()
    if not question:
        print("No question provided. Exiting.")
        return

    res = answer_question(question)

    print("\n--- Intermediates ---")
    print("[VALIDATOR]", res["validator"])
    tool_preview = res["tool_output"][:500] + ("..." if len(res["tool_output"]) > 500 else "")
    print("[DATA TOOL] (first 500 chars)\n", tool_preview)

    print("\n--- Insights ---")
    print(res["insights"])

