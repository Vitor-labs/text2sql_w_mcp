# src/main/server.py
import logging
import sqlite3
import sys
import traceback
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mcp = FastMCP("SQL Agent Server")

# Database configuration
DB_PATH = Path("./database.db")


def ensure_database_exists() -> bool:
    """Ensure database file exists and is accessible"""
    try:
        if not DB_PATH.exists():
            logger.warning(f"Database file {DB_PATH} does not exist. Creating...")
            # Create empty database with a sample table
            with sqlite3.connect(DB_PATH) as conn:
                # Create a sample table for demonstration
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sample_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE,
                        age INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Insert some sample data
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO sample_data (name, email, age) VALUES (?, ?, ?)
                """,
                    [
                        ("John Doe", "john@example.com", 30),
                        ("Jane Smith", "jane@example.com", 25),
                        ("Bob Johnson", "bob@example.com", 35),
                        ("Alice Brown", "alice@example.com", 28),
                        ("Charlie Wilson", "charlie@example.com", 42),
                    ],
                )
                conn.commit()
                logger.info("Created sample database with demo data")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


@mcp.tool()
def query_data(sql: str) -> str:
    """
    Execute a SQL query and return the result in a formatted way.

    Args:
        sql (str): The SQL query to execute

    Returns:
        str: Formatted query results or error message
    """
    try:
        logger.info(f"Executing SQL query: {sql}")

        if not ensure_database_exists():
            return "Error: Database is not accessible"

        with sqlite3.connect(DB_PATH) as conn:
            # Enable row factory for better output formatting
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Basic security check
            sql_upper = sql.strip().upper()
            if any(
                dangerous in sql_upper
                for dangerous in [
                    "DROP TABLE",
                    "DROP DATABASE",
                    "DELETE FROM sqlite_master",
                ]
            ):
                return "Security Warning: Potentially dangerous operation blocked."

            cursor.execute(sql)

            # Handle different query types
            if sql_upper.startswith(("SELECT", "PRAGMA", "EXPLAIN", "WITH")):
                rows = cursor.fetchall()
                if not rows:
                    return "Query executed successfully. No results returned."

                # Get column names
                columns = list(rows[0].keys())

                # Create formatted table
                result = "| " + " | ".join(columns) + " |\n"
                result += "| " + " | ".join(["---"] * len(columns)) + " |\n"

                for row in rows:
                    formatted_row = []
                    for value in row:
                        if value is None:
                            formatted_row.append("NULL")
                        else:
                            formatted_row.append(str(value))
                    result += "| " + " | ".join(formatted_row) + " |\n"

                return f"Query results ({len(rows)} rows):\n\n{result}"

            else:
                # For INSERT, UPDATE, DELETE, etc.
                conn.commit()
                affected_rows = cursor.rowcount
                return f"Query executed successfully. {affected_rows} rows affected."

    except sqlite3.Error as e:
        error_msg = f"SQL Error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error_msg


@mcp.tool()
def get_schema() -> str:
    """
    Get the database schema information.

    Returns:
        str: Database schema information
    """
    try:
        logger.info("Getting database schema")

        if not ensure_database_exists():
            return "Error: Database is not accessible"

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Get all tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = cursor.fetchall()

            if not tables:
                return "Database is empty (no user tables found)."

            schema_info = "Database Schema:\n\n"

            for (table_name,) in tables:
                schema_info += f"## Table: {table_name}\n"

                # Get column information
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()

                schema_info += "| Column | Type | Not Null | Default | Primary Key |\n"
                schema_info += "|--------|------|----------|---------|-------------|\n"

                for col_info in columns:
                    cid, name, type_, notnull, default, pk = col_info
                    schema_info += f"| {name} | {type_} | {'Yes' if notnull else 'No'} | {default or 'NULL'} | {'Yes' if pk else 'No'} |\n"

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                row_count = cursor.fetchone()[0]
                schema_info += f"\nRows: {row_count}\n\n"

            return schema_info

    except Exception as e:
        error_msg = f"Error getting schema: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error_msg


if __name__ == "__main__":
    try:
        logger.info("Starting SQL Agent MCP Server...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {Path.cwd()}")

        # Test database creation
        if ensure_database_exists():
            logger.info("Database is ready")
        else:
            logger.error("Failed to initialize database")
            sys.exit(1)

        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
