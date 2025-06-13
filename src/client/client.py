from dataclasses import dataclass, field
from typing import Any, Dict, List

from google.genai.types import Content, Part
from mcp import ClientSession
from mcp.client.stdio import stdio_client


@dataclass
class Chat:
    """
    Classe responsável por manter o histórico de mensagens e
    processar queries, usando um genai_client e o server_params injetados.
    """

    genai_client: Any  # Será o genai.Client (instanciado lá fora)
    server_params: Any  # Será um StdioServerParameters (passado de fora)
    messages: List[Dict[str, str]] = field(
        default_factory=lambda: [
            {
                "author": "system",
                "content": (
                    "You are a analyst assistant, master in SQL. Your job is to trans"
                    + "late natural language to SQL statements and execute those quer"
                    + "ies (via external tools) and provide the results back to the u"
                    + "ser in natural language and markdown tables if asked."
                ),
            }
        ]
    )

    async def process_query(self, session: ClientSession, query: str) -> None:
        """
        1) Adiciona a mensagem do usuário no histórico (self.messages).
        2) Converte self.messages em uma lista de Content e chama genai_client.
        3) Armazena a resposta (assistant_text) em self.messages.
        """
        self.messages.append({"author": "user", "content": query})

        content_list: list[Content] = []
        for msg in self.messages:
            if msg["author"] == "system":
                content_list.append(
                    Content(role="user", parts=[Part.from_text(text=msg["content"])])
                )
            elif msg["author"] == "user":
                content_list.append(
                    Content(role="user", parts=[Part.from_text(text=msg["content"])])
                )
            elif msg["author"] == "assistant":
                content_list.append(
                    Content(role="model", parts=[Part.from_text(text=msg["content"])])
                )
            else:
                content_list.append(
                    Content(role="user", parts=[Part.from_text(text=msg["content"])])
                )

        self.messages.append(
            {
                "author": "assistant",
                "content": (
                    assistant_text := self.genai_client.models.generate_content(
                        model="gemini-2.0-flash", contents=content_list
                    ).text
                ),
            }
        )
        return assistant_text

    async def chat_loop(self, session: ClientSession) -> None:
        while True:
            if not (query := input("\nQuery: ").strip()):
                continue
            await self.process_query(session, query)

    async def run(self) -> None:
        """
        Abre o stdio_client usando server_params e executa chat_loop.
        """
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await self.chat_loop(session)
