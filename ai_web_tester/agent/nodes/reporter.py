"""
Reporter Node

This module generates structured test reports from execution results.
It produces both JSON and human-readable formats.
"""

import json
from datetime import datetime
from typing import List

from ..state import AgentState, TestReport, StepResult


def calculate_summary(steps: List[StepResult]) -> dict:
    """
    Calculate test summary statistics.
    
    Args:
        steps: List of step results
        
    Returns:
        Summary dictionary with pass/fail counts
    """
    total = len(steps)
    passed = sum(1 for s in steps if s.get("status") == "pass")
    failed = total - passed
    
    return {
        "total": total,
        "passed": passed,
        "failed": failed
    }


def get_failure_reason(steps: List[StepResult], error_message: str = None) -> str:
    """
    Extract the failure reason from steps or error message.
    
    Args:
        steps: List of step results
        error_message: Overall error message if any
        
    Returns:
        Human-readable failure reason
    """
    # Check for failed steps
    for step in steps:
        if step.get("status") == "fail" and step.get("error"):
            return f"Step {step['step_number']} ({step['action']}): {step['error']}"
    
    # Fall back to overall error message
    if error_message:
        return error_message
    
    return None


def collect_screenshots(steps: List[StepResult]) -> List[str]:
    """
    Collect all screenshots from step results.
    
    Args:
        steps: List of step results
        
    Returns:
        List of screenshot file paths
    """
    screenshots = []
    for step in steps:
        if step.get("screenshot"):
            screenshots.append(step["screenshot"])
    return screenshots


def generate_human_readable_report(
    instruction: str,
    base_url: str,
    status: str,
    summary: dict,
    steps: List[StepResult],
    failure_reason: str,
    execution_time_ms: int
) -> str:
    """
    Generate a human-readable test report.
    
    Args:
        instruction: Original test instruction
        base_url: Target website URL
        status: Overall test status
        summary: Summary statistics
        steps: List of step results
        failure_reason: Reason for failure if any
        execution_time_ms: Total execution time
        
    Returns:
        Formatted report string
    """
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append("  AI WEB TESTING AGENT - TEST REPORT")
    lines.append("=" * 60)
    lines.append("")
    
    # Test Info
    lines.append(f"📋 Instruction: {instruction}")
    lines.append(f"🌐 Target URL: {base_url}")
    lines.append(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Status
    status_emoji = "✅" if status == "PASSED" else "❌"
    lines.append(f"{status_emoji} STATUS: {status}")
    lines.append("")
    
    # Summary
    lines.append("-" * 40)
    lines.append("📊 SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total Steps:  {summary['total']}")
    lines.append(f"  Passed:       {summary['passed']}")
    lines.append(f"  Failed:       {summary['failed']}")
    lines.append(f"  Duration:     {execution_time_ms}ms")
    lines.append("")
    
    # Step Details
    lines.append("-" * 40)
    lines.append("📝 STEP DETAILS")
    lines.append("-" * 40)
    
    for step in steps:
        step_emoji = "✅" if step.get("status") == "pass" else "❌"
        selector = step.get("selector", "")
        selector_str = f" [{selector}]" if selector else ""
        
        lines.append(f"  {step_emoji} Step {step['step_number']}: {step['action']}{selector_str}")
        lines.append(f"     Time: {step.get('time_ms', 0)}ms")
        
        if step.get("error"):
            lines.append(f"     Error: {step['error']}")
        
        lines.append("")
    
    # Failure Details
    if failure_reason:
        lines.append("-" * 40)
        lines.append("⚠️ FAILURE DETAILS")
        lines.append("-" * 40)
        lines.append(f"  {failure_reason}")
        lines.append("")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def generate_report(state: AgentState) -> AgentState:
    """
    Generate structured test report from execution results.
    
    This is a LangGraph node function that:
    1. Takes execution_result from state
    2. Generates JSON and human-readable reports
    3. Returns updated state with report
    
    Args:
        state: Current agent state with execution_result
        
    Returns:
        Updated state with report populated
    """
    execution_result = state["execution_result"]
    instruction = state["instruction"]
    base_url = state["base_url"]
    
    # Calculate summary
    steps = execution_result.get("steps", [])
    summary = calculate_summary(steps)
    
    # Determine status
    if execution_result["success"] and summary["failed"] == 0:
        status = "PASSED"
    else:
        status = "FAILED"
    
    # Get failure reason
    failure_reason = get_failure_reason(
        steps,
        execution_result.get("error_message")
    )
    
    # Collect screenshots
    screenshots = collect_screenshots(steps)
    
    # Generate human-readable report
    human_readable = generate_human_readable_report(
        instruction=instruction,
        base_url=base_url,
        status=status,
        summary=summary,
        steps=steps,
        failure_reason=failure_reason,
        execution_time_ms=execution_result.get("total_time_ms", 0)
    )
    
    # Build the report
    report = TestReport(
        status=status,
        total_steps=summary["total"],
        passed=summary["passed"],
        failed=summary["failed"],
        execution_time_ms=execution_result.get("total_time_ms", 0),
        steps=steps,
        failure_reason=failure_reason,
        screenshots=screenshots,
        human_readable=human_readable
    )
    
    state["report"] = report
    
    # Print the report
    print("\n" + human_readable)
    
    return state


def report_to_json(report: TestReport) -> str:
    """
    Convert report to JSON string.
    
    Args:
        report: TestReport object
        
    Returns:
        JSON string
    """
    # Create a copy without human_readable for cleaner JSON
    report_dict = dict(report)
    del report_dict["human_readable"]
    
    return json.dumps(report_dict, indent=2)
