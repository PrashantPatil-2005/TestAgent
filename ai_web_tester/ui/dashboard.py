"""
Streamlit Dashboard for AI Web Testing Agent

This module provides a modern, user-friendly interface for:
- Entering natural language test instructions
- Configuring target URLs
- Running tests and viewing real-time status
- Viewing structured test reports
- Viewing generated Playwright code
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_api_key():
    """Check if Google API key is configured."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("⚠️ **Google API Key Required**")
        st.markdown("""
        Please create a `.env` file in the `ai_web_tester` directory with:
        ```
        GOOGLE_API_KEY=your_google_api_key_here
        ```
        
        Get your API key from: [Google AI Studio](https://makersuite.google.com/app/apikey)
        """)
        
        # Allow manual input
        manual_key = st.text_input("Or enter your API key here:", type="password")
        if manual_key:
            os.environ["GOOGLE_API_KEY"] = manual_key
            st.success("✅ API key set for this session!")
            return True
        return False
    return True


def render_step_status(step: dict):
    """Render a single step result with styling."""
    status = step.get("status", "unknown")
    action = step.get("action", "unknown")
    selector = step.get("selector", "")
    time_ms = step.get("time_ms", 0)
    error = step.get("error", "")
    
    if status == "pass":
        icon = "✅"
        color = "green"
    else:
        icon = "❌"
        color = "red"
    
    selector_str = f" `{selector}`" if selector else ""
    
    st.markdown(f"""
    <div style="padding: 10px; margin: 5px 0; border-left: 4px solid {color}; background-color: {'#1e3a1e' if status == 'pass' else '#3a1e1e'}; border-radius: 4px;">
        <strong>{icon} Step {step['step_number']}: {action}</strong>{selector_str}
        <br><small style="color: #888;">⏱️ {time_ms}ms</small>
        {f'<br><small style="color: #ff6b6b;">Error: {error}</small>' if error else ''}
    </div>
    """, unsafe_allow_html=True)


def render_report(report: dict):
    """Render the test report with metrics and details."""
    status = report.get("status", "UNKNOWN")
    
    # Status banner
    if status == "PASSED":
        st.success(f"## ✅ Test {status}")
    else:
        st.error(f"## ❌ Test {status}")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Steps", report.get("total_steps", 0))
    
    with col2:
        st.metric("Passed", report.get("passed", 0))
    
    with col3:
        st.metric("Failed", report.get("failed", 0))
    
    with col4:
        exec_time = report.get("execution_time_ms", 0)
        st.metric("Duration", f"{exec_time}ms")
    
    # Step details
    st.markdown("### 📝 Step Details")
    
    steps = report.get("steps", [])
    if steps:
        for step in steps:
            render_step_status(step)
    else:
        st.info("No step details available")
    
    # Failure reason
    failure_reason = report.get("failure_reason")
    if failure_reason:
        st.markdown("### ⚠️ Failure Details")
        st.error(failure_reason)
    
    # Screenshots
    screenshots = report.get("screenshots", [])
    if screenshots:
        st.markdown("### 📸 Screenshots")
        for screenshot in screenshots:
            if os.path.exists(screenshot):
                st.image(screenshot)
            else:
                st.warning(f"Screenshot not found: {screenshot}")


