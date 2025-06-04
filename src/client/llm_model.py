import asyncio
import os

from dotenv import load_dotenv
from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client.chat import Chat

load_dotenv()

genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

server_params = StdioServerParameters(
    command="python",
    args=["./src/main/server.py"],
    env=None,
)


async def start_cli_chat() -> None:
    chat = Chat(genai_client=genai_client, server_params=server_params)
    print("Starting server dentro do start_cli_chat()…")
    await chat.run()


if __name__ == "__main__":
    asyncio.run(start_cli_chat())
