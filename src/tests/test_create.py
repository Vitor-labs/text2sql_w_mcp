import sqlite3

import pandas as pd
import pytest


class TestTableCreation:
    """Test the model's ability to create tables from CSV data."""

    @pytest.mark.asyncio
    async def test_create_customers_table_from_csv(
        self, chat_client, temp_database, raw_data_dir
    ):
        """Test creating customers table and importing CSV data."""
        customers_df = pd.read_csv(raw_data_dir / "customers.csv")

        # Create detailed prompt with CSV structure
        csv_content = customers_df.head(3).to_string(index=False)

        query = f"""
        I have a CSV file with customer data. Please create a table called 'customers' 
        and insert all the following data. Here's a sample of the CSV structure:
        
        {csv_content}
        
        The full data includes all {len(customers_df)} customers. Please:
        1. Create the appropriate table schema based on the data types
        2. Insert all the customer records
        3. Make sure customer_id is the primary key
        4. Make sure email is unique
        """

        response = await chat_client.process_query(query)

        # Verify table creation and data insertion
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
        )
        table_exists = cursor.fetchone() is not None

        # Check record count
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM customers")
            count = cursor.fetchone()[0]
        else:
            count = 0

        conn.close()

        assert table_exists, f"Customers table not created. Response: {response}"
        assert count > 0, f"No customer data inserted. Response: {response}"

    @pytest.mark.asyncio
    async def test_create_products_table_with_relationships(
        self, chat_client, temp_database, raw_data_dir
    ):
        """Test creating products table with foreign key relationships."""
        # First create suppliers table
        suppliers_df = pd.read_csv(raw_data_dir / "suppliers.csv")
        products_df = pd.read_csv(raw_data_dir / "products.csv")

        suppliers_content = suppliers_df.to_string(index=False)
        products_content = products_df.head(5).to_string(index=False)

        query = f"""
        I need to create two related tables from CSV data:
        
        1. First, create a 'suppliers' table and insert this data:
        {suppliers_content}
        
        2. Then, create a 'products' table and insert this sample data:
        {products_content}
        
        Make sure:
        - supplier_id in products references supplier_id in suppliers
        - Both tables have appropriate primary keys
        - Use appropriate data types for all columns
        """

        response = await chat_client.process_query(query)

        # Verify both tables and relationships
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        # Check suppliers table
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        suppliers_count = cursor.fetchone()[0]

        # Check products table
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]

        # Check foreign key relationship
        cursor.execute("""
            SELECT p.name, s.name 
            FROM products p 
            JOIN suppliers s ON p.supplier_id = s.supplier_id 
            LIMIT 1
        """)
        join_result = cursor.fetchone()

        conn.close()

        assert suppliers_count > 0, f"Suppliers not inserted. Response: {response}"
        assert products_count > 0, f"Products not inserted. Response: {response}"
        assert join_result is not None, (
            f"Foreign key relationship not working. Response: {response}"
        )

    @pytest.mark.asyncio
    async def test_create_orders_system_from_multiple_csvs(
        self, chat_client, temp_database, raw_data_dir
    ):
        """Test creating a complete order system from multiple CSV files."""
        # Load all CSV files
        customers_df = pd.read_csv(raw_data_dir / "customers.csv")
        orders_df = pd.read_csv(raw_data_dir / "orders.csv")
        order_items_df = pd.read_csv(raw_data_dir / "order_items.csv")

        query = f"""
        I need to create a complete order management system with the following tables:
        
        1. customers table with {len(customers_df)} records
        2. orders table with {len(orders_df)} records  
        3. order_items table with {len(order_items_df)} records
        
        Sample customers data:
        {customers_df.head(2).to_string(index=False)}
        
        Sample orders data:
        {orders_df.head(2).to_string(index=False)}
        
        Sample order_items data:
        {order_items_df.head(3).to_string(index=False)}
        
        Please:
        1. Create all tables with proper primary keys and foreign keys
        2. Insert all the data
        3. Ensure referential integrity between tables
        """

        response = await chat_client.process_query(query)

        # Verify complete system
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        # Check all tables exist and have data
        tables_data = {}
        for table in ["customers", "orders", "order_items"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            tables_data[table] = cursor.fetchone()[0]

        # Test a complex join to verify relationships
        cursor.execute("""
            SELECT c.name, o.order_date, oi.quantity, oi.unit_price
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            LIMIT 1
        """)
        complex_join = cursor.fetchone()

        conn.close()

        assert all(count > 0 for count in tables_data.values()), (
            f"Not all tables have data: {tables_data}. Response: {response}"
        )
        assert complex_join is not None, (
            f"Complex join failed - relationships not working. Response: {response}"
        )
