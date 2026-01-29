"""
LangGraph Agent Orchestration

This module defines the LangGraph workflow that orchestrates all the nodes
in the AI web testing pipeline. It handles state transitions, conditional
routing, and retry logic.
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from .state import AgentState, create_initial_state
from .nodes import (
    parse_instruction,
    generate_code,
    validate_code,
    execute_test,
    generate_report,
    handle_error
)
from .nodes.validator import is_valid
from .nodes.error_handler import should_retry


def route_after_validation(state: AgentState) -> Literal["execute_test", "handle_error"]:
    """
    Route after validation based on result.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name
    """
    if is_valid(state):
        return "execute_test"
    else:
        return "handle_error"


def route_after_error_handler(state: AgentState) -> Literal["generate_code", "generate_report"]:
    """
    Route after error handling - retry or finalize.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name
    """
    if should_retry(state):
        return "generate_code"
    else:
        return "generate_report"


def route_after_execution(state: AgentState) -> Literal["generate_report", "handle_error"]:
    """
    Route after execution based on success.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name
    """
    if state["execution_result"]["success"]:
        return "generate_report"
    else:
        # Check if we should retry
        if should_retry(state):
            return "handle_error"
        else:
            return "generate_report"


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph workflow for the AI web testing agent.
    
    Workflow:
    1. parse_instruction - Convert NL to actions
    2. generate_code - Create Playwright script
    3. validate_code - Validate the code
    4. execute_test (if valid) or handle_error (if invalid)
    5. generate_report - Create final report
    
    Returns:
        Compiled StateGraph
    """
    # Create the graph with our state type
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("parse_instruction", parse_instruction)
    workflow.add_node("generate_code", generate_code)
    workflow.add_node("validate_code", validate_code)
    workflow.add_node("execute_test", execute_test)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("handle_error", handle_error)
    
    # Set entry point
    workflow.set_entry_point("parse_instruction")
    
    # Add edges
    # parse_instruction -> generate_code
    workflow.add_edge("parse_instruction", "generate_code")
    
    # generate_code -> validate_code
    workflow.add_edge("generate_code", "validate_code")
    
    # validate_code -> execute_test (if valid) or handle_error (if invalid)
    workflow.add_conditional_edges(
        "validate_code",
        route_after_validation,
        {
            "execute_test": "execute_test",
            "handle_error": "handle_error"
        }
    )
    
    # execute_test -> generate_report or handle_error
    workflow.add_conditional_edges(
        "execute_test",
        route_after_execution,
        {
            "generate_report": "generate_report",
            "handle_error": "handle_error"
        }
    )
    
    # handle_error -> generate_code (retry) or generate_report (give up)
    workflow.add_conditional_edges(
        "handle_error",
        route_after_error_handler,
        {
            "generate_code": "generate_code",
            "generate_report": "generate_report"
        }
    )
    
    # generate_report -> END
    workflow.add_edge("generate_report", END)
    
    return workflow


def compile_graph():
    """
    Compile the agent graph for execution.
    
    Returns:
        Compiled graph ready for invocation
    """
    workflow = create_agent_graph()
    return workflow.compile()


def run_agent(instruction: str, base_url: str = "http://localhost:5000") -> AgentState:
    """
    Run the AI web testing agent.
    
    Args:
        instruction: Natural language test instruction
        base_url: Target website base URL
        
    Returns:
        Final AgentState with all results
    """
    print("=" * 60)
    print("  AI WEB TESTING AGENT")
    print("=" * 60)
    print(f"\n📋 Instruction: {instruction}")
    print(f"🌐 Target: {base_url}\n")
    
    # Create initial state
    initial_state = create_initial_state(instruction, base_url)
    
    # Compile and run the graph
    graph = compile_graph()
    
    # Run the workflow
    final_state = graph.invoke(initial_state)
    
    return final_state


# For direct execution
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set")
        print("Please create a .env file with your Google API key:")
        print("GOOGLE_API_KEY=your_key_here")
        exit(1)
    
    # Run a sample test
    test_instruction = """
    Go to the login page, 
    enter 'testuser' as username and 'password123' as password,
    click the sign in button,
    and verify the page shows 'Logged in as'
    """
    
    result = run_agent(test_instruction)
    
    print("\n" + "=" * 60)
    print("  FINAL STATE")
    print("=" * 60)
    print(f"Status: {result['report']['status']}")
    print(f"Passed: {result['report']['passed']}/{result['report']['total_steps']}")
