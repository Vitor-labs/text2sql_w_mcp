# Exemplo para scripts/embed_schema.py
import sqlite3

# Carregar variáveis de ambiente (GOOGLE_API_KEY)
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()


def get_schema_description(conn) -> list[str]:
    """Extrai os comandos CREATE TABLE do banco de dados SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
    return [f"Tabela '{name}':\n{sql}" for name, sql in cursor.fetchall() if sql]


# Conecta ao banco de dados
conn = sqlite3.connect("./database.db")
schema_description = get_schema_description(conn)
conn.close()

# Cria e salva o Vector Store
vector_store = FAISS.from_texts(
    texts=schema_description,
    embedding=GoogleGenerativeAIEmbeddings(model="models/embedding-001"),
)
vector_store.save_local("faiss_index_schema")

print("✅ Vector Store do schema criado e salvo em 'faiss_index_schema'")
