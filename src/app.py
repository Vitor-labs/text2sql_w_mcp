# src/app.py
import asyncio
import logging
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client.client import Chat

# Setup paths
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))


# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Configuration
@st.cache_resource
def get_genai_client():
    """Get cached GenAI client"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY not found in environment variables")
        st.stop()
    return genai.Client(api_key=api_key)


@st.cache_data
def get_server_params():
    """Get server parameters"""
    return StdioServerParameters(
        command="python",
        args=[str(PROJECT_ROOT / "src" / "main" / "server.py")],
        env=None,
    )


# Initialize session state
def init_session_state():
    """Initialize Streamlit session state"""
    if "chat" not in st.session_state:
        st.session_state.chat = Chat(
            genai_client=get_genai_client(), server_params=get_server_params()
        )

    if "history" not in st.session_state:
        st.session_state.history = []

    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False


async def process_user_input(chat_obj: Chat, user_query: str) -> str:
    """Process user input through the chat system"""
    try:
        async with stdio_client(chat_obj.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                return await chat_obj.process_query(session, user_query)
    except Exception as e:
        logger.error(f"Error processing user input: {e}")
        return f"❌ Error: {str(e)}"


def send_message(user_text: str) -> str:
    """Send message and get response"""
    return asyncio.run(process_user_input(st.session_state.chat, user_text))


# Streamlit UI
def main():
    st.set_page_config(page_title="Text2SQL Agent", page_icon="🗣️", layout="wide")

    init_session_state()

    # Header
    st.title("🗣️ Text2SQL Agent")
    st.markdown("*Powered by Gemini + MCP*")

    # Sidebar with info
    with st.sidebar:
        st.header("ℹ️ Information")
        st.markdown("""
        This is a text-to-SQL agent that can:
        - Convert natural language to SQL
        - Execute queries on your database
        - Format results in tables
        - Provide explanations
        
        **Available Commands:**
        - Ask questions about your data
        - Request specific SQL queries
        - Ask for database schema
        """)

        if st.button("🗑️ Clear History"):
            st.session_state.history = []
            st.session_state.chat.messages = st.session_state.chat.messages[
                :1
            ]  # Keep system message
            st.rerun()

    # Chat history
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.history:
            if msg["author"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

    # Input form
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([6, 1])

        with col1:
            user_input = st.text_input(
                "Ask me anything about your data...",
                placeholder="e.g., 'Show me all users' or 'What's the database schema?'",
                disabled=st.session_state.is_processing,
            )

        with col2:
            submitted = st.form_submit_button(
                "Send", disabled=st.session_state.is_processing
            )

    # Process input
    if submitted and user_input.strip():
        # Add user message to history
        st.session_state.history.append({"author": "user", "content": user_input})

        # Set processing state
        st.session_state.is_processing = True
        st.rerun()

    # Handle processing
    if st.session_state.is_processing and st.session_state.history:
        last_message = st.session_state.history[-1]
        if last_message["author"] == "user":
            with st.spinner("🤔 Thinking and processing..."):
                try:
                    response = send_message(last_message["content"])
                    st.session_state.history.append(
                        {"author": "assistant", "content": response}
                    )
                except Exception as e:
                    st.session_state.history.append(
                        {
                            "author": "assistant",
                            "content": f"❌ An error occurred: {str(e)}",
                        }
                    )
                finally:
                    st.session_state.is_processing = False
                    st.rerun()


if __name__ == "__main__":
    main()
