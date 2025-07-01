# src/run.py
import os
import sys
import traceback
from asyncio import run
from pathlib import Path

from dotenv import load_dotenv
from google.genai import Client
from mcp import StdioServerParameters

# Add src to path if not already there
if "src" not in sys.path:
    sys.path.append("src")

from client.client import Chat
from config.logger import logger

load_dotenv()


async def test_server_connectivity():
    """Test if the server can start properly"""
    try:
        logger.info("Testing server connectivity...")

        if not (server_path := Path("src/main/server.py")).exists():
            raise Exception(f"Server file not found: {server_path}")

        sys.path.insert(0, str(Path("src").absolute()))
        try:
            logger.info("Server module imported successfully")
        except Exception as e:
            logger.error(f"Failed to import server module: {e}")
            raise

        return True
    except Exception as e:
        logger.error(f"Server connectivity test failed: {e}")
        return False


async def main():
    """Main CLI entry point with enhanced error handling"""
    try:
        logger.info("Starting SQL Agent CLI...")
        if not (api_key := os.getenv("GOOGLE_API_KEY")):
            raise Exception("❌ GOOGLE_API_KEY not found in environment variables")

        # Test server connectivity
        if not await test_server_connectivity():
            raise Exception("❌ Server connectivity test failed")

        await Chat(
            genai_client=Client(api_key=api_key),
            server_params=StdioServerParameters(
                command="python", args=["src/main/server.py"], env=None
            ),
        ).run()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Error running CLI: {e}\ntraceback: {traceback.format_exc()}")


if __name__ == "__main__":
    run(main())
