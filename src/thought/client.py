from typing import Any

from notion_client import Client as NotionClient

from thought.settings import NOTION_ACCESS_TOKEN


class NotionAPIClient:
    """
    Notion API Client wrapper
    """

    def __init__(self) -> None:
        """
        Used for initializing a Notion API client
        """
        self.client: NotionClient | None = None
        if self.client is None:
            self.client = self.get_client(NOTION_ACCESS_TOKEN)

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        """
        Sends a query to the Notion API
        """
        assert self.client is not None
        result = self.client.databases.query(**query)
        assert isinstance(result, dict)
        return result

    def get_client(self, token: str | None) -> NotionClient:
        """
        Returns an official Notion API Client
        """
        if token is None:
            raise ValueError("Notion access token is required")
        return NotionClient(auth=token)

    def search_users(self, search_term: str | None = None) -> list[dict[str, Any]]:
        """
        Search for users in the workspace
        """
        assert self.client is not None
        users = self.client.users.list()
        all_users = users.get("results", [])

        if search_term is None:
            return all_users

        search_lower = search_term.lower()
        filtered_users = []

        for user in all_users:
            name = user.get("name", "").lower()
            email = (
                user.get("person", {}).get("email", "").lower()
                if user.get("person")
                else ""
            )

            if search_lower in name or search_lower in email:
                filtered_users.append(user)

        return filtered_users

    def get_user_by_name_or_email(self, identifier: str) -> dict[str, Any] | None:
        """
        Get a user by name or email
        """
        users = self.search_users(identifier)

        for user in users:
            name = user.get("name", "").lower()
            email = (
                user.get("person", {}).get("email", "").lower()
                if user.get("person")
                else ""
            )
            identifier_lower = identifier.lower()

            if identifier_lower in (name, email):
                return user

        return None
