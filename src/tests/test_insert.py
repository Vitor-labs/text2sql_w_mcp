import sqlite3

import pandas as pd
import pytest


class TestDataInsertion:
    """Test the model's ability to insert data into existing tables."""

    @pytest.mark.asyncio
    async def test_insert_single_customer(self, chat_client, temp_database):
        """Test inserting a single customer record."""
        # Setup: Create customer table
        conn = sqlite3.connect(temp_database)
        conn.execute("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                city TEXT,
                country TEXT,
                registration_date DATE,
                credit_limit DECIMAL(10,2)
            )
        """)
        conn.commit()
        conn.close()

        # Test: Ask model to insert a customer
        query = """
        Please insert a new customer with the following details:
        - Name: Test Customer
        - Email: test@example.com
        - City: Test City
        - Country: Test Country
        - Registration Date: 2024-03-25
        - Credit Limit: 5000.00
        """

        response = await chat_client.process_query(query)

        # Verify: Check if record was inserted
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE email = 'test@example.com'")
        result = cursor.fetchone()
        conn.close()

        assert result is not None, f"Customer not inserted. Response: {response}"
        assert result[1] == "Test Customer"
        assert result[2] == "test@example.com"

    @pytest.mark.asyncio
    async def test_insert_multiple_products(
        self, chat_client, temp_database, raw_data_dir
    ):
        """Test inserting multiple product records."""
        # Setup: Create products table
        conn = sqlite3.connect(temp_database)
        conn.execute("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price DECIMAL(10,2),
                stock_quantity INTEGER,
                supplier_id INTEGER,
                created_date DATE
            )
        """)
        conn.commit()
        conn.close()

        # Load sample products
        products_df = pd.read_csv(raw_data_dir / "products.csv")
        first_three_products = products_df.head(3)

        # Format products for insertion
        products_text = ""
        for _, row in first_three_products.iterrows():
            products_text += f"""
            - Product: {row["name"]}, Category: {row["category"]}, 
              Price: {row["price"]}, Stock: {row["stock_quantity"]}, 
              Supplier ID: {row["supplier_id"]}, Created: {row["created_date"]}
            """

        query = f"""
        Please insert the following products into the products table:
        {products_text}
        """

        response = await chat_client.process_query(query)

        # Verify: Check if records were inserted
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 3, f"Expected 3 products, got {count}. Response: {response}"

    @pytest.mark.asyncio
    async def test_insert_with_validation(self, chat_client, temp_database):
        """Test insertion with data validation constraints."""
        # Setup: Create table with constraints
        conn = sqlite3.connect(temp_database)
        conn.execute("""
            CREATE TABLE validated_customers (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                age INTEGER CHECK(age >= 18),
                credit_score INTEGER CHECK(credit_score BETWEEN 300 AND 850)
            )
        """)
        conn.commit()
        conn.close()

        # Test valid insertion
        valid_query = """
        Insert a customer with email 'valid@test.com', age 25, and credit score 750
        """

        response = await chat_client.process_query(valid_query)

        # Verify valid insertion worked
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM validated_customers WHERE email = 'valid@test.com'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None, f"Valid customer not inserted. Response: {response}"

        # Test invalid insertion (should fail)
        invalid_query = """
        Insert a customer with email 'invalid@test.com', age 16, and credit score 900
        """

        response = await chat_client.process_query(invalid_query)

        # Verify invalid insertion was rejected
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM validated_customers WHERE email = 'invalid@test.com'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is None, (
            f"Invalid customer was inserted when it shouldn't be. Response: {response}"
        )
