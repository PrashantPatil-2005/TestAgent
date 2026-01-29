"""
Validator Node

This module validates generated Playwright code before execution.
It checks for syntax errors, required imports, and proper structure.
"""

import ast
import re
from typing import Tuple

from ..state import AgentState, ValidationResult


def check_syntax(code: str) -> Tuple[bool, str, int]:
    """
    Check Python syntax of generated code.
    
    Args:
        code: Python code string
        
    Returns:
        Tuple of (is_valid, error_message, error_line)
    """
    try:
        ast.parse(code)
        return True, "", 0
    except SyntaxError as e:
        return False, f"Syntax error: {e.msg}", e.lineno or 0


def check_required_imports(code: str) -> Tuple[bool, str]:
    """
    Check that all required imports are present.
    
    Args:
        code: Python code string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_imports = [
        "playwright",
        "sync_playwright"
    ]
    
    for imp in required_imports:
        if imp not in code:
            return False, f"Missing required import: {imp}"
    
    return True, ""


def check_function_structure(code: str) -> Tuple[bool, str]:
    """
    Check that the generated code has proper function structure.
    
    Args:
        code: Python code string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for run_test function
    if "def run_test" not in code:
        return False, "Missing run_test function"
    
    # Check for browser launch
    if "launch(" not in code:
        return False, "Missing browser launch"
    
    # Check for browser close
    if "close()" not in code:
        return False, "Missing browser close"
    
    return True, ""


def check_selectors(code: str) -> Tuple[bool, str]:
    """
    Basic check for potentially problematic selectors.
    
    Args:
        code: Python code string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for empty selectors
    if 'page.click("")' in code or 'page.fill("",':
        return False, "Empty selector detected"
    
    # Check for unescaped quotes in selectors
    selector_pattern = r'page\.(click|fill|wait_for_selector)\("([^"]*)"\)'
    matches = re.findall(selector_pattern, code)
    
    for match in matches:
        selector = match[1]
        if selector.count('"') > 0:
            return False, f"Unescaped quotes in selector: {selector}"
    
    return True, ""


def validate_code(state: AgentState) -> AgentState:
    """
    Validate generated Playwright code.
    
    This is a LangGraph node function that:
    1. Takes generated_code from state
    2. Performs syntax and structural validation
    3. Returns updated state with validation_result
    
    Args:
        state: Current agent state with generated_code
        
    Returns:
        Updated state with validation_result populated
    """
    code = state["generated_code"]
    
    if not code:
        state["validation_result"] = ValidationResult(
            is_valid=False,
            error_message="No code to validate",
            error_line=0
        )
        print("❌ Validation failed: No code to validate")
        return state
    
    # Run all validation checks
    validations = [
        ("Syntax", check_syntax(code)),
        ("Imports", check_required_imports(code)),
        ("Structure", check_function_structure(code)),
        ("Selectors", check_selectors(code))
    ]
    
    for check_name, result in validations:
        if isinstance(result, tuple) and len(result) == 3:
            is_valid, error_msg, error_line = result
        else:
            is_valid, error_msg = result
            error_line = 0
        
        if not is_valid:
            state["validation_result"] = ValidationResult(
                is_valid=False,
                error_message=f"{check_name} check failed: {error_msg}",
                error_line=error_line
            )
            print(f"❌ Validation failed: {check_name} - {error_msg}")
            return state
    
    # All checks passed
    state["validation_result"] = ValidationResult(
        is_valid=True,
        error_message=None,
        error_line=None
    )
    
    print("✅ Code validation passed")
    return state


def is_valid(state: AgentState) -> bool:
    """
    Check if code validation passed.
    
    Used as a conditional edge function in LangGraph.
    
    Args:
        state: Current agent state
        
    Returns:
        True if validation passed, False otherwise
    """
    return state["validation_result"]["is_valid"]
