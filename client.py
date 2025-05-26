import asyncio
from dataclasses import field
from typing import Final, cast

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, TextBlock, ToolUnionParam, ToolUseBlock
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
anthropic_client = AsyncAnthropic()
server_params = StdioServerParameters(
    command="python", args=["./app/server.py"], env=None
)


class Chat:
    messages: list[MessageParam] = field(default_factory=list)
    system_prompt: Final[str] = (
        "You are a master SQLite assistant. Your job is to use the tools at "
        + "your disposal to execute SQL queries and provide the results to t"
        + "he user."
    )

    async def process_query(self, session: ClientSession, query: str) -> None:
        available_tools: list[ToolUnionParam] = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            for tool in (await session.list_tools()).tools
        ]
        response = await anthropic_client.messages.create(
            model="claude-3-7-sonnet-latest",
            system=self.system_prompt,
            max_tokens=8000,
            messages=self.messages,
            tools=available_tools,
        )

        assistant_message_content: list[ToolUseBlock | TextBlock] = []
        for content in response.content:
            if content.type == "text":
                assistant_message_content.append(content)
                print(content.text)

            elif content.type == "tool_use":
                result = await session.call_tool(
                    content.name, cast(dict, content.input)
                )
                assistant_message_content.append(content)
                self.messages.append(
                    {"role": "assistant", "content": assistant_message_content}
                )
                self.messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": getattr(result.content[0], "text", ""),
                            }
                        ],
                    }
                )
                res = await anthropic_client.messages.create(
                    model="claude-3-7-sonnet-latest",
                    max_tokens=8000,
                    messages=self.messages,
                    tools=available_tools,
                )
                self.messages.append(
                    {
                        "role": "assistant",
                        "content": getattr(res.content[0], "text", ""),
                    }
                )
                print(getattr(res.content[0], "text", ""))

    async def chat_loop(self, session: ClientSession):
        while True:
            query = input("\nQuery: ").strip()
            self.messages.append(MessageParam(role="user", content=query))
            await self.process_query(session, query)

    async def run(self):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await self.chat_loop(session)


chat = Chat()
asyncio.run(chat.run())
