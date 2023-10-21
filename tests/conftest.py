import pytest

from thought.client import NotionAPIClient


@pytest.fixture(name="notion_api_client")
def notion_api_client() -> NotionAPIClient:
    """
    Actual instance of the local BigQueryClient class
    """
    return NotionAPIClient()


@pytest.fixture()
def notion_api_client_client(
    notion_api_client: NotionAPIClient,
) -> NotionAPIClient.client:
    """
    Fixture: BigQueryClient.client
    """
    return notion_api_client.client
