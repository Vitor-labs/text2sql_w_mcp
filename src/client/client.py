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

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

server_params = StdioServerParameters(
    command="python",
    args=["./src/main/server.py"],
    env=None,
)

@dataclass
class Chat:
    # Agora guardamos o histórico como lista de dicionários,
    # mas converteremos para types.Content na hora de chamar o SDK.
    messages: list[dict] = field(
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
        # 1) Adiciona a mensagem do usuário ao histórico (como dicionário)
        self.messages.append({"author": "user", "content": query})

               # 2) Converte cada item de self.messages em um types.Content
        content_list: list[types.Content] = []
        for msg in self.messages:
            role = msg["author"]
            texto = msg["content"]

            # Mapeia os papéis para os aceitos pelo Gemini
            if role == "system":
                # Gemini não aceita "system", então tratamos como "user" (prompt inicial)
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
                # Caso tenha outro papel, trate como "user" por padrão
                content_list.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=texto)]
                    )
                )

        # 3) Chama o generate_content com a lista de types.Content
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=content_list,
        )

        # 4) O SDK retorna um objeto cujo .text é a resposta em texto
        assistant_text = response.text
        # 5) Armazena a resposta no histórico (como dicionário para exibição local)
        self.messages.append({"author": "assistant", "content": assistant_text})

        print(assistant_text)

    async def chat_loop(self, session: ClientSession) -> None:
        while True:
            query = input("\nQuery: ").strip()
            if not query:
                continue
            await self.process_query(session, query)

    async def run(self):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await self.chat_loop(session)


if __name__ == "__main__":
    import asyncio

    chat = Chat()
    print("Starting server...")
    asyncio.run(chat.run())
