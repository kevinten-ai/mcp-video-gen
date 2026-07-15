import asyncio
import re
import shutil

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ENTRYPOINT = "video-gen"
EXPECTED_TOOLS = ["generate_video","query_video_status","list_providers"]


async def _list_tools():
    command = shutil.which(ENTRYPOINT)
    assert command is not None, f"{ENTRYPOINT} console script is not installed"

    params = StdioServerParameters(command=command)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return (await session.list_tools()).tools


def test_tools_list_contract():
    tools = asyncio.run(_list_tools())
    assert [tool.name for tool in tools] == EXPECTED_TOOLS

    for tool in tools:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", tool.name)
        assert tool.description and tool.description.strip()
        assert tool.inputSchema.get("type") == "object"
        properties = tool.inputSchema.get("properties", {})
        required = tool.inputSchema.get("required", [])
        assert isinstance(properties, dict)
        assert set(required).issubset(properties)

