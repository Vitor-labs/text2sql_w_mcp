import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from google.genai import Client
from mcp import StdioServerParameters

from src.client.client import Chat
from src.config.logger import logger


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir():
    """Get the test data directory path."""
    return Path(__file__).parent / "data"


@pytest.fixture
def raw_data_dir(test_data_dir):
    """Get the raw data directory path."""
    return test_data_dir / "raw"


@pytest.fixture
def expected_data_dir(test_data_dir):
    """Get the expected results directory path."""
    return test_data_dir / "expected"


@pytest.fixture
async def temp_database():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create and setup database
        conn = sqlite3.connect(db_path)
        conn.close()
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def genai_client():
    """Create a mock or real GenAI client based on environment."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set in environment")

    return Client(api_key=api_key)


@pytest.fixture
def server_params():
    """Create server parameters for testing."""
    # Adjust path based on your project structure
    server_path = Path(__file__).parent.parent / "src" / "main" / "server.py"
    return StdioServerParameters(command="python", args=[str(server_path)])


@pytest.fixture
async def chat_client(genai_client, server_params):
    """Create a chat client for testing."""
    return Chat(genai_client, server_params)


def load_csv_as_dataframe(csv_path: Path) -> pd.DataFrame:
    """Helper function to load CSV as DataFrame."""
    return pd.read_csv(csv_path)


def compare_dataframes(
    df1: pd.DataFrame, df2: pd.DataFrame, tolerance: float = 0.01
) -> bool:
    """Compare two DataFrames with numerical tolerance."""
    try:
        # Sort both dataframes to ensure consistent ordering
        df1_sorted = df1.sort_values(by=df1.columns.tolist()).reset_index(drop=True)
        df2_sorted = df2.sort_values(by=df2.columns.tolist()).reset_index(drop=True)

        # Check if shapes are equal
        if df1_sorted.shape != df2_sorted.shape:
            return False

        # Compare columns
        if not df1_sorted.columns.equals(df2_sorted.columns):
            return False

        # Compare values with tolerance for numeric columns
        for col in df1_sorted.columns:
            if pd.api.types.is_numeric_dtype(df1_sorted[col]):
                if not df1_sorted[col].equals(df2_sorted[col]):
                    # Check with tolerance
                    diff = abs(df1_sorted[col] - df2_sorted[col])
                    if (diff > tolerance).any():
                        return False
            else:
                if not df1_sorted[col].equals(df2_sorted[col]):
                    return False

        return True
    except Exception as e:
        logger.error(f"Error comparing dataframes: {e}")
        return False
