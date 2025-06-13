import asyncio
import os

from dotenv import load_dotenv
from google import genai
from mcp import StdioServerParameters

from client.client import Chat

load_dotenv()

genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
server_params = StdioServerParameters(
    command="python", args=["./src/main/server.py"], env=None
)


async def start_cli_chat() -> None:
    """
    Exemplo de execução em linha de comando (terminal).
    Esta função cria uma instância do Chat, passa genai_client e server_params,
    e executa o run() para iniciar o loop de stdin/stdout.
    """
    print("Starting server dentro do start_cli_chat()…")
    await Chat(genai_client=genai_client, server_params=server_params).run()


if __name__ == "__main__":
    # Se desejarmos rodar em terminal: python main.py
    asyncio.run(start_cli_chat())
