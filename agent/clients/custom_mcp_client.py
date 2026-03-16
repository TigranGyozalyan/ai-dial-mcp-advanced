import json
import uuid
from typing import Optional, Any
import aiohttp

MCP_SESSION_ID_HEADER = "Mcp-Session-Id"
request_id = 0

def get_request_id() -> int:
    """Get request id"""
    global request_id
    request_id += 1
    return request_id

class CustomMCPClient:
    """Pure Python MCP client without external MCP libraries"""

    def __init__(self, mcp_server_url: str) -> None:
        self.server_url = mcp_server_url
        self.session_id: Optional[str] = None
        self.http_session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def create(cls, mcp_server_url: str) -> 'CustomMCPClient':
        """Async factory method to create and connect CustomMCPClient"""
        instance = cls(mcp_server_url)
        await instance.connect()
        return instance

    async def _send_request(self, method: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Send JSON-RPC request to MCP server"""
        if self.http_session is None:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
        if method not in ['initialize']:
            headers[MCP_SESSION_ID_HEADER] = self.session_id

        request_body = {
            'jsonrpc': '2.0',
            'method': method,
            'id': get_request_id(),
        }
        if params:
            request_body['params'] = params

        async with self.http_session.post(url=self.server_url, headers=headers, json=request_body) as response:
            if not self.session_id and response.headers.get(MCP_SESSION_ID_HEADER):
                self.session_id = response.headers[MCP_SESSION_ID_HEADER]

            if response.status == 202:
                return {}

            content_type = response.headers.get('Content-Type')
            if 'text/event-stream' in content_type.lower():
                response_data = await self._parse_sse_response_streaming(response)
            else:
                response_data = await response.json()
            if not response_data:
                response_data = {}
            if "error" in response_data:
                error = response_data["error"]
                raise RuntimeError(f"MCP Error {error['code']}: {error['message']}")

            return response_data

    async def _parse_sse_response_streaming(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        """Parse Server-Sent Events response with streaming"""
        async for line in response.content:
            line_str = line.decode('utf-8').strip()

            if not line_str or line_str.startswith(':'):
                continue

            if line_str.startswith('data: '):
                data_part = line_str[6:].strip()

                if data_part in ('[DONE]', ''):
                    continue

                try:
                    return json.loads(data_part)
                except json.JSONDecodeError:
                    continue

        raise RuntimeError("No valid JSON data found in SSE stream")

    async def connect(self) -> None:
        """Connect to MCP server and initialize session"""
        http_timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        self.http_session = aiohttp.ClientSession(timeout=http_timeout, connector=connector)

        try:
            init_params = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "my-custom-mcp-client", "version": "1.0.0"}
            }
            response = await self._send_request('initialize', init_params)
            await self._send_notification('notifications/initialized')
            print(json.dumps(response, indent=2))
        except Exception as e:
            raise RuntimeError(f"Failed to connect to MCP server: {e}")

    async def _send_notification(self, method: str) -> None:
        """Send notification (no response expected)"""
        if self.http_session is None:
            raise RuntimeError("HTTP session not initialized")

        request_data = {
            "jsonrpc": "2.0",
            "method": method,
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
        }

        if self.session_id:
            headers[MCP_SESSION_ID_HEADER] = self.session_id
        async with self.http_session.post(url=self.server_url, headers=headers, json=request_data) as response:
            if response.status == 400:
                error = await response.json()
                print(f"request failed with {response.status}: {error}")
            if MCP_SESSION_ID_HEADER in response.headers:
                self.session_id = response.headers[MCP_SESSION_ID_HEADER]
                print(f" setting session_id: {self.session_id}")

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if self.http_session is None:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        print(f"    listing available tools...")
        response = await self._send_request('tools/list')

        return [{
            'type': 'function',
            'function': {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.inputSchmea
            }
        }
            for tool in response["result"]["tools"]
        ]

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server"""
        if self.http_session is None:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        print(f"    Calling `{tool_name}` with {tool_args}")
        params = {
            'name': tool_name,
            'arguments': tool_args
        }
        response = await self._send_request("tools/call", params)

        if content := response["result"].get("content", []):
            if item := content[0]:
                text_result = item.get('text', '')
                print(f"    ⚙️: {text_result}\n")
                return text_result
        return "Unexpected error occurred!"
