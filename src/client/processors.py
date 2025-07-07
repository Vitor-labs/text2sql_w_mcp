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


# Em src/client/processors.py

class SqlQueryProcessor(MessageProcessor):
    """Handles SQL query execution requests."""

    # Expressão regular atualizada para detetar o comando EXECUTE_SQL: OU um bloco de código SQL.
    SQL_PATTERN = re.compile(
        r"EXECUTE_SQL:\s*(.+?)(?:\n|$)|```sql\n(.+?)\n```",
        re.IGNORECASE | re.DOTALL
    )

    async def can_handle(self, message: str) -> bool:
        """Verifica se a mensagem contém um pedido de execução de SQL em qualquer formato."""
        return bool(self.SQL_PATTERN.search(message))

    async def process(self, message: str, tool_executor: ToolExecutor) -> str:
        """Extrai e executa a consulta SQL de qualquer um dos formatos."""
        try:
            match = self.SQL_PATTERN.search(message)
            if not match:
                return "Nenhuma consulta SQL válida encontrada para execução."

            # O resultado da nossa expressão regular terá dois grupos.
            # Usamos o que não for nulo, que será a nossa consulta SQL.
            sql_query = (match.group(1) or match.group(2)).strip()
            
            logger.info(f"Executando SQL: {sql_query}")
            
            # Executa a ferramenta e retorna DIRETAMENTE o resultado, sem reinterpretação.
            tool_result = await tool_executor.execute_tool('query_data', {'sql': sql_query})
            return f"SQL Query Result:\n{tool_result}"

        except Exception as e:
            logger.error(f"Erro ao processar a consulta SQL: {e}")
            return f"Erro ao executar SQL: {str(e)}"


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
