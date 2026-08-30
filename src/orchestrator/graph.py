# src/orchestrator/graph.py
# Graph construction with 3-agent architecture

from langgraph.graph import StateGraph, END
from .state import State
from .routing import should_continue
from src.agents.auditor_agent import auditor_agent
from src.agents.fixer_agent import fixer_agent
from src.agents.judge_agent import judge_agent


def create_refactoring_graph():
    """
    Build the LangGraph workflow with 3 specialized agents:
    
    1. AUDITOR: Reads code, runs static analysis, produces refactoring plan
    2. FIXER: Reads plan, modifies code to correct errors
    3. JUDGE: Executes unit tests
       - If unsuccessful: Sends code back to AUDITOR with error logs (Self-Healing Loop)
       - If successful: Confirms mission end
    
    Workflow:
    AUDITOR → FIXER → JUDGE → (decision) 
                                  ↓
                        if is_fixed=True → END (SUCCESS)
                        if iteration >= max → END (FAILURE)
                        else → AUDITOR (LOOP)
    
    Returns:
        Compiled graph ready for execution
    """
    # Fail fast with a clear error rather than letting a broken import
    # silently produce a graph node that isn't callable — LangGraph's own
    # error for that surfaces much later and doesn't name which agent broke.
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

    # Set up the state graph builder
    graph_builder = StateGraph(State)
    
    # ===================================================================
    # REGISTER NODES
    # ===================================================================
    
    # 1. AUDITOR: Static analysis + refactoring plan
    graph_builder.add_node("auditor", auditor_agent)
    
    # 2. FIXER: Applies fixes based on plan
    graph_builder.add_node("fixer", fixer_agent)
    
    # 3. JUDGE: Validates with unit tests
    graph_builder.add_node("judge", judge_agent)

    # Verify all three nodes actually registered before wiring edges —
    # catches a silent no-op add_node call rather than letting a missing
    # node surface later as a confusing "node not found" error from
    # add_conditional_edges or compile() instead.
    expected_nodes = {"auditor", "fixer", "judge"}
    registered_nodes = set(graph_builder.nodes.keys())
    missing = expected_nodes - registered_nodes
    if missing:
        raise RuntimeError(f"Graph nodes failed to register: {missing}")
    
    # ===================================================================
    # ENTRY POINT
    # ===================================================================
    graph_builder.set_entry_point("auditor")
    
    # ===================================================================
    # REGISTER EDGES
    # ===================================================================
    
    # Linear flow: Auditor → Fixer → Judge
    graph_builder.add_edge("auditor", "fixer")
    graph_builder.add_edge("fixer", "judge")
    
    graph_builder.add_conditional_edges(
        "judge",              # Source node
        should_continue,      # Routing function
        {
            "auditor": "auditor",  # Loop back for re-audit with test failures
            "end": END             # Terminate if successful or max iterations
        }
    )
    
    # Compile and return the graph
    return graph_builder.compile()