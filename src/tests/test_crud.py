from json import load
from pathlib import Path

from src.client.client import Chat

expected_data_dir = Path(__file__).parent / "data" / "expected"


async def test_insert_and_delete_operations(chat: Chat) -> bool:
    """Test insert and delete operations."""
    print("\n🧪 Testing insert and delete operations...")

    insert_data_file = expected_data_dir / "insert_test_data.json"
    if not insert_data_file.exists():
        print("❌ Insert test data file not found")
        return False

    with open(insert_data_file, "r") as f:
        insert_data = load(f)

    success_count = 0
    total_operations = 0

    if "new_customers" in insert_data:
        for customer in insert_data["new_customers"]:
            total_operations += 1

            insert_query = f"""
            INSERT INTO customers (customer_id, name, email, city, country, age) 
            VALUES ({customer["customer_id"]}, '{customer["name"]}', '{customer["email"]}', 
                    '{customer["city"]}', '{customer["country"]}', {customer["age"]})
            """
            print(f"➕ Inserting customer: {customer['name']}")
            response = await chat.process_query(f"EXECUTE_SQL: {insert_query}")

            if "successfully" in response.lower() or "1 rows affected" in response:
                # Verify insertion
                verify_query = f"SELECT * FROM customers WHERE customer_id = {customer['customer_id']}"
                if customer["name"] in await chat.process_query(
                    f"EXECUTE_SQL: {verify_query}"
                ):
                    print(f"✅ Customer {customer['name']} inserted and verified")
                    # Now delete the record
                    delete_response = await chat.process_query(
                        f"EXECUTE_SQL: DELETE FROM customers WHERE customer_id = {customer['customer_id']}"
                    )
                    if (
                        "successfully" in delete_response.lower()
                        or "1 rows affected" in delete_response
                    ):
                        # Verify deletion
                        check = await chat.process_query(f"EXECUTE_SQL: {verify_query}")
                        if "No results" in check or "0 rows" in check:
                            print(
                                f"✅ Customer {customer['name']} deleted and verified"
                            )
                            success_count += 1
                        else:
                            print(
                                f"❌ Customer {customer['name']} deletion verification failed"
                            )
                    else:
                        print(f"❌ Customer {customer['name']} deletion failed")
                else:
                    print(
                        f"❌ Customer {customer['name']} insertion verification failed"
                    )
            else:
                print(f"❌ Customer {customer['name']} insertion failed")

    print(f"\n📊 Insert/Delete operations: {success_count}/{total_operations} passed")
    return success_count == total_operations
