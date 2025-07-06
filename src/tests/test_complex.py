from json import load
from pathlib import Path

from src.client.client import Chat

expected_data_dir = Path(__file__).parent / "data" / "expected"


async def test_complex_queries(chat: Chat) -> bool:
    """Test complex queries with joins and aggregations."""
    print("\n🧪 Testing complex queries...")

    test_queries_file = expected_data_dir / "test_queries.json"
    with open(test_queries_file, "r") as f:
        test_cases = load(f)

    complex_categories = ["aggregations", "joins"]
    success_count = 0
    total_tests = 0

    for category in complex_categories:
        if category not in test_cases:
            continue

        print(f"\n📂 Testing complex category: {category}")

        for test_name, test_data in test_cases[category].items():
            total_tests += 1
            query = test_data["query"]

            print(f"🔍 Running complex test: {test_name}")
            response = await chat.process_query(f"EXECUTE_SQL: {query}")

            # More detailed validation for complex queries
            if "error" not in response.lower() and "exception" not in response.lower():
                # Check if expected data patterns are present
                if "expected_result" in test_data:
                    expected = test_data["expected_result"]
                    if isinstance(expected, list) and len(expected) > 0:
                        # Check if at least some expected values appear in response
                        found_matches = 0
                        for expected_row in expected[:2]:  # Check first 2 rows
                            for key, value in expected_row.items():
                                if str(value) in response:
                                    found_matches += 1
                                    break

                        if found_matches > 0:
                            print(
                                f"✅ Complex query passed with data validation: {test_name}"
                            )
                            success_count += 1
                        else:
                            print(
                                f"⚠️ Complex query executed but data validation failed: {test_name}"
                            )
                            success_count += 0.5  # Partial credit
                    else:
                        print(f"✅ Complex query executed successfully: {test_name}")
                        success_count += 1
                else:
                    print(f"✅ Complex query executed successfully: {test_name}")
                    success_count += 1
            else:
                print(f"❌ Complex query failed: {test_name}")
                print(f"   Response: {response[:200]}...")

    print(f"\n📊 Complex queries: {success_count}/{total_tests} passed")
    return success_count >= (total_tests * 0.8)  # 80% pass rate for complex queries
