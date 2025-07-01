# src/main/server.py
import logging
import sqlite3
import sys
import traceback
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Não dá pra tirar esse logging daqui, o sistema só aceita esse e não o custom.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mcp = FastMCP("SQL Agent Server")
DB_PATH = Path("./database.db")


def ensure_database_exists() -> bool:
    """Ensure database file exists and is accessible"""
    try:
        if not DB_PATH.exists():
            logger.warning(f"Database file {DB_PATH} does not exist. Creating...")
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sample_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE,
                        age INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
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
            sql_upper = sql.strip().upper()
            cursor.execute(sql)

            # Handle different query types
            if sql_upper.startswith(("SELECT", "PRAGMA", "EXPLAIN", "WITH")):
                if not (rows := cursor.fetchall()):
                    return "Query executed successfully. No results returned."

                columns = list(rows[0].keys())
                result = (
                    "| "
                    + " | ".join(columns)
                    + " |\n| "
                    + " | ".join(["---"] * len(columns))
                    + " |\n"
                )
                for row in rows:
                    result += (
                        "| "
                        + " | ".join(
                            ["NULL" if value is None else str(value) for value in row]
                        )
                        + " |\n"
                    )
                return f"Query results ({len(rows)} rows):\n\n{result}"

            else:  # For INSERT, UPDATE, DELETE, etc.
                conn.commit()
                return f"Query executed successfully. {cursor.rowcount} rows affected."

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
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            if not (tables := cursor.fetchall()):
                return "Database is empty (no user tables found)."

            schema_info = "Database Schema:\n\n"

            for (table_name,) in tables:
                schema_info += f"## Table: {table_name}\n"
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()

                schema_info += "| Column | Type | Not Null | Default | Primary Key |\n"
                schema_info += "|--------|------|----------|---------|-------------|\n"

                for col_info in columns:
                    cid, name, type_, notnull, default, pk = col_info
                    schema_info += f"| {name} | {type_} | {'Yes' if notnull else 'No'} | {default or 'NULL'} | {'Yes' if pk else 'No'} |\n"

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                schema_info += f"\nRows: {cursor.fetchone()[0]}\n\n"

            return schema_info

    except Exception as e:
        error_msg = f"Error getting schema: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error_msg


@mcp.tool()
def analyze_table(table_name: str) -> str:
    """
    Perform detailed analysis of a specific table.

    Args:
        table_name (str): Name of the table to analyze

    Returns:
        str: Detailed table analysis
    """
    try:
        logger.info(f"Analyzing table: {table_name}")

        if not ensure_database_exists():
            return "Error: Database is not accessible"

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (table_name,),
            )
            if not cursor.fetchone():
                return f"Error: Table '{table_name}' does not exist."

            analysis = f"Analysis of Table: {table_name}\n\n"
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            total_rows = cursor.fetchone()[0]
            analysis += f"Total Rows: {total_rows}\n\n"

            if total_rows == 0:
                return analysis + "Table is empty."

            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()

            analysis += "Column Statistics:\n\n"

            for col_info in columns:
                col_name = col_info[1]
                col_type = col_info[2]

                analysis += f"Column: {col_name} ({col_type})\n"
                cursor.execute(  # Count non-null values
                    f"SELECT COUNT({col_name}) FROM {table_name} WHERE {col_name} IS NOT NULL;"
                )
                non_null_count = cursor.fetchone()[0]
                analysis += f"  - Non-null values: {non_null_count}\n"
                analysis += f"  - Null values: {total_rows - non_null_count}\n"

                # For numeric columns, get additional stats
                if col_type.upper() in ["INTEGER", "REAL", "NUMERIC"]:
                    try:
                        cursor.execute(f"""
                            SELECT 
                                MIN({col_name}) as min_val,
                                MAX({col_name}) as max_val,
                                AVG({col_name}) as avg_val
                            FROM {table_name} 
                            WHERE {col_name} IS NOT NULL
                        """)
                        stats = cursor.fetchone()
                        if stats[0] is not None:
                            analysis += f"  - Min: {stats[0]}\n"
                            analysis += f"  - Max: {stats[1]}\n"
                            analysis += f"  - Average: {stats[2]:.2f}\n"
                    except Exception as exc:
                        logger.warning(f"Exception: {exc}")

                analysis += "\n"

            return analysis

    except Exception as e:
        error_msg = f"Error analyzing table: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error_msg


if __name__ == "__main__":
    try:
        logger.info("Starting SQL Agent MCP Server...")
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
