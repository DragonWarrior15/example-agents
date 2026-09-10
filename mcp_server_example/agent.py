"""An Agent to interact with the game."""

import asyncio
from pathlib import Path
import sys

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from opentelemetry import trace
from phoenix.otel import register
from phoenix.otel import SpanAttributes

tracer_provider = register(
    protocol="http/protobuf",
    project_name="game-agent",
    auto_instrument=True,
)
tracer = tracer_provider.get_tracer(__name__)

SERVER_FILE = Path(__file__).with_name("server.py")

chat_model = ChatOllama(model="qwen3.5:9b", base_url="http://localhost:11434")

user_query = "Play the game."

inputs = {
    "messages": [
        {
            "role": "system",
            "content": "You are an expert at playing games.",
        },
        {
            "role": "user",
            "content": user_query,
        },
    ]
}


async def main():

    # build a client for use inside the agent
    client = MultiServerMCPClient(
        {
            "game": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(SERVER_FILE)],
            }
        }
    )



    with tracer.start_as_current_span(
        "game-agent",
        attributes={
            SpanAttributes.OPENINFERENCE_SPAN_KIND: "AGENT",
            SpanAttributes.INPUT_VALUE: user_query,
        },
    ) as agent_span:
        try:
            async with client.session("game") as session:
                tools = await load_mcp_tools(session)
                graph = create_agent(
                    model=chat_model,
                    tools=tools,
                )

                # All LLM calls, tool executions, and embeddings inside here
                # will appear as children of this span
                output = await graph.ainvoke(inputs)

                messages = output.get("messages", [])

                if messages:
                    output_message = messages[-1].content
                    print(output_message)

                # custom trace handling here
                agent_span.set_attribute(
                    SpanAttributes.OUTPUT_VALUE, output_message
                )
                agent_span.set_status(trace.Status(trace.StatusCode.OK))

        except Exception as error:
            agent_span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise


if __name__ == "__main__":
    asyncio.run(main())
