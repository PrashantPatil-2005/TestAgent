"""
Executor Node

This module executes generated Playwright test scripts dynamically.
It captures results, console logs, screenshots, and execution metrics.
"""

import os
import sys
import time
import json
import tempfile
import traceback
from typing import Dict, Any
from pathlib import Path

from ..state import AgentState, ExecutionResult, StepResult


def ensure_directories():
    """Ensure required directories exist for screenshots and videos."""
    Path("screenshots").mkdir(exist_ok=True)
    Path("videos").mkdir(exist_ok=True)


def execute_code_safely(code: str) -> Dict[str, Any]:
    """
    Execute generated Playwright code safely.
    
    The code is written to a temp file and executed in a controlled environment.
    
    Args:
        code: Generated Playwright Python code
        
    Returns:
        Execution results dictionary
    """
    ensure_directories()
    
    # Create a temporary file for the test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Create a namespace for execution
        namespace = {
            '__name__': '__main__',
            '__file__': temp_file,
        }
        
        # Execute the code
        exec(compile(code, temp_file, 'exec'), namespace)
        
        # Call the run_test function
        if 'run_test' in namespace:
            result = namespace['run_test']()
            return result
        else:
            return {
                "success": False,
                "error_message": "run_test function not found in generated code",
                "steps": [],
                "total_time_ms": 0,
                "console_logs": []
            }
    
    except Exception as e:
        return {
            "success": False,
            "error_message": f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            "steps": [],
            "total_time_ms": 0,
            "console_logs": []
        }
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except:
            pass


def save_test_file(code: str, output_dir: str = "playwright_tests") -> str:
    """
    Save generated test to a file for reference.
    
    Args:
        code: Generated test code
        output_dir: Directory to save the test file
        
    Returns:
        Path to saved file
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    timestamp = int(time.time())
    filename = f"generated_test_{timestamp}.py"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write(code)
    
    return filepath


def execute_test(state: AgentState) -> AgentState:
    """
    Execute the generated Playwright test.
    
    This is a LangGraph node function that:
    1. Takes generated_code from state
    2. Executes it in a controlled environment
    3. Returns updated state with execution_result
    
    Args:
        state: Current agent state with generated_code
        
    Returns:
        Updated state with execution_result populated
    """
    code = state["generated_code"]
    
    if not code:
        state["execution_result"] = ExecutionResult(
            success=False,
            steps=[],
            total_time_ms=0,
            console_logs=[],
            error_message="No code to execute"
        )
        print("❌ Execution failed: No code to execute")
        return state
    
    # Check if validation passed
    if not state["validation_result"]["is_valid"]:
        state["execution_result"] = ExecutionResult(
            success=False,
            steps=[],
            total_time_ms=0,
            console_logs=[],
            error_message=f"Code validation failed: {state['validation_result']['error_message']}"
        )
        print("❌ Execution skipped: Validation failed")
        return state
    
    print("🚀 Executing generated test...")
    
    # Save the test file
    test_file_path = save_test_file(code)
    state["test_file_path"] = test_file_path
    print(f"📄 Test saved to: {test_file_path}")
    
    # Execute the test
    start_time = time.time()
    result = execute_code_safely(code)
    total_time = int((time.time() - start_time) * 1000)
    
    # Build execution result
    execution_result = ExecutionResult(
        success=result.get("success", False),
        steps=result.get("steps", []),
        total_time_ms=result.get("total_time_ms", total_time),
        console_logs=result.get("console_logs", []),
        error_message=result.get("error_message")
    )
    
    state["execution_result"] = execution_result
    
    if execution_result["success"]:
        passed_steps = sum(1 for s in execution_result["steps"] if s.get("status") == "pass")
        total_steps = len(execution_result["steps"])
        print(f"✅ Test execution completed: {passed_steps}/{total_steps} steps passed")
    else:
        print(f"❌ Test execution failed: {execution_result['error_message']}")
    
    return state
