import asyncio
import os
import sys

import streamlit as st
from dotenv import load_dotenv
from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client.client import Chat

load_dotenv()

PROJECT_ROOT = os.path.dirname(__file__)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)


genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
server_params = StdioServerParameters(
    command="python",
    args=["./src/main/server.py"],
    env=None,
)

if "chat" not in st.session_state:
    # A classe Chat agora não precisa mais de messages no construtor
    st.session_state.chat = Chat(genai_client=genai_client, server_params=server_params)


if "history" not in st.session_state:
    st.session_state.history = [
        {
            "author": "system",
            "content": (
                "Você é um assistente mestre de SQLite. "
                "Seu trabalho é executar queries SQL via ferramentas externas "
                "e retornar resultados ao usuário."
            ),
        }
    ]


async def _send_to_gemini_and_sql(chat_obj: Chat, user_query: str) -> str: # Modificado para retornar str
    async with stdio_client(chat_obj.server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            # A nova process_query fará todo o trabalho pesado.
            return await chat_obj.process_query(session, user_query)

def send_to_assistant(user_text: str) -> None:
    chat = Chat(genai_client=genai_client, server_params=server_params)
    return asyncio.run(_send_to_gemini_and_sql(chat, user_text))


st.title("🗣️ text2sql (com Gemini + MCP)")

# Renderiza cada mensagem armazenada em session_state.history
for msg in st.session_state.history:
    if msg["author"] == "system":
        st.markdown(f"**⛑️ Sistema:**  {msg['content']}")
    elif msg["author"] == "user":
        st.markdown(f"**👤 Você:**  {msg['content']}")
    else:
        st.markdown(f"**🤖 Assistente:**  {msg['content']}")

st.divider()

with st.form("input_form", clear_on_submit=True):
    user_input = st.text_input("Digite seu comando SQL ou pergunta geral…")
    submitted = st.form_submit_button("Enviar")
    if submitted and user_input.strip() != "":
        st.session_state.history.append({"author": "user", "content": user_input})

        with st.spinner("Obtendo resposta…"):
            try:
                bot_answer = send_to_assistant(user_input)
            except Exception as e:
                bot_answer = f"❗ Ocorreu um erro ao chamar o servidor: {e}"

        st.session_state.history.append({"author": "assistant", "content": bot_answer})  # type: ignore

        st.rerun()
