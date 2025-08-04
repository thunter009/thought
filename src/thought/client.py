import time
from typing import Any

from notion_client import Client as NotionClient

from thought.logging_utils import get_logger, log_api_call
from thought.settings import NOTION_ACCESS_TOKEN


class NotionAPIClient:
    """
    Notion API Client wrapper
    """

    def __init__(self) -> None:
        """
        Used for initializing a Notion API client
        """
        self.logger = get_logger(__name__)
        self.client: NotionClient | None = None
        if self.client is None:
            self.client = self.get_client(NOTION_ACCESS_TOKEN)
            self.logger.debug("Notion API client initialized")

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        """
        Sends a query to the Notion API
        """
        assert self.client is not None

        start_time = time.time()
        database_id = query.get("database_id", "unknown")

        try:
            self.logger.debug(f"Querying database | database_id={database_id}")
            result = self.client.databases.query(**query)
            duration = time.time() - start_time

            # Log success before validation
            if isinstance(result, dict):
                result_count = len(result.get("results", []))
                self.logger.info(
                    f"Database query successful | database_id={database_id} | "
                    f"results={result_count} | duration={duration:.3f}s"
                )
            else:
                self.logger.info(
                    f"Database query completed | database_id={database_id} | "
                    f"duration={duration:.3f}s"
                )

            log_api_call(
                self.logger,
                "POST",
                f"databases/{database_id}/query",
                params={"filter": query.get("filter"), "sort": query.get("sort")},
                response_status=200,
                duration=duration,
            )

            assert isinstance(result, dict)
            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Database query failed | database_id={database_id} | "
                f"error={e} | duration={duration:.3f}s"
            )

            log_api_call(
                self.logger,
                "POST",
                f"databases/{database_id}/query",
                params={"filter": query.get("filter"), "sort": query.get("sort")},
                response_status=None,
                duration=duration,
            )
            raise

    def get_client(self, token: str | None) -> NotionClient:
        """
        Returns an official Notion API Client
        """
        if token is None:
            self.logger.error("Notion access token is missing")
            raise ValueError("Notion access token is required")

        self.logger.debug("Creating Notion API client")
        return NotionClient(auth=token)

    def search_users(self, search_term: str | None = None) -> list[dict[str, Any]]:
        """
        Search for users in the workspace
        """
        assert self.client is not None

        start_time = time.time()

        try:
            self.logger.debug(f"Searching users | search_term={search_term}")
            users = self.client.users.list()
            all_users = users.get("results", [])

            if search_term is None:
                duration = time.time() - start_time
                self.logger.info(
                    f"User search completed | total_users={len(all_users)} | "
                    f"duration={duration:.3f}s"
                )
                log_api_call(
                    self.logger, "GET", "users", response_status=200, duration=duration
                )
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

            duration = time.time() - start_time
            self.logger.info(
                f"User search completed | search_term={search_term} | "
                f"found={len(filtered_users)}/{len(all_users)} | "
                f"duration={duration:.3f}s"
            )
            log_api_call(
                self.logger,
                "GET",
                "users",
                params={"search": search_term},
                response_status=200,
                duration=duration,
            )

            return filtered_users

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"User search failed | search_term={search_term} | "
                f"error={e} | duration={duration:.3f}s"
            )
            log_api_call(
                self.logger,
                "GET",
                "users",
                params={"search": search_term},
                response_status=None,
                duration=duration,
            )
            raise

    def get_user_by_name_or_email(self, identifier: str) -> dict[str, Any] | None:
        """
        Get a user by name or email
        """
        self.logger.debug(f"Looking up user | identifier={identifier}")
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
                self.logger.debug(
                    f"User found | identifier={identifier} | "
                    f"user_id={user.get('id')} | name={user.get('name')}"
                )
                return user

        self.logger.warning(f"User not found | identifier={identifier}")
        return None
