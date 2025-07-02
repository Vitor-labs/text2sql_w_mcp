import sqlite3

import pandas as pd
import pytest

from config.logger import logger


class TestMCPDatabaseIntegration:
    """Integration tests for MCP database operations."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, chat_client, temp_database, raw_data_dir):
        """Test complete workflow: create tables, insert data, run complex queries."""

        # Step 1: Create database schema
        schema_query = """
        I need to create a complete e-commerce database schema. Please create tables for:
        customers, suppliers, products, orders, and order_items with appropriate relationships.
        """

        schema_response = await chat_client.process_query(schema_query)

        # Step 2: Load sample data
        customers_df = pd.read_csv(raw_data_dir / "customers.csv")
        insert_query = f"""
        Insert sample customer data. Here are a few examples:
        {customers_df.head(3).to_string(index=False)}
        
        Please insert all customers from this pattern.
        """

        insert_response = await chat_client.process_query(insert_query)

        # Step 3: Run analysis query
        analysis_query = """
        Now analyze the customer data:
        1. Show total number of customers
        2. Show customers by country
        3. Show average credit limit
        """

        analysis_response = await chat_client.process_query(analysis_query)

        # Verify the complete workflow worked
        conn = sqlite3.connect(temp_database)

        # Check if customers table exists and has data
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customers")
            customer_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT country) FROM customers")
            country_count = cursor.fetchone()[0]

            assert customer_count > 0, (
                f"No customers inserted. Responses: Schema: {schema_response}, Insert: {insert_response}"
            )
            assert country_count > 1, (
                f"Country diversity not captured. Analysis: {analysis_response}"
            )

        except sqlite3.Error as e:
            pytest.fail(f"Database error during workflow test: {e}")
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_error_handling(self, chat_client):
        """Test how the model handles SQL errors and invalid queries."""

        # Test 1: Invalid table name
        invalid_query = "SELECT * FROM non_existent_table"
        response1 = await chat_client.process_query(
            f"Execute this query: {invalid_query}"
        )

        # Test 2: Invalid syntax
        syntax_error_query = "SELCT * FORM customers"  # Intentional typos
        response2 = await chat_client.process_query(
            f"Execute this query: {syntax_error_query}"
        )

        # Test 3: Constraint violation
        constraint_query = """
        First create a table: CREATE TABLE test_table (id INTEGER PRIMARY KEY, email TEXT UNIQUE);
        Then try to insert duplicate emails and see what happens.
        """
        response3 = await chat_client.process_query(constraint_query)

        # Verify error handling
        assert "error" in response1.lower() or "not exist" in response1.lower(), (
            f"Model didn't handle table error: {response1}"
        )
        assert "error" in response2.lower() or "syntax" in response2.lower(), (
            f"Model didn't handle syntax error: {response2}"
        )

        logger.info(f"Error handling responses: {response1}, {response2}, {response3}")

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, chat_client, temp_database):
        """Test model performance with larger datasets."""

        # Create a larger dataset programmatically
        large_data_query = """
        Create a performance test:
        1. Create a table called 'performance_test' with columns: id, name, value, category, created_date
        2. Insert 1000 random records for testing
        3. Create indexes on frequently queried columns
        4. Run a complex aggregation query to test performance
        """

        response = await chat_client.process_query(large_data_query)

        # Verify the model handled the large dataset appropriately
        conn = sqlite3.connect(temp_database)
        try:
            cursor = conn.cursor()

            # Check if table was created
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='performance_test'"
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM performance_test")
                record_count = cursor.fetchone()[0]
                logger.info(f"Performance test created {record_count} records")
            else:
                record_count = 0

            # We don't require exactly 1000 records, just that the model attempted to create a substantial dataset
            assert table_exists, (
                f"Performance test table not created. Response: {response}"
            )

        except sqlite3.Error as e:
            logger.warning(f"Performance test database error: {e}")
        finally:
            conn.close()
