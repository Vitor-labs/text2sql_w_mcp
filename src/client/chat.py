# from dataclasses import dataclass, field
# from typing import cast

# import anthropic
# from anthropic.types import (MessageParam, TextBlock, ToolUnionParam,
#                              ToolUseBlock)
# from dotenv import load_dotenv
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client

# load_dotenv()


# anthropic_client = anthropic.AsyncAnthropic()


# # Create server parameters for stdio connection
# server_params = StdioServerParameters(
#     command="python",  # Executable
#     args=["./src/main/server.py"],  # Optional command line arguments
#     env=None,  # Optional environment variables
# )


# @dataclass
# class Chat:
#     messages: list[MessageParam] = field(default_factory=list)

#     system_prompt: str = """
#     You are a master SQLite assistant. 
#     Your job is to use the tools at your dispoal to execute SQL queries and provide the results to the user.
#     """

#     async def process_query(self, session: ClientSession, query: str) -> None:
#         available_tools: list[ToolUnionParam] = [
#             {
#                 "name": tool.name,
#                 "description": tool.description or "",
#                 "input_schema": tool.inputSchema,
#             }
#             for tool in (await session.list_tools()).tools
#         ]

#         assistant_message_content: list[ToolUseBlock | TextBlock] = []
#         # Initial Claude API call
#         res = await anthropic_client.messages.create(
#             model="claude-3-5-sonnet-latest",
#             system=self.system_prompt,
#             max_tokens=8000,
#             messages=self.messages,
#             tools=available_tools,
#         )

#         for content in res.content:
#             if content.type == "text":
#                 assistant_message_content.append(content)
#                 print(content.text)

#             elif content.type == "tool_use":
#                 tool_name = content.name
#                 tool_args = content.input

#                 # Execute tool call
#                 result = await session.call_tool(tool_name, cast(dict, tool_args))
#                 assistant_message_content.append(content)

#                 self.messages.append(
#                     {"role": "assistant", "content": assistant_message_content}
#                 )
#                 self.messages.append(
#                     {
#                         "role": "user",
#                         "content": [
#                             {
#                                 "type": "tool_result",
#                                 "tool_use_id": content.id,
#                                 "content": getattr(result.content[0], "text", ""),
#                             }
#                         ],
#                     }
#                 )
#                 # Get next response from Claude
#                 res = await anthropic_client.messages.create(
#                     model="claude-3-7-sonnet-latest",
#                     max_tokens=8000,
#                     messages=self.messages,
#                     tools=available_tools,
#                 )
#                 self.messages.append(
#                     {
#                         "role": "assistant",
#                         "content": getattr(res.content[0], "text", ""),
#                     }
#                 )
#                 print(getattr(res.content[0], "text", ""))

#     async def chat_loop(self, session: ClientSession) -> None:
#         # logger.info("Starting chat loop...")
#         while True:
#             query = input("\nQuery: ").strip()
#             self.messages.append(MessageParam(role="user", content=query))
#             await self.process_query(session, query)

#     async def run(self):
#         async with stdio_client(server_params) as (read, write):
#             async with ClientSession(read, write) as session:
#                 await session.initialize()
#                 await self.chat_loop(session)

# src/client/client.py

# chat.py

from dataclasses import dataclass, field
from typing import Any, Dict, List

from google.genai import types
from mcp import ClientSession


@dataclass
class Chat:
    """
    Classe responsável por manter o histórico de mensagens e
    processar queries, usando um genai_client e o server_params injetados.
    """
    genai_client: Any                    # Será o genai.Client (instanciado lá fora)
    server_params: Any                   # Será um StdioServerParameters (passado de fora)
    messages: List[Dict[str, str]] = field(
        default_factory=lambda: [
            {
                "author": "system",
                "content": (
                    "You are a master SQLite assistant. "
                    "Your job is to execute SQL queries (via ferramentas externas) "
                    "and provide the results back to the user."
                ),
            }
        ]
    )

    async def process_query(self, session: ClientSession, query: str) -> None:
        """
        1) Adiciona a mensagem do usuário no histórico (self.messages).
        2) Converte self.messages em uma lista de types.Content e chama genai_client.
        3) Armazena a resposta (assistant_text) em self.messages.
        """
        self.messages.append({"author": "user", "content": query})

        content_list: List[types.Content] = []
        for msg in self.messages:
            role = msg["author"]
            texto = msg["content"]

            if role == "system":
                content_list.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=texto)]
                    )
                )
            elif role == "user":
                content_list.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=texto)]
                    )
                )
            elif role == "assistant":
                content_list.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=texto)]
                    )
                )
            else:
                content_list.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=texto)]
                    )
                )

        response = self.genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=content_list,
        )

        assistant_text = response.text
        self.messages.append({"author": "assistant", "content": assistant_text})

        return assistant_text

    async def chat_loop(self, session: ClientSession) -> None:
        while True:
            query = input("\nQuery: ").strip()
            if not query:
                continue
            await self.process_query(session, query)

    async def run(self) -> None:
        """
        Abre o stdio_client usando server_params e executa chat_loop.
        """
        from mcp.client.stdio import stdio_client 
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await self.chat_loop(session)
