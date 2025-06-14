import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.genai import Client
from mcp import StdioServerParameters

from client.client import Chat

PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main CLI entry point"""
    try:
        if not (api_key := os.getenv("GOOGLE_API_KEY")):
            raise Exception("❌ GOOGLE_API_KEY not found in environment variables")

        await Chat(
            genai_client=Client(api_key=api_key),
            server_params=StdioServerParameters(
                command="python", args=[str(SRC_DIR / "main" / "server.py")], env=None
            ),
        ).run()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Error running CLI: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
