# src/orchestrator/graph.py
# Graph construction with 3-agent architecture

from langgraph.graph import StateGraph, END
from .state import State
from .routing import should_continue
from src.agents.auditor_agent import auditor_agent
from src.agents.fixer_agent import fixer_agent
from src.agents.judge_agent import judge_agent


def _count_auditor_pass(state: State) -> State:
    """
    Increments iteration_count exactly once per loop, at the point the graph
    re-enters AUDITOR — rather than trusting auditor_agent, fixer_agent, or
    judge_agent to remember to do it themselves. A forgotten increment
    anywhere in agent code would otherwise defeat should_continue's
    max_iterations cutoff and turn a failing refactor into an infinite loop.
    """
    current = state.get("iteration_count", 0)
    return {**state, "iteration_count": current + 1}


def create_refactoring_graph():
    """
    Build the LangGraph workflow with 3 specialized agents:
    
    1. AUDITOR: Reads code, runs static analysis, produces refactoring plan
    2. FIXER: Reads plan, modifies code to correct errors
    3. JUDGE: Executes unit tests
       - If unsuccessful: Sends code back to AUDITOR with error logs (Self-Healing Loop)
       - If successful: Confirms mission end
    
    Workflow:
    COUNT → AUDITOR → FIXER → JUDGE → (decision) 
                                  ↓
                        if is_fixed=True → END (SUCCESS)
                        if iteration >= max → END (FAILURE)
                        else → COUNT → AUDITOR (LOOP)
    
    Returns:
        Compiled graph ready for execution
    """
    for agent_name, agent_fn in [
        ("auditor_agent", auditor_agent),
        ("fixer_agent", fixer_agent),
        ("judge_agent", judge_agent),
    ]:
        if not callable(agent_fn):
            raise TypeError(
                f"{agent_name} is not callable (got {agent_fn!r}) — "
                f"check its import, this graph cannot be built without it."
            )

    graph_builder = StateGraph(State)

    # ===================================================================
    # REGISTER NODES
    # ===================================================================

    # 0. COUNT: bumps iteration_count before every AUDITOR pass, so the loop
    #    guard in should_continue is enforced by the graph itself, not by
    #    agent code remembering to update shared state correctly.
    graph_builder.add_node("count", _count_auditor_pass)

    graph_builder.add_node("auditor", auditor_agent)
    graph_builder.add_node("fixer", fixer_agent)
    graph_builder.add_node("judge", judge_agent)

    expected_nodes = {"count", "auditor", "fixer", "judge"}
    registered_nodes = set(graph_builder.nodes.keys())
    missing = expected_nodes - registered_nodes
    if missing:
        raise RuntimeError(f"Graph nodes failed to register: {missing}")

    # ===================================================================
    # ENTRY POINT
    # ===================================================================
    graph_builder.set_entry_point("count")

    # ===================================================================
    # REGISTER EDGES
    # ===================================================================
    graph_builder.add_edge("count", "auditor")
    graph_builder.add_edge("auditor", "fixer")
    graph_builder.add_edge("fixer", "judge")

    graph_builder.add_conditional_edges(
        "judge",
        should_continue,
        {
            "auditor": "count",  # loop back through COUNT, not straight to auditor
            "end": END,
        },
    )

    return graph_builder.compile()