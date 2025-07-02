import sqlite3

import pandas as pd
import pytest


class TestComplexQueries:
    """Test the model's ability to execute complex SQL queries."""

    @pytest.fixture(autouse=True)
    async def setup_test_database(self, temp_database, raw_data_dir):
        """Setup complete test database with all tables and data."""
        conn = sqlite3.connect(temp_database)

        # Create all tables
        tables_sql = {
            "customers": """
                CREATE TABLE customers (
                    customer_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    city TEXT,
                    country TEXT,
                    registration_date DATE,
                    credit_limit DECIMAL(10,2)
                )
            """,
            "suppliers": """
                CREATE TABLE suppliers (
                    supplier_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    contact_email TEXT,
                    phone TEXT,
                    country TEXT,
                    rating DECIMAL(3,2)
                )
            """,
            "products": """
                CREATE TABLE products (
                    product_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    price DECIMAL(10,2),
                    stock_quantity INTEGER,
                    supplier_id INTEGER,
                    created_date DATE,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
                )
            """,
            "orders": """
                CREATE TABLE orders (
                    order_id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    order_date DATE,
                    total_amount DECIMAL(10,2),
                    status TEXT,
                    shipping_city TEXT,
                    shipping_country TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """,
            "order_items": """
                CREATE TABLE order_items (
                    order_item_id INTEGER PRIMARY KEY,
                    order_id INTEGER,
                    product_id INTEGER,
                    quantity INTEGER,
                    unit_price DECIMAL(10,2),
                    total_price DECIMAL(10,2),
                    FOREIGN KEY (order_id) REFERENCES orders(order_id),
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                )
            """,
        }

        # Create tables
        for table_name, sql in tables_sql.items():
            conn.execute(sql)

        # Load and insert data
        csv_files = ["customers", "suppliers", "products", "orders", "order_items"]
        for csv_file in csv_files:
            df = pd.read_csv(raw_data_dir / f"{csv_file}.csv")
            df.to_sql(csv_file, conn, if_exists="append", index=False)

        conn.commit()
        conn.close()

        self.temp_database = temp_database

    @pytest.mark.asyncio
    async def test_top_customers_by_spending(self, chat_client, expected_data_dir):
        """Test finding top customers by total spending with JOIN and GROUP BY."""
        query = """
        Find the top 5 customers by total spending. Show customer name, 
        total amount spent, and number of orders. Order by total spending descending.
        """

        response = await chat_client.process_query(query)

        # Get actual result from database for comparison
        conn = sqlite3.connect(self.temp_database)
        actual_df = pd.read_sql_query(
            """
            SELECT 
                c.name as customer_name,
                SUM(o.total_amount) as total_spent,
                COUNT(o.order_id) as order_count
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_id, c.name
            ORDER BY total_spent DESC
            LIMIT 5
        """,
            conn,
        )
        conn.close()

        # Verify the response contains expected structure
        assert "customer" in response.lower(), (
            f"Response doesn't mention customers: {response}"
        )
        assert "total" in response.lower(), f"Response doesn't show totals: {response}"
        assert len(actual_df) > 0, "No data returned from query"

    @pytest.mark.asyncio
    async def test_product_sales_by_category(self, chat_client):
        """Test aggregating product sales by category."""
        query = """
        Show sales analysis by product category. Include:
        - Category name
        - Total revenue
        - Number of products sold
        - Average price per product
        Order by total revenue descending.
        """

        response = await chat_client.process_query(query)

        # Verify with direct database query
        conn = sqlite3.connect(self.temp_database)
        actual_df = pd.read_sql_query(
            """
            SELECT 
                p.category,
                SUM(oi.total_price) as total_revenue,
                SUM(oi.quantity) as products_sold,
                AVG(oi.unit_price) as avg_price
            FROM products p
            JOIN order_items oi ON p.product_id = oi.product_id
            GROUP BY p.category
            ORDER BY total_revenue DESC
        """,
            conn,
        )
        conn.close()

        assert len(actual_df) > 0, "No category data returned"
        assert "category" in response.lower(), (
            f"Response doesn't show categories: {response}"
        )
        assert "revenue" in response.lower(), (
            f"Response doesn't show revenue: {response}"
        )

    @pytest.mark.asyncio
    async def test_monthly_sales_trends(self, chat_client):
        """Test monthly sales analysis with date functions."""
        query = """
        Analyze sales trends by month for 2024. Show:
        - Month (format as YYYY-MM)
        - Total number of orders
        - Total revenue
        - Average order value
        Order by month.
        """

        response = await chat_client.process_query(query)

        # Verify with direct query
        conn = sqlite3.connect(self.temp_database)
        actual_df = pd.read_sql_query(
            """
            SELECT 
                strftime('%Y-%m', order_date) as month,
                COUNT(order_id) as total_orders,
                SUM(total_amount) as total_revenue,
                AVG(total_amount) as avg_order_value
            FROM orders
            WHERE strftime('%Y', order_date) = '2024'
            GROUP BY strftime('%Y-%m', order_date)
            ORDER BY month
        """,
            conn,
        )
        conn.close()

        assert len(actual_df) > 0, "No monthly data returned"
        assert "2024" in response, f"Response doesn't show 2024 data: {response}"
        assert "month" in response.lower(), (
            f"Response doesn't show monthly breakdown: {response}"
        )

    @pytest.mark.asyncio
    async def test_supplier_performance_analysis(self, chat_client):
        """Test complex query with multiple JOINs and subqueries."""
        query = """
        Create a supplier performance report showing:
        - Supplier name and country
        - Number of products they supply
        - Total revenue generated from their products
        - Average product rating (assume rating = supplier rating)
        - Total quantity sold of their products
        Only include suppliers who have products that were actually sold.
        Order by total revenue descending.
        """

        response = await chat_client.process_query(query)

        # Verify with complex query
        conn = sqlite3.connect(self.temp_database)
        actual_df = pd.read_sql_query(
            """
            SELECT 
                s.name as supplier_name,
                s.country,
                COUNT(DISTINCT p.product_id) as product_count,
                SUM(oi.total_price) as total_revenue,
                s.rating as avg_rating,
                SUM(oi.quantity) as total_quantity_sold
            FROM suppliers s
            JOIN products p ON s.supplier_id = p.supplier_id
            JOIN order_items oi ON p.product_id = oi.product_id
            GROUP BY s.supplier_id, s.name, s.country, s.rating
            ORDER BY total_revenue DESC
        """,
            conn,
        )
        conn.close()

        assert len(actual_df) > 0, "No supplier performance data returned"
        assert "supplier" in response.lower(), (
            f"Response doesn't mention suppliers: {response}"
        )
        assert "revenue" in response.lower(), (
            f"Response doesn't show revenue: {response}"
        )

    @pytest.mark.asyncio
    async def test_customer_segmentation_analysis(self, chat_client):
        """Test advanced customer segmentation with CASE statements."""
        query = """
        Segment customers based on their total spending:
        - High Value: > $1000
        - Medium Value: $500 - $1000  
        - Low Value: < $500
        
        Show for each segment:
        - Segment name
        - Number of customers
        - Total revenue from segment
        - Average spending per customer
        Order by total revenue descending.
        """

        response = await chat_client.process_query(query)

        # Verify segmentation
        conn = sqlite3.connect(self.temp_database)
        actual_df = pd.read_sql_query(
            """
            SELECT 
                CASE 
                    WHEN total_spent > 1000 THEN 'High Value'
                    WHEN total_spent >= 500 THEN 'Medium Value'
                    ELSE 'Low Value'
                END as segment,
                COUNT(*) as customer_count,
                SUM(total_spent) as total_revenue,
                AVG(total_spent) as avg_spending
            FROM (
                SELECT 
                    c.customer_id,
                    SUM(o.total_amount) as total_spent
                FROM customers c
                JOIN orders o ON c.customer_id = o.customer_id
                GROUP BY c.customer_id
            ) customer_totals
            GROUP BY segment
            ORDER BY total_revenue DESC
        """,
            conn,
        )
        conn.close()

        assert len(actual_df) > 0, "No segmentation data returned"
        assert "segment" in response.lower() or "value" in response.lower(), (
            f"Response doesn't show segmentation: {response}"
        )

    @pytest.mark.asyncio
    async def test_inventory_and_sales_correlation(self, chat_client):
        """Test query analyzing relationship between inventory and sales."""
        query = """
        Analyze the relationship between current stock levels and sales performance:
        - Product name and category
        - Current stock quantity
        - Total quantity sold
        - Revenue generated
        - Stock turnover ratio (sold/stock)
        
        Only show products that have been sold.
        Order by stock turnover ratio descending to see best-performing products.
        """

        response = await chat_client.process_query(query)

        conn = sqlite3.connect(self.temp_database)
        actual_df = pd.read_sql_query(
            """
            SELECT 
                p.name as product_name,
                p.category,
                p.stock_quantity,
                SUM(oi.quantity) as total_sold,
                SUM(oi.total_price) as revenue,
                CAST(SUM(oi.quantity) AS FLOAT) / p.stock_quantity as turnover_ratio
            FROM products p
            JOIN order_items oi ON p.product_id = oi.product_id
            GROUP BY p.product_id, p.name, p.category, p.stock_quantity
            ORDER BY turnover_ratio DESC
        """,
            conn,
        )
        conn.close()

        assert len(actual_df) > 0, "No inventory analysis data returned"
        assert "stock" in response.lower(), (
            f"Response doesn't mention stock: {response}"
        )
        assert "turnover" in response.lower() or "ratio" in response.lower(), (
            f"Response doesn't show turnover analysis: {response}"
        )
