from asyncio import run
from os import getenv

from google.genai import Client
from mcp import StdioServerParameters

from client.client import Chat
from config import logger
from tests.test_creation import test_table_creation_from_csv


async def run_all_tests() -> dict[str, bool]:
    """Run all test suites."""
    chat = Chat(
        genai_client=Client(api_key=getenv("GOOGLE_API_KEY")),
        server_params=StdioServerParameters(
            command="python", args=["src/main/server.py"], env=None
        ),
    )
    print("🚀 Starting MCP SQL comprehensive ..\n")
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY:")
    print("=" * 50)

    try:
        async with chat.test_context():
            results = {
                "table_creation": await test_table_creation_from_csv(chat),
                # "basic_queries": await test_basic_queries(chat),
                # "insert_delete": await test_insert_and_delete_operations(chat),
                # "complex_queries": await test_complex_queries(chat),
            }
    except Exception as exc:
        logger.error(exc)
        raise exc

    for name, passed in results.items():
        print(
            f"{name.replace('_', ' ').title()}: {'✅ PASSED' if passed else '❌ FAILED'}"
        )
    print(f"\nOverall: {sum(results.values())}/{len(results)} test suites passed")
    print(f"Success rate: {(sum(results.values()) / len(results)) * 100:.1f}%")

    return results


if __name__ == "__main__":
    run(run_all_tests())
