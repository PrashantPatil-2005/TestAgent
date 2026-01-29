"""
Error Handler Node

This module handles errors and implements retry logic for the testing pipeline.
It can modify prompts and suggest alternate selectors when failures occur.
"""

from typing import Dict, List, Optional
import re

from ..state import AgentState


# Selector alternatives for common element types
SELECTOR_ALTERNATIVES = {
    "button": [
        "button[type='submit']",
        "button",
        "input[type='submit']",
        "[role='button']"
    ],
    "username": [
        "input[name='username']",
        "input[id='username']",
        "input[type='text']",
        "#username",
        "[placeholder*='user']"
    ],
    "password": [
        "input[name='password']",
        "input[id='password']",
        "input[type='password']",
        "#password",
        "[placeholder*='pass']"
    ],
    "email": [
        "input[name='email']",
        "input[id='email']",
        "input[type='email']",
        "#email",
        "[placeholder*='email']"
    ],
    "search": [
        "input[name='search']",
        "input[name='query']",
        "input[id='search']",
        "input[type='search']",
        "#search",
        "[placeholder*='search']"
    ],
    "login": [
        "button:has-text('Login')",
        "button:has-text('Sign In')",
        "button:has-text('Log In')",
        "input[type='submit']",
        "button[type='submit']"
    ]
}


def extract_failed_selector(error_message: str) -> Optional[str]:
    """
    Extract the failing selector from an error message.
    
    Args:
        error_message: Error message from execution
        
    Returns:
        The failing selector if found, None otherwise
    """
    # Common patterns for selector errors
    patterns = [
        r'Selector "([^"]+)" not found',
        r'locator\.click: Timeout.*selector="([^"]+)"',
        r'waiting for selector "([^"]+)"',
        r'Error: ([^\s]+) not found'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            return match.group(1)
    
    return None


def suggest_alternative_selectors(failed_selector: str) -> List[str]:
    """
    Suggest alternative selectors based on the failed one.
    
    Args:
        failed_selector: The selector that failed
        
    Returns:
        List of alternative selectors to try
    """
    alternatives = []
    
    # Check for keyword matches in the selector
    selector_lower = failed_selector.lower()
    
    for keyword, selectors in SELECTOR_ALTERNATIVES.items():
        if keyword in selector_lower:
            alternatives.extend(selectors)
    
    # Remove the original failed selector
    alternatives = [s for s in alternatives if s != failed_selector]
    
    # Add generic alternatives
    if "button" in selector_lower or "submit" in selector_lower:
        alternatives.extend([
            "button:first-of-type",
            "form button",
            "[type='submit']"
        ])
    elif "input" in selector_lower:
        # Try to extract the field name and suggest alternatives
        name_match = re.search(r"name='([^']+)'", failed_selector)
        if name_match:
            field_name = name_match.group(1)
            alternatives.extend([
                f"#{field_name}",
                f"input[id='{field_name}']",
                f"[placeholder*='{field_name}']"
            ])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_alternatives = []
    for alt in alternatives:
        if alt not in seen:
            seen.add(alt)
            unique_alternatives.append(alt)
    
    return unique_alternatives[:5]  # Return top 5 alternatives


def modify_actions_with_alternatives(state: AgentState, failed_selector: str, alternatives: List[str]) -> bool:
    """
    Modify parsed actions to use alternative selectors.
    
    Args:
        state: Current agent state
        failed_selector: The selector that failed
        alternatives: List of alternative selectors
        
    Returns:
        True if modifications were made, False otherwise
    """
    if not alternatives:
        return False
    
    modified = False
    new_selector = alternatives[0]  # Use the first alternative
    
    for action in state["parsed_actions"]:
        if action.get("selector") == failed_selector:
            action["selector"] = new_selector
            modified = True
    
    if modified:
        print(f"🔄 Replaced selector '{failed_selector}' with '{new_selector}'")
    
    return modified


def handle_error(state: AgentState) -> AgentState:
    """
    Handle errors and implement retry logic.
    
    This is a LangGraph node function that:
    1. Analyzes errors from validation or execution
    2. Attempts to fix issues (modify selectors, adjust actions)
    3. Increments retry count
    4. Returns updated state
    
    Args:
        state: Current agent state with errors
        
    Returns:
        Updated state with retry information
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    # Check if we've exceeded retries
    if retry_count >= max_retries:
        print(f"❌ Maximum retries ({max_retries}) exceeded")
        state["errors"].append(f"Maximum retries ({max_retries}) exceeded")
        return state
    
    # Increment retry count
    state["retry_count"] = retry_count + 1
    print(f"🔄 Retry attempt {state['retry_count']}/{max_retries}")
    
    # Analyze the error
    error_source = None
    error_message = None
    
    # Check validation errors
    if not state["validation_result"]["is_valid"]:
        error_source = "validation"
        error_message = state["validation_result"]["error_message"]
    
    # Check execution errors
    elif state["execution_result"] and not state["execution_result"]["success"]:
        error_source = "execution"
        error_message = state["execution_result"]["error_message"]
        
        # Check for step-level errors
        for step in state["execution_result"].get("steps", []):
            if step.get("status") == "fail" and step.get("error"):
                error_message = step["error"]
                break
    
    if error_message:
        print(f"📋 Error source: {error_source}")
        print(f"📋 Error: {error_message[:200]}...")
        
        # Try to extract and fix selector issues
        failed_selector = extract_failed_selector(error_message)
        
        if failed_selector:
            print(f"🔍 Failed selector: {failed_selector}")
            alternatives = suggest_alternative_selectors(failed_selector)
            
            if alternatives:
                print(f"💡 Suggested alternatives: {alternatives}")
                
                if modify_actions_with_alternatives(state, failed_selector, alternatives):
                    # Clear previous generated code to force regeneration
                    state["generated_code"] = ""
                    state["validation_result"]["is_valid"] = False
                    print("✅ Actions modified, will regenerate code")
    
    return state


def should_retry(state: AgentState) -> bool:
    """
    Determine if the pipeline should retry.
    
    Used as a conditional edge function in LangGraph.
    
    Args:
        state: Current agent state
        
    Returns:
        True if retry should be attempted, False otherwise
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    # Don't retry if we've exceeded limit
    if retry_count >= max_retries:
        return False
    
    # Retry if validation failed
    if not state["validation_result"]["is_valid"]:
        return True
    
    # Retry if execution failed and we have room
    if state["execution_result"] and not state["execution_result"]["success"]:
        return True
    
    return False
