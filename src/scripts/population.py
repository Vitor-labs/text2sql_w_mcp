import sqlite3

conn = sqlite3.connect("./database.db")
cursor = conn.cursor()

# Cria tabela
cursor.execute("""
CREATE TABLE IF NOT EXISTS alunos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    idade INTEGER,
    curso TEXT
)
""")

# Insere alguns dados
cursor.executemany(
    "INSERT INTO alunos (nome, idade, curso) VALUES (?, ?, ?)",
    [
        ("Moniere", 21, "Engenharia de Software")
    ]
)

conn.commit()
conn.close()
print("Banco populado com sucesso!")