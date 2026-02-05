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
    # Initialize the graph
    builder = StateGraph(State)
    
    # ===================================================================
    # ADD NODES
    # ===================================================================
    
    # 1. AUDITOR: Static analysis + refactoring plan
    builder.add_node("auditor", auditor_agent)
    
    # 2. FIXER: Applies fixes based on plan
    builder.add_node("fixer", fixer_agent)
    
    # 3. JUDGE: Validates with unit tests
    builder.add_node("judge", judge_agent)
    
    # ===================================================================
    # SET ENTRY POINT
    # ===================================================================
    builder.set_entry_point("auditor")
    
    # ===================================================================
    # ADD EDGES
    # ===================================================================
    
    # Linear flow: Auditor → Fixer → Judge
    builder.add_edge("auditor", "fixer")
    builder.add_edge("fixer", "judge")
    
    # Conditional edge from Judge (routing.should_continue decides):
    # - "end" → END (if is_fixed=True OR iteration_count >= max_iterations)
    # - "auditor" → Loop back to Auditor (if more iterations available)
    builder.add_conditional_edges(
        "judge",              # Source node
        should_continue,      # Routing function
        {
            "auditor": "auditor",  # Loop back for re-audit with test failures
            "end": END             # Terminate if successful or max iterations
        }
    )
    
    # Compile and return the graph
    return builder.compile()