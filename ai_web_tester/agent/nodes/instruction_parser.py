"""
Instruction Parser Node

This module converts natural language test instructions into structured browser actions
using an LLM (Google Gemini). It's the first node in the LangGraph pipeline.
"""

import os
import json
import re
from typing import List, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..state import AgentState, TestAction


# System prompt for the instruction parser
PARSER_SYSTEM_PROMPT = """You are an expert web testing engineer. Your job is to convert natural language test instructions into structured browser actions.

Given a test instruction, output a JSON array of actions. Each action should have:
- "action": The type of action (goto, click, fill, wait, assert_url, assert_visible, assert_text)
- "selector": CSS selector for the element (if applicable)
- "value": Value to use (for fill actions, URLs, or assertion values)

Action Types:
1. "goto" - Navigate to a URL path. Use "value" for the path (e.g., "/login")
2. "click" - Click an element. Use "selector" for the CSS selector
3. "fill" - Fill an input field. Use "selector" and "value"
4. "wait" - Wait for an element. Use "selector"
5. "assert_url" - Assert URL contains a value. Use "value"
6. "assert_visible" - Assert element is visible. Use "selector"
7. "assert_text" - Assert element contains text. Use "selector" and "value"

Selector Guidelines:
- Prefer input[name='fieldname'] for form fields
- Use button[type='submit'] or button:has-text('ButtonText') for buttons
- Use #id selectors when IDs are mentioned
- Use descriptive CSS selectors

IMPORTANT: Output ONLY valid JSON, no markdown formatting, no explanation.

Example Input: "Go to login page, enter username 'admin' and password 'secret', click login button"
Example Output:
[
  {"action": "goto", "value": "/login"},
  {"action": "fill", "selector": "input[name='username']", "value": "admin"},
  {"action": "fill", "selector": "input[name='password']", "value": "secret"},
  {"action": "click", "selector": "button[type='submit']"}
]
"""


def create_parser_chain():
    """Create the LangChain chain for parsing instructions."""
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.1,  # Low temperature for consistent outputs
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", PARSER_SYSTEM_PROMPT),
        ("human", "Convert this test instruction to actions:\n\n{instruction}")
    ])
    
    # Create parser
    parser = JsonOutputParser()
    
    # Build the chain
    chain = prompt | llm | parser
    
    return chain


def clean_json_response(response: str) -> str:
    """Clean LLM response to extract valid JSON."""
    # Remove markdown code blocks if present
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        response = response.split("```")[1].split("```")[0]
    
    # Strip whitespace
    return response.strip()


def normalize_actions(actions: List[Dict[str, Any]]) -> List[TestAction]:
    """
    Normalize parsed actions to ensure consistent structure.
    
    Args:
        actions: Raw actions from LLM
        
    Returns:
        List of normalized TestAction objects
    """
    normalized = []
    
    for action in actions:
        normalized_action = TestAction(
            action=action.get("action", ""),
            target=action.get("target") or action.get("value") if action.get("action") == "goto" else None,
            selector=action.get("selector"),
            value=action.get("value")
        )
        normalized.append(normalized_action)
    
    return normalized


def parse_instruction(state: AgentState) -> AgentState:
    """
    Parse natural language instruction into structured browser actions.
    
    This is a LangGraph node function that:
    1. Takes the instruction from state
    2. Uses LLM to convert it to structured actions
    3. Returns updated state with parsed_actions
    
    Args:
        state: Current agent state with instruction
        
    Returns:
        Updated state with parsed_actions populated
    """
    instruction = state["instruction"]
    
    try:
        # Create and run the parser chain
        chain = create_parser_chain()
        result = chain.invoke({"instruction": instruction})
        
        # Handle if result is already parsed or is a string
        if isinstance(result, str):
            result = json.loads(clean_json_response(result))
        
        # Normalize the actions
        parsed_actions = normalize_actions(result)
        
        # Update state
        state["parsed_actions"] = parsed_actions
        
        print(f"✅ Parsed {len(parsed_actions)} actions from instruction")
        for i, action in enumerate(parsed_actions, 1):
            print(f"   {i}. {action['action']}: {action.get('selector') or action.get('value', '')}")
        
    except Exception as e:
        error_msg = f"Failed to parse instruction: {str(e)}"
        state["errors"].append(error_msg)
        state["parsed_actions"] = []
        print(f"❌ {error_msg}")
    
    return state


def parse_instruction_fallback(instruction: str) -> List[TestAction]:
    """
    Fallback parser using regex patterns when LLM is unavailable.
    
    This is a simple rule-based parser for basic test instructions.
    """
    actions = []
    instruction_lower = instruction.lower()
    
    # Pattern matching for common actions
    patterns = {
        r"go to (?:the )?(\w+)(?: page)?": ("goto", "/{0}"),
        r"navigate to (?:the )?(\w+)(?: page)?": ("goto", "/{0}"),
        r"open (?:the )?(\w+)(?: page)?": ("goto", "/{0}"),
        r"enter ['\"]?(\w+)['\"]? (?:as|in|into) (?:the )?(\w+)": ("fill", "input[name='{1}']", "{0}"),
        r"type ['\"]?(\w+)['\"]? (?:in|into) (?:the )?(\w+)": ("fill", "input[name='{1}']", "{0}"),
        r"click (?:the )?(\w+)(?: button)?": ("click", "button:has-text('{0}')"),
        r"verify (?:the )?page shows ['\"]?(.+?)['\"]?": ("assert_text", "body", "{0}"),
        r"verify (?:we are on|url contains) ['\"]?(.+?)['\"]?": ("assert_url", None, "{0}"),
    }
    
    for pattern, action_template in patterns.items():
        matches = re.findall(pattern, instruction_lower)
        for match in matches:
            if isinstance(match, tuple):
                match = list(match)
            else:
                match = [match]
            
            action_type = action_template[0]
            selector = action_template[1].format(*match) if len(action_template) > 1 and action_template[1] else None
            value = action_template[2].format(*match) if len(action_template) > 2 else (action_template[1].format(*match) if action_type == "goto" else None)
            
            actions.append(TestAction(
                action=action_type,
                target=value if action_type == "goto" else None,
                selector=selector,
                value=value if action_type != "goto" else None
            ))
    
    return actions
