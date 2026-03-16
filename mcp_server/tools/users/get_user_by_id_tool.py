from typing import Any


from mcp_server.models.user_info import UserUpdate
from mcp_server.tools.users.base import BaseUserServiceTool


class UpdateUserTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        return 'update_user'

    @property
    def description(self) -> str:
        return 'update information of a user with given id with new information from the request'

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "number",
                    "description": "ID of the user to delete"
                },
                "new_info": UserUpdate.model_json_schema()
            },
            "required": [
                "id"
            ]
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        user_id = int(arguments['id'])

        UserUpdate.model_validate(arguments)
        user = UserUpdate(**arguments['new_info'])
        return await self._user_client.update_user(user_id, user)

