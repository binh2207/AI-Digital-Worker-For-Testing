"""
LangGraph workflow:
fetch_tickets → test_designer → test_executor → test_automator → test_reporter
All AI tasks are handled by Claude Code CLI subprocesses.
"""
from langgraph.graph import StateGraph, END
from state import WorkflowState
from agents.test_designer import build_test_designer_node
from agents.test_executor import build_test_executor_node
from agents.test_automator import build_test_automator_node
from agents.test_healer import build_test_healer_node
from agents.test_reporter import build_test_reporter_node
from tools.jira_client import get_review_tickets
from tools.slack_client import notify_progress


def _fetch_jira_tickets(state: WorkflowState) -> WorkflowState:
    try:
        tickets = get_review_tickets()
        return {**state, "jira_tickets": tickets, "test_cases": {}, "test_results": {}, "action_logs": {}, "automation_scripts": {}, "github_prs": {}, "test_summary": {}}
    except Exception as exc:
        return {**state, "jira_tickets": [], "error": str(exc)}


def _should_continue(state: WorkflowState) -> str:
    if state.get("error") or not state.get("jira_tickets"):
        return "end"
    return "continue"


def _with_progress(node_fn, step: str, label: str):
    """Wrap a node to post a Slack progress message before it runs."""
    def wrapped(state: WorkflowState) -> WorkflowState:
        channel = state.get("slack_channel")
        thread_ts = state.get("slack_thread_ts")
        tickets = state.get("jira_tickets", [])
        ticket_ids = ", ".join(t["id"] for t in tickets) if tickets else "—"
        if channel:
            notify_progress(
                channel=channel,
                text=f"{step} *{label}*\nTickets: `{ticket_ids}`",
                thread_ts=thread_ts,
            )
        return node_fn(state)
    return wrapped


def build_graph():
    graph = StateGraph(WorkflowState)

    graph.add_node("fetch_tickets", _fetch_jira_tickets)
    graph.add_node("test_designer",  _with_progress(build_test_designer_node(),  ":pencil:",        "Test Designer — generating test cases"))
    graph.add_node("test_executor",  _with_progress(build_test_executor_node(),  ":globe_with_meridians:", "Test Executor — running live browser tests"))
    graph.add_node("test_automator", _with_progress(build_test_automator_node(), ":robot_face:",    "Test Automator — generating automation scripts"))
    graph.add_node("test_healer",    _with_progress(build_test_healer_node(),    ":stethoscope:",   "Self-Healer — validating and fixing scripts"))
    graph.add_node("test_reporter",  _with_progress(build_test_reporter_node(),  ":bar_chart:",     "Test Reporter — compiling results"))

    graph.set_entry_point("fetch_tickets")

    graph.add_conditional_edges(
        "fetch_tickets",
        _should_continue,
        {"continue": "test_designer", "end": END},
    )
    graph.add_edge("test_designer",  "test_executor")
    graph.add_edge("test_executor",  "test_automator")
    graph.add_edge("test_automator", "test_healer")
    graph.add_edge("test_healer",    "test_reporter")
    graph.add_edge("test_reporter",  END)

    return graph.compile()


workflow = build_graph()
