from tests.test_basic_queries import test_basic_queries
from tests.test_complex import test_complex_queries
from tests.test_creation import test_table_creation_from_csv
from tests.test_crud import test_insert_and_delete_operations


async def run_all_tests() -> dict[str, bool]:
    """Run all test suites."""
    print("🚀 Starting MCP SQL comprehensive tests...\n")
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY:")
    print("=" * 50)
    results = {
        "table_creation": await test_table_creation_from_csv(),
        "basic_queries": await test_basic_queries(),
        "insert_delete": await test_insert_and_delete_operations(),
        "complex_queries": await test_complex_queries(),
    }
    passed_tests = sum(results.values())
    total_tests = len(results)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    print(f"\nOverall: {passed_tests}/{total_tests} test suites passed")
    print(f"Success rate: {(passed_tests / total_tests) * 100:.1f}%")

    return results
