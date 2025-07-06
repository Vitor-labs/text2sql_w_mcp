from json import load
from pathlib import Path

from src.client.client import Chat

expected_data_dir = Path(__file__).parent / "data" / "expected"


async def test_basic_queries(chat: Chat) -> bool:
    """Test basic SQL operations."""
    print("\n🧪 Testing basic SQL queries...")

    test_queries_file = expected_data_dir / "test_queries.json"
    if not test_queries_file.exists():
        print("❌ Test queries file not found")
        return False

    with open(test_queries_file, "r") as f:
        test_cases = load(f)

    success_count = 0
    total_tests = 0

    for category, tests in test_cases.items():
        print(f"\n📂 Testing category: {category}")

        for test_name, test_data in tests.items():
            total_tests += 1
            print(f"🔍 Running test: {test_name}")
            response = await chat.process_query(f"EXECUTE_SQL: {test_data['query']}")
            if (  # Check if query executed successfully (no error messages)
                "error" not in response.lower() and "exception" not in response.lower()
            ):
                print(f"✅ Query executed successfully: {test_name}")
                success_count += 1
            else:
                print(f"❌ Query failed: {test_name}")
                print(f"   Response: {response[:200]}...")

    print(f"\n📊 Basic queries: {success_count}/{total_tests} passed")
    return success_count == total_tests
