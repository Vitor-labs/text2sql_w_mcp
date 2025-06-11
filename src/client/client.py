#src/client/client.py
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool as CoreTool
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import (ChatGoogleGenerativeAI,
                                    GoogleGenerativeAIEmbeddings)
from mcp import ClientSession


@dataclass
class Chat:
    """
    Classe refatorada para orquestrar um agente Text2SQL com LangChain, HyDE e MCP.
    VERSÃO TOTALMENTE ASSÍNCRONA.
    """
    genai_client: Any
    server_params: Any
    mcp_session: ClientSession = field(init=False)
    vector_store: FAISS = field(init=False, default=None)
    llm: ChatGoogleGenerativeAI = field(init=False)
    agent_executor: AgentExecutor = field(init=False)
    
    def __post_init__(self):
        """Inicializa componentes após a criação da instância."""
        if not os.path.exists("faiss_index_schema"):
            raise FileNotFoundError("O diretório 'faiss_index_schema' não foi encontrado. Execute 'python scripts/embed_schema.py' primeiro.")
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        #self.vector_store = FAISS.load_local("faiss_index_schema", embeddings, allow_dangerous_deserialization=True)
        # Garantindo que o nome do modelo está correto
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    def _get_current_schema(self, db_path="./database.db") -> str:
        """Obtém o schema atual do banco SQLite."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            schemas = [row[0] for row in cursor.fetchall() if row[0]]
        return "\n".join(schemas)
    
    def _build_faiss_index_from_schema(self, schema_str: str):
        """Gera o índice FAISS do schema em tempo real."""
        docs = [Document(page_content=schema_str)]
        return FAISS.from_documents(docs, self.embeddings)

    def setup_agent(self, session: ClientSession):
        """Configura o agente LangChain com a sessão MCP ativa."""
        self.mcp_session = session

        # Flag para evitar execução repetida da mesma query
        self._last_executed_sql = None

        async def _arun_sql_query_tool(sql: str) -> str:
            """Executa uma query SQL de forma assíncrona no banco de dados remoto via MCP."""
            print(f"DEBUG: Executando a corotina da ferramenta com SQL: {sql}")
            # Previne execução repetida da mesma query (loop)
            if self._last_executed_sql == sql.strip():
                return "A mesma query já foi executada. Evitando repetição."
            self._last_executed_sql = sql.strip()
            try:
                result = await self.mcp_session.call_tool("query_data", {"sql": sql})
                if result and result.content and hasattr(result.content[0], "text"):
                    return result.content[0].text
                return "Comando SQL executado com sucesso."
            except Exception as e:
                return f"Erro ao executar a query via MCP: {e}"

        mcp_sql_tool = CoreTool(
            name="sql_executor",
            func=None,
            coroutine=_arun_sql_query_tool,
            description="Útil para executar consultas SQL e obter resultados do banco de dados. Input deve ser uma query SQL válida."
        )
        tools = [mcp_sql_tool]

        prompt_template = """Você é um assistente especialista em SQL. Sua tarefa é converter perguntas em linguagem natural para queries SQL e executá-las.

        Com base na pergunta do usuário e no schema do banco de dados fornecido, gere e execute a query SQL correta.
        Responda ao usuário em português com base nos resultados da query.

        **Schema do Banco de Dados Relevante:**
        {retrieved_schema}

        **Histórico da Conversa:**
        {chat_history}

        **Pergunta do Usuário:**
        {input}

        **Instruções para o Agente:**
        {agent_scratchpad}

        IMPORTANTE: Execute cada comando SQL apenas uma vez. NÃO repita a execução da mesma query, mesmo que solicitado novamente.
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)
        agent = create_tool_calling_agent(self.llm, tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,  # Ajuda a evitar erros de parsing
        )

    # MUDANÇA 1: Transformar a função HyDE em uma corotina (async def)
    async def _get_hypothetical_query(self, query: str) -> str:
        """Gera uma query SQL hipotética (HyDE) de forma assíncrona."""
        hyde_prompt = ChatPromptTemplate.from_template(
            "Dado a pergunta do usuário, gere uma query SQL para SQLite que provavelmente responderia a essa pergunta. "
            "Seja conciso. Pergunta: {query}"
        )
        hyde_chain = hyde_prompt | self.llm
        # Usar ainvoke para a chamada assíncrona
        response = await hyde_chain.ainvoke({"query": query})
        return response.content

    async def process_query(self, session: ClientSession, query: str) -> str:
        """
        Processa a query do usuário usando o fluxo completo com HyDE e o agente LangChain.
        """
        # self.setup_agent(session)
        # hypothetical_query = await self._get_hypothetical_query(query)
        # retriever = self.vector_store.as_retriever()
        # relevant_schema_docs = retriever.invoke(hypothetical_query)
        # retrieved_schema = "\n\n".join([doc.page_content for doc in relevant_schema_docs])
        
        self.setup_agent(session)
        hypothetical_query = await self._get_hypothetical_query(query)

        # ATUALIZE o vector_store com o schema atual do banco
        schema_str = self._get_current_schema()
        self.vector_store = self._build_faiss_index_from_schema(schema_str)

        retriever = self.vector_store.as_retriever()
        relevant_schema_docs = retriever.invoke(hypothetical_query)
        retrieved_schema = "\n\n".join([doc.page_content for doc in relevant_schema_docs])

        try:
            response = await self.agent_executor.ainvoke({
                "input": query,
                "retrieved_schema": retrieved_schema,
                "chat_history": [] 
            })
            return response["output"]
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            error_message = f"Desculpe, houve um erro ao processar sua solicitação no agente: {e}\n{tb}"
            print(error_message)
            return error_message