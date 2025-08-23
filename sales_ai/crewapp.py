import os, re, json
from crewai import Agent, Task, Crew, Process
from .tools import simple_validator, sales_data_tool

def make_agents():
    validator = Agent(
        role="Validator",
        goal="Turn the user's question into a single valid instruction JSON.",
        backstory="You output only compact JSON for the tool to run.",
        tools=[simple_validator],
        allow_delegation=False,
        verbose=True,
    )
    data_analyst = Agent(
        role="Data Analyst",
        goal="CALL the Sales Data Query Tool using the validated instruction and return raw output.",
        backstory="You execute the tool; no extra commentary.",
        tools=[sales_data_tool],
        allow_delegation=False,
        verbose=True,
    )
    insights_agent = Agent(
        role="Business Insights Specialist",
        goal="Summarize tool results into a crisp business insight.",
        backstory="You make numbers meaningful.",
        allow_delegation=False,
        verbose=True,
    )
    return validator, data_analyst, insights_agent

def create_tasks(question: str, validator: Agent, data_analyst: Agent, insights_agent: Agent):
    validate = Task(
        description=(
            f"User question: '{question}'.\n"
            "Use Simple Instruction Validator. Return ONLY a compact JSON instruction string for Sales Data Query Tool."
        ),
        expected_output="A single compact JSON object string.",
        agent=validator,
    )
    analysis = Task(
        description="Take the validator's JSON output and CALL Sales Data Query Tool with it. Return only the raw tool output.",
        expected_output="Raw tool output containing the relevant data.",
        agent=data_analyst,
        context=[validate],
    )
    reporting = Task(
        description="Interpret the previous tool result and summarize plainly. If it’s a series of totals, identify the top item explicitly.",
        expected_output="A clear, concise summary for the user.",
        agent=insights_agent,
        context=[analysis],
    )
    return [validate, analysis, reporting]

def run_offline(question: str):
    from .core import _run_sales_instruction
    print("⚠️  OPENAI_API_KEY not set. Running OFFLINE.")
    q = question.lower().strip()
    if "which product sold the most" in q:
        instr = {"operation":"aggregate","group_by":"product_id","metric":"actual_quantity","agg_func":"sum"}
        print(_run_sales_instruction(instr)); return
    if "which location had the highest sales" in q or "highest sales volume" in q:
        instr = {"operation":"aggregate","group_by":"location","metric":"actual_quantity","agg_func":"sum"}
        print(_run_sales_instruction(instr)); return
    print('\nOffline mode accepts direct JSON. Example:\n{"operation":"aggregate","group_by":"product_id","metric":"actual_quantity","agg_func":"sum"}\n')
    raw = input("JSON instruction:\n> ").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m: print('Error: expected a JSON like {"operation":...}.'); return
    instr = json.loads(m.group(0))
    print(_run_sales_instruction(instr))

def main():
    print("🤖 CrewAI Sales Data Analyzer")
    online = bool(os.getenv("OPENAI_API_KEY"))

    # Create agents once if we're online; reuse across questions
    if online:
        validator, data_analyst, insights_agent = make_agents()

    while True:
        try:
            question = input("\nAsk a question about the dataset:\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not question or question.lower() in {"q", "quit", "exit"}:
            print("Bye!")
            break

        try:
            if not online:
                run_offline(question)
            else:
                tasks = create_tasks(question, validator, data_analyst, insights_agent)
                crew = Crew(
                    agents=[validator, data_analyst, insights_agent],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True,
                )
                result = crew.kickoff()
                print("\n--- Final Answer ---")
                print(result)
        except Exception as e:
            print(f"\nError: {e}")