def main():
    """Main Streamlit application."""
    # Page config
    st.set_page_config(
        page_title="AI Web Testing Agent",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        }
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 2rem;
        }
        .sub-header {
            color: #a0a0a0;
            text-align: center;
            margin-bottom: 2rem;
        }
        .stTextArea textarea {
            background-color: #1e1e2e;
            border: 1px solid #3a3a5a;
            border-radius: 8px;
            color: #ffffff;
        }
        .stTextInput input {
            background-color: #1e1e2e;
            border: 1px solid #3a3a5a;
            border-radius: 8px;
            color: #ffffff;
        }
        .stButton button {
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 2rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4);
        }
        .code-block {
            background-color: #1e1e2e;
            border-radius: 8px;
            padding: 1rem;
            overflow-x: auto;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🤖 AI Web Testing Agent</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Convert natural language test instructions into automated Playwright tests</p>', unsafe_allow_html=True)
    
    # Check API key
    if not check_api_key():
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        base_url = st.text_input(
            "Target Base URL",
            value="http://localhost:5000",
            help="The base URL of the website to test"
        )
        
        st.markdown("---")
        
        st.markdown("### 📋 Quick Templates")
        
        if st.button("🔐 Login Test"):
            st.session_state.instruction = """Go to the login page, 
enter 'testuser' as username and 'password123' as password, 
click the Sign In button,
and verify the page shows 'Logged in as'"""
        
        if st.button("🔍 Search Test"):
            st.session_state.instruction = """Go to the search page,
enter 'test query' in the search field,
click the Search button,
and verify the page shows 'Search result'"""
        
        if st.button("📝 Multi-step Form"):
            st.session_state.instruction = """Go to the form step 1 page,
click the Next button,
and verify we are on form-step-2"""
        
        st.markdown("---")
        
        st.markdown("### 📊 Statistics")
        if "test_history" in st.session_state:
            total = len(st.session_state.test_history)
            passed = sum(1 for t in st.session_state.test_history if t.get("status") == "PASSED")
            st.metric("Total Tests", total)
            st.metric("Pass Rate", f"{(passed/total*100):.1f}%" if total > 0 else "N/A")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📝 Test Instruction")
        
        # Get instruction from session state or use default
        default_instruction = st.session_state.get("instruction", """Go to the login page,
enter 'testuser' as username and 'password123' as password,
click the Sign In button,
and verify the page shows 'Logged in as'""")
        
        instruction = st.text_area(
            "Enter your test instruction in plain English:",
            value=default_instruction,
            height=200,
            placeholder="Example: Go to the login page, enter username and password, click login button, verify dashboard loads"
        )
        
        # Run button
        if st.button("🚀 Run Test", use_container_width=True):
            if instruction.strip():
                with st.spinner("🔄 Running AI-powered test..."):
                    try:
                        # Import and run the agent
                        from agent.graph import run_agent
                        
                        # Run the agent
                        result = run_agent(instruction, base_url)
                        
                        # Store result in session state
                        st.session_state.last_result = result
                        
                        # Add to history
                        if "test_history" not in st.session_state:
                            st.session_state.test_history = []
                        st.session_state.test_history.append({
                            "instruction": instruction,
                            "status": result["report"]["status"],
                            "report": result["report"]
                        })
                        
                        st.success("✅ Test completed!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error running test: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
            else:
                st.warning("Please enter a test instruction")
    
    with col2:
        st.markdown("### 📊 Test Report")
        
        if "last_result" in st.session_state:
            result = st.session_state.last_result
            render_report(result["report"])
        else:
            st.info("Run a test to see the report here")
    
    # Generated code section
    if "last_result" in st.session_state and st.session_state.last_result.get("generated_code"):
        st.markdown("---")
        st.markdown("### 💻 Generated Playwright Code")
        
        with st.expander("View Generated Code", expanded=False):
            st.code(st.session_state.last_result["generated_code"], language="python")
            
            # Download button
            st.download_button(
                label="📥 Download Test Script",
                data=st.session_state.last_result["generated_code"],
                file_name="generated_test.py",
                mime="text/plain"
            )
    
    # Parsed actions section
    if "last_result" in st.session_state and st.session_state.last_result.get("parsed_actions"):
        st.markdown("---")
        st.markdown("### 🎯 Parsed Actions")
        
        with st.expander("View Parsed Actions", expanded=False):
            import json
            st.json(st.session_state.last_result["parsed_actions"])
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p>Built with ❤️ using LangGraph, Playwright, and Streamlit</p>
        <p><small>AI Web Testing Agent v1.0</small></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
