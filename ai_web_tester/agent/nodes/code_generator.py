"""
Code Generator Node

This module converts parsed browser actions into executable Playwright Python scripts.
It generates clean, runnable test code with proper error handling and logging.
"""

import os
from typing import List
from datetime import datetime

from ..state import AgentState, TestAction


# Template for generated Playwright test script
PLAYWRIGHT_TEMPLATE = '''"""
Auto-generated Playwright Test Script
Generated: {timestamp}
Instruction: {instruction}
"""

import time
from playwright.sync_api import sync_playwright, expect


def run_test():
    """Execute the generated test case."""
    results = {{
        "steps": [],
        "console_logs": [],
        "success": True,
        "error_message": None
    }}
    
    start_time = time.time()
    
    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={{"width": 1280, "height": 720}},
            record_video_dir="videos/" if {record_video} else None
        )
        page = context.new_page()
        
        # Capture console logs
        page.on("console", lambda msg: results["console_logs"].append(f"[{{msg.type}}] {{msg.text}}"))
        
        try:
{test_steps}
        except Exception as e:
            results["success"] = False
            results["error_message"] = str(e)
            # Take screenshot on failure
            try:
                page.screenshot(path="screenshots/error_{{int(time.time())}}.png")
                results["steps"][-1]["screenshot"] = f"screenshots/error_{{int(time.time())}}.png"
            except:
                pass
        finally:
            context.close()
            browser.close()
    
    results["total_time_ms"] = int((time.time() - start_time) * 1000)
    return results


if __name__ == "__main__":
    import json
    result = run_test()
    print(json.dumps(result, indent=2))
'''


def generate_step_code(action: TestAction, step_number: int, base_url: str) -> str:
    """
    Generate Playwright code for a single action.
    
    Args:
        action: The action to generate code for
        step_number: Step number for tracking
        base_url: Base URL for the website
        
    Returns:
        Python code string for the action
    """
    action_type = action["action"]
    selector = action.get("selector", "")
    value = action.get("value", "")
    target = action.get("target", "")
    
    # Escape quotes in values
    if selector:
        selector = selector.replace('"', '\\"')
    if value:
        value = value.replace('"', '\\"')
    
    code_lines = []
    
    # Add step tracking
    code_lines.append(f'            # Step {step_number}: {action_type}')
    code_lines.append(f'            step_start = time.time()')
    code_lines.append(f'            step_result = {{"step_number": {step_number}, "action": "{action_type}", "selector": "{selector}", "status": "pass", "error": None, "time_ms": 0, "screenshot": None}}')
    code_lines.append(f'            try:')
    
    # Generate action-specific code
    if action_type == "goto":
        url_path = target or value or "/"
        if not url_path.startswith("http"):
            url_path = f'{base_url}{url_path}'
        code_lines.append(f'                page.goto("{url_path}")')
        code_lines.append(f'                page.wait_for_load_state("networkidle")')
    
    elif action_type == "click":
        code_lines.append(f'                page.click("{selector}")')
    
    elif action_type == "fill":
        code_lines.append(f'                page.fill("{selector}", "{value}")')
    
    elif action_type == "wait":
        code_lines.append(f'                page.wait_for_selector("{selector}", timeout=10000)')
    
    elif action_type == "assert_url":
        code_lines.append(f'                assert "{value}" in page.url, f"URL assertion failed: expected \\"{value}\\" in {{page.url}}"')
    
    elif action_type == "assert_visible":
        code_lines.append(f'                expect(page.locator("{selector}")).to_be_visible()')
    
    elif action_type == "assert_text":
        if selector:
            code_lines.append(f'                expect(page.locator("{selector}")).to_contain_text("{value}")')
        else:
            code_lines.append(f'                expect(page.locator("body")).to_contain_text("{value}")')
    
    else:
        code_lines.append(f'                pass  # Unknown action: {action_type}')
    
    # Add step completion
    code_lines.append(f'            except Exception as step_error:')
    code_lines.append(f'                step_result["status"] = "fail"')
    code_lines.append(f'                step_result["error"] = str(step_error)')
    code_lines.append(f'                raise')
    code_lines.append(f'            finally:')
    code_lines.append(f'                step_result["time_ms"] = int((time.time() - step_start) * 1000)')
    code_lines.append(f'                results["steps"].append(step_result)')
    code_lines.append('')
    
    return '\n'.join(code_lines)


def generate_code(state: AgentState) -> AgentState:
    """
    Generate Playwright Python script from parsed actions.
    
    This is a LangGraph node function that:
    1. Takes parsed_actions from state
    2. Generates executable Playwright code
    3. Returns updated state with generated_code
    
    Args:
        state: Current agent state with parsed_actions
        
    Returns:
        Updated state with generated_code populated
    """
    parsed_actions = state["parsed_actions"]
    base_url = state["base_url"]
    instruction = state["instruction"]
    
    if not parsed_actions:
        error_msg = "No parsed actions to generate code from"
        state["errors"].append(error_msg)
        state["generated_code"] = ""
        print(f"❌ {error_msg}")
        return state
    
    try:
        # Generate code for each step
        step_codes = []
        for i, action in enumerate(parsed_actions, 1):
            step_code = generate_step_code(action, i, base_url)
            step_codes.append(step_code)
        
        # Combine all steps
        all_steps = '\n'.join(step_codes)
        
        # Generate the complete script
        generated_code = PLAYWRIGHT_TEMPLATE.format(
            timestamp=datetime.now().isoformat(),
            instruction=instruction.replace('"', '\\"'),
            test_steps=all_steps,
            record_video="False"  # Can be made configurable
        )
        
        state["generated_code"] = generated_code
        
        print(f"✅ Generated Playwright script with {len(parsed_actions)} steps")
        
    except Exception as e:
        error_msg = f"Failed to generate code: {str(e)}"
        state["errors"].append(error_msg)
        state["generated_code"] = ""
        print(f"❌ {error_msg}")
    
    return state
