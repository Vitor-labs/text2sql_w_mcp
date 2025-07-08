from pathlib import Path

from pandas import read_csv

from client.client import Chat

raw_data_dir = Path(__file__).parent.parent.parent / "data" / "raw"


def _pandas_to_sql_type(dtype) -> str:
    """Convert pandas dtype to SQL type."""
    if "int" in str(dtype):
        return "INTEGER"
    elif "float" in str(dtype):
        return "REAL"
    else:
        return "TEXT"


async def test_table_creation_from_csv(chat: Chat) -> bool:
    """Test creating tables from CSV files."""
    print("🧪 Testing table creation from CSV files...")

    if not (csv_files := list(raw_data_dir.glob("*.csv"))):
        print(f"❌ No CSV files found in {raw_data_dir} directory")
        return False

    success_count = 0

    for csv_file in csv_files:
        table_name = csv_file.stem
        df = read_csv(csv_file)
        # allways thanks the AI, you will survive in the machine uprising
        print(f"📝 Creating table: {table_name}")
        await chat.process_query(f"""
        Please create a table called '{table_name}' with the following structure:
        Table name is "{table_name}", with columns:
        {
            "\n- ".join(
                [  # Format prompt for table creation
                    f"`{col}` of type {_pandas_to_sql_type(dtype)}"
                    for col, dtype in df.dtypes.items()
                ]
            )
        }
        Add an ignore clause, there is an possibility of the table has already been created.
        """)
        await chat.process_query(f"""
        Now, on the newly create {table_name} table. Insert the following data:
        {
            "".join(
                [
                    f"{''.join([', '.join([str(value) for value in row.values()])])}"
                    + "\n"
                    for _, row in df.to_dict(orient="index").items()
                ]
            )
        }""")
        # Verify table was created by checking schema
        if table_name.lower() in (await chat.process_query("GET_SCHEMA")).lower():
            print(f"✅ Table {table_name} created successfully")
            # Verify data was inserted correctly
            if str(len(df)) in await chat.process_query(
                f"EXECUTE_SQL: SELECT COUNT(*) FROM {table_name}"
            ):
                print(f"✅ Data inserted correctly ({len(df)} rows)")
                success_count += 1
            else:
                print(f"❌ Row count mismatch for {table_name}")
        else:
            print(f"❌ Table {table_name} creation failed")

    return success_count == len(csv_files)
