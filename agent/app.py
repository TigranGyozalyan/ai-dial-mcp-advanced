import asyncio
import json
import os

from agent.clients.custom_mcp_client import CustomMCPClient
from agent.clients.mcp_client import MCPClient
from agent.clients.dial_client import DialClient
from agent.models.message import Message, Role

DIAL_URL = 'https://ai-proxy.lab.epam.com'
API_KEY = os.environ.get('API_KEY', '')
SYSTEM_PROMPT = """
You are an LLM assistant that provides user with information based on their requests.

You have MCP tools available to you, use them as necessary for providing additional context or performing actions.
"""

async def create_dial_client(clients: list[CustomMCPClient | MCPClient]) -> DialClient:
    tools = []
    tools_name_client_map = {}
    for client in clients:
        client_tools = await client.get_tools()
        for client_tool in client_tools:
            tools_name_client_map[client_tool['name']] = client
            tools.append(client_tools)
    return DialClient(endpoint=DIAL_URL, tools=tools, tool_name_client_map=tools_name_client_map, api_key=API_KEY)

async def main():
    print('initializing mcp clients...')
    ums_mcp_client = await CustomMCPClient.create(mcp_server_url='http://localhost:8006/mcp')
    remote_mcp_client = await MCPClient.create(mcp_server_url='https://remote.mcpservers.org/fetch/mcp')
    print('initializing dial client...')
    dial_client = await create_dial_client(clients=[ums_mcp_client, remote_mcp_client])

    messages = [
        Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)
    ]
    print('What can help you with today?')
    while True:
        user_input = input('-> ')
        if user_input == 'exit':
            break
        messages.append(Message(role=Role.USER, content=user_input))
        reply = await dial_client.get_completion(messages)
        messages.append(reply)
    #TODO:
    # 1. Take a look what applies DialClient
    # 2. Create empty list where you save tools from MCP Servers later
    # 3. Create empty dict where where key is str (tool name) and value is instance of MCPClient or CustomMCPClient
    # 4. Create UMS MCPClient, url is `http://localhost:8006/mcp` (use static method create and don't forget that its async)
    # 5. Collect tools and dict [tool name, mcp client]
    # 6. Do steps 4 and 5 for `https://remote.mcpservers.org/fetch/mcp`
    # 7. Create DialClient, endpoint is `https://ai-proxy.lab.epam.com`
    # 8. Create array with Messages and add there System message with simple instructions for LLM that it should help to handle user request
    # 9. Create simple console chat (as we done in previous tasks)

if __name__ == "__main__":
    asyncio.run(main())


# Check if Arkadiy Dobkin present as a user, if not then search info about him in the web and add him
