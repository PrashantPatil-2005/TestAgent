"""
State Management for AI Web Testing Agent

This module defines the shared state model used across all LangGraph nodes.
The state flows through the entire pipeline and accumulates results from each step.
"""

from typing import TypedDict, List, Dict, Any, Optional


class TestAction(TypedDict):
    """Represents a single browser action parsed from natural language."""
    action: str  # Type of action: goto, click, fill, wait, assert_url, assert_visible, assert_text
    target: Optional[str]  # URL path or selector
    selector: Optional[str]  # CSS selector for the element
    value: Optional[str]  # Value for fill actions or assertions


class ValidationResult(TypedDict):
    """Result of code validation."""
    is_valid: bool
    error_message: Optional[str]
    error_line: Optional[int]


class StepResult(TypedDict):
    """Result of a single test step execution."""
    step_number: int
    action: str
    selector: Optional[str]
    status: str  # "pass" or "fail"
    error: Optional[str]
    time_ms: int
    screenshot: Optional[str]


class ExecutionResult(TypedDict):
    """Result of test execution."""
    success: bool
    steps: List[StepResult]
    total_time_ms: int
    console_logs: List[str]
    error_message: Optional[str]


class TestReport(TypedDict):
    """Final test report structure."""
    status: str  # "PASSED" or "FAILED"
    total_steps: int
    passed: int
    failed: int
    execution_time_ms: int
    steps: List[StepResult]
    failure_reason: Optional[str]
    screenshots: List[str]
    human_readable: str


class AgentState(TypedDict):
    """
    Shared state model for the LangGraph agent.
    
    This state is passed through all nodes in the pipeline:
    parse_instruction -> generate_code -> validate_code -> execute_test -> report
    
    Each node reads from and writes to this state, building up the complete
    test execution context.
    """
    # Input
    instruction: str  # Original natural language test instruction
    base_url: str  # Target website base URL (e.g., "http://localhost:5000")
    
    # Parsed data
    parsed_actions: List[TestAction]  # Structured actions from instruction
    
    # Generated code
    generated_code: str  # Playwright Python script
    test_file_path: str  # Path where generated test is saved
    
    # Validation
    validation_result: ValidationResult  # Code validation outcome
    
    # Execution
    execution_result: ExecutionResult  # Test execution results
    
    # Reporting
    report: TestReport  # Final structured report
    
    # Error handling
    errors: List[str]  # List of errors encountered
    retry_count: int  # Number of retries attempted
    max_retries: int  # Maximum retries allowed


def create_initial_state(instruction: str, base_url: str) -> AgentState:
    """
    Create an initial state for a new test run.
    
    Args:
        instruction: Natural language test instruction
        base_url: Target website URL
        
    Returns:
        AgentState: Initialized state ready for pipeline execution
    """
    return AgentState(
        instruction=instruction,
        base_url=base_url,
        parsed_actions=[],
        generated_code="",
        test_file_path="",
        validation_result={"is_valid": False, "error_message": None, "error_line": None},
        execution_result={
            "success": False,
            "steps": [],
            "total_time_ms": 0,
            "console_logs": [],
            "error_message": None
        },
        report={
            "status": "PENDING",
            "total_steps": 0,
            "passed": 0,
            "failed": 0,
            "execution_time_ms": 0,
            "steps": [],
            "failure_reason": None,
            "screenshots": [],
            "human_readable": ""
        },
        errors=[],
        retry_count=0,
        max_retries=3
    )
