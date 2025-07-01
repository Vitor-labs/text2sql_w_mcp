# src/run.py
import asyncio
import os
import sys
import traceback
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

        # Check if server file exists
        server_path = Path("src/main/server.py")
        if not server_path.exists():
            raise Exception(f"Server file not found: {server_path}")

        # Try to import the server module
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

        # Check API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise Exception("❌ GOOGLE_API_KEY not found in environment variables")
        logger.info("✅ Google API key found")

        # Test server connectivity
        if not await test_server_connectivity():
            raise Exception("❌ Server connectivity test failed")
        logger.info("✅ Server connectivity test passed")

        # Create and run chat
        chat = Chat(
            genai_client=Client(api_key=api_key),
            server_params=StdioServerParameters(
                command="python", args=["src/main/server.py"], env=None
            ),
        )

        logger.info("✅ Chat instance created, starting...")
        await chat.run()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Error running CLI: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        print(f"❌ Error: {e}")
        print("💡 Check the logs above for more details")


if __name__ == "__main__":
    asyncio.run(main())
