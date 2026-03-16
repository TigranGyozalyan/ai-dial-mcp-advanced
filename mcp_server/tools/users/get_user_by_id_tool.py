from typing import Any

from mcp_server.tools.users.base import BaseUserServiceTool


class GetUserByIdTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        return 'get_user_by_id'

    @property
    def description(self) -> str:
        return 'get user information based on their ID'

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "number",
                    "description": "ID of the user to get"
                }
            },
            "required": [
                "id"
            ]
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        user_id = int(arguments['id'])
        return await self._user_client.get_user(user_id)
