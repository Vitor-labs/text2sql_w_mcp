# src/client/processors.py
import re

from client.interfaces import MessageProcessor, ToolExecutor
from config.logger import logger


class SchemaRequestProcessor(MessageProcessor):
    """Handles database schema requests."""

    async def can_handle(self, message: str) -> bool:
        """Check if message requests schema information."""
        return "GET_SCHEMA" in message.upper()

    async def process(self, message: str, tool_executor: ToolExecutor) -> str:
        """Process schema request and return formatted schema."""
        try:
            logger.info("Processing schema request")
            return f"Database Schema:\n{await tool_executor.execute_tool('get_schema', {})}"
        except Exception as e:
            logger.error(f"Error processing schema request: {e}")
            return f"Error retrieving schema: {str(e)}"


class SqlQueryProcessor(MessageProcessor):
    """Handles SQL query execution requests."""

    SQL_PATTERN = re.compile(r"EXECUTE_SQL:\s*(.+?)(?:\n|$)", re.IGNORECASE | re.DOTALL)

    async def can_handle(self, message: str) -> bool:
        """Check if message contains SQL execution request."""
        return bool(self.SQL_PATTERN.search(message))

    async def process(self, message: str, tool_executor: ToolExecutor) -> str:
        """Extract and execute SQL query."""
        try:
            if not (match := self.SQL_PATTERN.search(message)):
                return "No valid SQL query found"

            sql_query = match.group(1).strip()
            logger.info(f"Executing SQL: {sql_query}")
            return f"SQL Query Result:\n{await tool_executor.execute_tool('query_data', {'sql': sql_query})}"

        except Exception as e:
            logger.error(f"Error processing SQL query: {e}")
            return f"Error executing SQL: {str(e)}"


class TableAnalysisProcessor(MessageProcessor):
    """Handles table analysis requests."""

    ANALYSIS_PATTERN = re.compile(r"ANALYZE_TABLE:\s*(\w+)", re.IGNORECASE)

    async def can_handle(self, message: str) -> bool:
        """Check if message requests table analysis."""
        return bool(self.ANALYSIS_PATTERN.search(message))

    async def process(self, message: str, tool_executor: ToolExecutor) -> str:
        """Extract table name and perform analysis."""
        try:
            if not (match := self.ANALYSIS_PATTERN.search(message)):
                return "No valid table name found"

            table_name = match.group(1).strip()
            logger.info(f"Analyzing table: {table_name}")

            return f"Table Analysis:\n{
                await tool_executor.execute_tool(
                    'analyze_table', {'table_name': table_name}
                )
            }"

        except Exception as e:
            logger.error(f"Error analyzing table: {e}")
            return f"Error analyzing table: {str(e)}"
