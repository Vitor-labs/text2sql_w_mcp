from asyncio import run

from client.client import Chat
from main.server import mcp

chat = Chat()

if __name__ == "__main__":
    print("Starting server...")
    #mcp.run(transport="stdio")
    run(chat.run())
