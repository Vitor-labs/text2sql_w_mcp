import sqlite3

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQL Agent Server")


@mcp.tool()
def query_data(sql: str) -> str:
    """
    Execute a SQL query and return the result.

    Params:
        sql (str): The SQL query to execute

    Returns:
        str: the result of the query as a string
    """
    # logger.info(f"Executing SQL query: {sql}")
    print(f"Executing SQL query: {sql}")
    with sqlite3.connect("./database.db") as conn:
        try:
            result = conn.execute(sql).fetchall()
            conn.commit()
            return "\n".join(str(row) for row in result)
        except Exception as e:
            print(f"Erro ao executar SQL: {e}")
            return f"Error: {str(e)}"


if __name__ == "__main__":
    # Ao rodar “python src/main/server.py”, entramos aqui e iniciamos o MCP via stdio.
    mcp.run(transport="stdio")
