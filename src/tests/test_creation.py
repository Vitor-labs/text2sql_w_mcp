from pathlib import Path

from pandas import read_csv

from src.client.client import Chat

raw_data_dir = Path(__file__).parent / "data" / "raw"


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
        print("❌ No CSV files found in raw data directory")
        return False

    success_count = 0

    for csv_file in csv_files:
        table_name = csv_file.stem
        df = read_csv(csv_file)
        create_prompt = f"""
        Please create a table called '{table_name}' with the following structure:
        CREATE TABLE {table_name} (
            {
            ", ".join(
                [  # Format prompt for table creation
                    f"{col} {_pandas_to_sql_type(dtype)}"
                    for col, dtype in df.dtypes.items()
                ]
            )
        }
        );
    
        Then insert the following data:
        {df.to_csv(index=False, header=False)}
        
        Please execute the SQL commands to create and populate the table.
        """

        print(f"📝 Creating table: {table_name}")
        await chat.process_query(create_prompt)
        # Verify table was created by checking schema
        schema_response = await chat.process_query("GET_SCHEMA")

        if table_name.lower() in schema_response.lower():
            print(f"✅ Table {table_name} created successfully")
            # Verify data was inserted correctly
            count_response = await chat.process_query(
                f"EXECUTE_SQL: SELECT COUNT(*) FROM {table_name}"
            )
            if str(len(df)) in count_response:
                print(f"✅ Data inserted correctly ({len(df)} rows)")
                success_count += 1
            else:
                print(f"❌ Row count mismatch for {table_name}")
        else:
            print(f"❌ Table {table_name} creation failed")

    return success_count == len(csv_files)
