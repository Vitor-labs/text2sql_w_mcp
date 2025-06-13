# Exemplo para scripts/embed_schema.py
import sqlite3
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# Carregar variáveis de ambiente (GOOGLE_API_KEY)
from dotenv import load_dotenv
load_dotenv()

def get_schema_description(conn):
    """Extrai os comandos CREATE TABLE do banco de dados SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
    schema_docs = []
    for name, sql in cursor.fetchall():
        if sql:
            schema_docs.append(f"Tabela '{name}':\n{sql}")
    return schema_docs

# Conecta ao banco de dados
conn = sqlite3.connect("./database.db")
schema_description = get_schema_description(conn)
conn.close()

# Cria o gerador de embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# Cria e salva o Vector Store
vector_store = FAISS.from_texts(texts=schema_description, embedding=embeddings)
vector_store.save_local("faiss_index_schema")

print("✅ Vector Store do schema criado e salvo em 'faiss_index_schema'")