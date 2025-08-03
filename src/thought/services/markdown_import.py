"""Markdown import service for importing Markdown files to Notion."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from thought.client import NotionAPIClient
from thought.markdown_parser import MarkdownParser, ParsedMarkdown
from thought.notion_converter import NotionBlockConverter
from thought.service import GenericService


@dataclass
class ImportResult:
    """Result of a single file import."""

    file_path: Path
    success: bool
    page_id: str | None = None
    error: str | None = None
    action: str = "created"  # created, updated, skipped


@dataclass
class DirectoryImportOptions:
    """Options for directory import."""

    directory_path: Path
    database_id: str
    recursive: bool = False
    mode: str = "merge"
    identifier: str = "auto"
    dry_run: bool = False
    pattern: str = "*.md"


@dataclass
class BatchImportResult:
    """Result of a batch import operation."""

    total_files: int
    successful: int
    failed: int
    results: list[ImportResult] = field(default_factory=list)

    @property
    def all_successful(self) -> bool:
        return self.failed == 0


@dataclass
class MarkdownImportService(GenericService):
    """Service for importing Markdown files to Notion."""

    _type: str = field(default="markdown_import", init=False)
    client: NotionAPIClient = field(default_factory=NotionAPIClient)
    parser: MarkdownParser = field(default_factory=MarkdownParser)
    converter: NotionBlockConverter = field(default_factory=NotionBlockConverter)

    def import_file(
        self,
        file_path: Path,
        database_id: str,
        mode: str = "merge",
        identifier: str = "auto",
        dry_run: bool = False,
    ) -> ImportResult:
        """Import a single Markdown file to Notion."""
        try:
            # Parse the Markdown file
            parsed = self.parser.parse_file(file_path)

            # Find existing page if updating
            existing_page = self._find_existing_page(parsed, database_id, identifier)

            if dry_run:
                action = "update" if existing_page else "create"
                return ImportResult(
                    file_path=file_path,
                    success=True,
                    page_id=existing_page["id"] if existing_page else None,
                    action=f"would {action}",
                )

            if existing_page:
                # Update existing page
                page_id = self._update_page(existing_page["id"], parsed, mode)
                return ImportResult(
                    file_path=file_path, success=True, page_id=page_id, action="updated"
                )
            else:
                # Create new page
                page_id = self._create_page(database_id, parsed)
                return ImportResult(
                    file_path=file_path, success=True, page_id=page_id, action="created"
                )

        except Exception as e:
            return ImportResult(file_path=file_path, success=False, error=str(e))

    def import_directory(  # noqa: PLR0913
        self,
        directory_path: Path,
        database_id: str,
        recursive: bool = False,
        mode: str = "merge",
        identifier: str = "auto",
        dry_run: bool = False,
        pattern: str = "*.md",
    ) -> BatchImportResult:
        """Import all Markdown files from a directory."""
        # Create options object
        options = DirectoryImportOptions(
            directory_path=directory_path,
            database_id=database_id,
            recursive=recursive,
            mode=mode,
            identifier=identifier,
            dry_run=dry_run,
            pattern=pattern,
        )

        # Find all Markdown files
        if options.recursive:
            files = list(options.directory_path.rglob(options.pattern))
        else:
            files = list(options.directory_path.glob(options.pattern))

        results = []
        for file_path in files:
            result = self.import_file(
                file_path,
                options.database_id,
                options.mode,
                options.identifier,
                options.dry_run,
            )
            results.append(result)

        # Calculate summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        return BatchImportResult(
            total_files=len(results),
            successful=successful,
            failed=failed,
            results=results,
        )

    def _find_existing_page(
        self, parsed: ParsedMarkdown, database_id: str, identifier: str
    ) -> dict[str, Any] | None:
        """Find existing page based on identifier strategy."""
        if identifier == "id" or (identifier == "auto" and parsed.notion_id):
            # Try to find by ID
            if parsed.notion_id and self.client.client:
                try:
                    page = self.client.client.pages.retrieve(page_id=parsed.notion_id)
                    return page
                except Exception:
                    pass

        if identifier in ["title", "auto"] and parsed.title:
            # Try to find by title
            if self.client.client:
                results = self.client.client.databases.query(
                    database_id=database_id,
                    filter={"property": "title", "title": {"equals": parsed.title}},
                )

                if results.get("results"):
                    return results["results"][0]

        return None

    def _get_database_properties(self, database_id: str) -> dict[str, dict[str, Any]]:
        """Get properties from database schema."""
        if not self.client.client:
            raise RuntimeError("Notion client not initialized")

        database = self.client.client.databases.retrieve(database_id=database_id)
        return database.get("properties", {})

    def _filter_valid_properties(
        self, properties: dict[str, Any], db_properties: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Filter properties to only include those that exist in the database."""
        valid_properties = {}
        db_prop_names_lower = {name.lower(): name for name in db_properties.keys()}

        for prop_name, prop_value in properties.items():
            # Try exact match first
            if prop_name in db_properties:
                valid_properties[prop_name] = prop_value
            # Then try case-insensitive match
            elif prop_name.lower() in db_prop_names_lower:
                actual_name = db_prop_names_lower[prop_name.lower()]
                valid_properties[actual_name] = prop_value

        return valid_properties

    def _convert_properties_with_schema(  # noqa: PLR0912
        self, frontmatter: dict[str, Any], db_properties: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Convert frontmatter to Notion properties using database schema."""
        properties = {}
        db_prop_names_lower = {name.lower(): name for name in db_properties.keys()}

        for key, original_value in frontmatter.items():
            # Skip special keys
            if key in {"notion_id", "notion_page_id"}:
                continue

            # Normalize key name
            property_name = key.replace("_", " ").title()

            # Find matching database property (case-insensitive)
            actual_prop_name = None
            if property_name in db_properties:
                actual_prop_name = property_name
            elif property_name.lower() in db_prop_names_lower:
                actual_prop_name = db_prop_names_lower[property_name.lower()]

            if not actual_prop_name:
                continue  # Skip properties not in database

            # Get property type from database schema
            prop_config = db_properties[actual_prop_name]
            prop_type = prop_config.get("type", "")

            # Set the working value
            value = original_value

            # Special handling for assignee fields
            if key.lower() in ["assignee", "assigned_to"] and prop_type == "people":
                resolved_value = self._resolve_assignee_to_user_id(original_value)
                if not resolved_value:
                    continue  # Skip if user not found
                value = resolved_value

            # Convert value based on property type
            if prop_type == "select":
                properties[actual_prop_name] = {"select": {"name": str(value)}}
            elif prop_type == "status":
                properties[actual_prop_name] = {"status": {"name": str(value)}}
            elif prop_type == "multi_select":
                if isinstance(value, list):
                    properties[actual_prop_name] = {
                        "multi_select": [{"name": str(item)} for item in value]
                    }
                else:
                    properties[actual_prop_name] = {
                        "multi_select": [{"name": str(value)}]
                    }
            elif prop_type == "checkbox":
                properties[actual_prop_name] = {"checkbox": bool(value)}
            elif prop_type == "number":
                properties[actual_prop_name] = {
                    "number": float(value) if value else None
                }
            elif prop_type == "date":
                if isinstance(value, str):
                    properties[actual_prop_name] = {"date": {"start": value}}
                else:
                    # Handle datetime objects from frontmatter
                    properties[actual_prop_name] = {"date": {"start": str(value)}}
            elif prop_type in ["title", "rich_text"]:
                properties[actual_prop_name] = {
                    prop_type: [{"text": {"content": str(value)}}]
                }
            elif prop_type == "people":
                # Handle people/user assignments - value should be user ID(s)
                if isinstance(value, list):
                    # Multiple assignees
                    properties[actual_prop_name] = {
                        "people": [
                            {"object": "user", "id": str(user_id)}
                            for user_id in value
                            if user_id
                        ]
                    }
                # Single assignee
                elif value:
                    properties[actual_prop_name] = {
                        "people": [{"object": "user", "id": str(value)}]
                    }
            # Add more property types as needed

        return properties

    def _resolve_assignee_to_user_id(
        self, assignee_value: Any
    ) -> str | list[str] | None:
        """Resolve assignee name/email to Notion user ID(s)."""
        if not assignee_value:
            return None

        if isinstance(assignee_value, list):
            # Multiple assignees
            user_ids = []
            for assignee in assignee_value:
                user = self.client.get_user_by_name_or_email(str(assignee))
                if user:
                    user_ids.append(user["id"])
                else:
                    print(f"Warning: User '{assignee}' not found in workspace")
            return user_ids if user_ids else None
        else:
            # Single assignee
            user = self.client.get_user_by_name_or_email(str(assignee_value))
            if user:
                return user["id"]
            else:
                print(f"Warning: User '{assignee_value}' not found in workspace")
                return None

    def _create_page(self, database_id: str, parsed: ParsedMarkdown) -> str:
        """Create a new page in Notion."""
        # Get database schema
        db_properties = self._get_database_properties(database_id)

        # Convert frontmatter to properties with schema awareness
        properties = self._convert_properties_with_schema(
            parsed.frontmatter, db_properties
        )

        # Find the title property (it might be named differently)
        title_prop = None
        for prop_name, prop_config in db_properties.items():
            if prop_config.get("type") == "title":
                title_prop = prop_name
                break

        # Ensure we have a title
        if title_prop and title_prop not in properties:
            title = parsed.title or "Untitled"
            properties[title_prop] = {"title": [{"text": {"content": title}}]}

        # Add directory path as a property if file path exists and property exists
        if parsed.file_path:
            rel_path = parsed.file_path.parent.as_posix()
            if rel_path and rel_path != ".":
                # Check if Path property exists in database
                path_in_db = "Path" in db_properties or "path" in [
                    p.lower() for p in db_properties.keys()
                ]
                if path_in_db:
                    path_prop = next(
                        (p for p in db_properties.keys() if p.lower() == "path"), "Path"
                    )
                    properties[path_prop] = {
                        "rich_text": [{"text": {"content": rel_path}}]
                    }

                # Add tags based on directory structure if Tags property exists
                path_parts = [p for p in parsed.file_path.parent.parts if p != "."]
                tags_in_db = "Tags" in db_properties or "tags" in [
                    p.lower() for p in db_properties.keys()
                ]
                if path_parts and tags_in_db:
                    tags_prop = next(
                        (p for p in db_properties.keys() if p.lower() == "tags"), "Tags"
                    )
                    properties[tags_prop] = {
                        "multi_select": [{"name": part} for part in path_parts]
                    }

        # Convert content to blocks
        blocks = self.converter.markdown_to_blocks(parsed.content)

        # Create the page
        if not self.client.client:
            raise RuntimeError("Notion client not initialized")

        page = self.client.client.pages.create(
            parent={"database_id": database_id}, properties=properties, children=blocks
        )

        return page["id"]

    def _update_page(self, page_id: str, parsed: ParsedMarkdown, mode: str) -> str:
        """Update an existing page in Notion."""
        # Update properties
        if not self.client.client:
            raise RuntimeError("Notion client not initialized")

        # Get the parent database ID from the page
        page = self.client.client.pages.retrieve(page_id=page_id)
        database_id = page["parent"]["database_id"]

        # Get database schema and filter properties
        db_properties = self._get_database_properties(database_id)
        properties = self._convert_properties_with_schema(
            parsed.frontmatter, db_properties
        )

        if properties and mode != "skip":
            try:
                self.client.client.pages.update(page_id=page_id, properties=properties)
            except Exception as e:
                # Log the error but continue with content update
                print(f"Warning: Failed to update properties: {e}")

        # Handle content update based on mode
        if mode == "replace":
            # Replace all content
            self._replace_page_content(page_id, parsed.content)
        elif mode == "merge":
            # Merge content with section matching
            self._merge_page_content(page_id, parsed)
        # mode == "skip" means we don't update content

        return page_id

    def _replace_page_content(self, page_id: str, content: str) -> None:
        """Replace all content in a page."""
        # Get existing blocks
        blocks = self._get_page_blocks(page_id)

        # Delete all existing blocks
        if not self.client.client:
            raise RuntimeError("Notion client not initialized")

        for block in blocks:
            self.client.client.blocks.delete(block_id=block["id"])

        # Add new blocks
        new_blocks = self.converter.markdown_to_blocks(content)
        for block in new_blocks:
            self.client.client.blocks.children.append(
                block_id=page_id, children=[block]
            )

    def _merge_page_content(self, page_id: str, parsed: ParsedMarkdown) -> None:
        """Merge content with existing page.

        For now, this replaces all content like replace mode.
        True merge functionality would require complex matching of existing blocks.
        """
        if not self.client.client:
            raise RuntimeError("Notion client not initialized")

        # Get existing blocks
        blocks = self._get_page_blocks(page_id)

        # Delete all existing blocks
        for block in blocks:
            self.client.client.blocks.delete(block_id=block["id"])

        # Add new blocks
        new_blocks = self.converter.markdown_to_blocks(parsed.content)
        for block in new_blocks:
            self.client.client.blocks.children.append(
                block_id=page_id, children=[block]
            )

    def _get_page_blocks(self, page_id: str) -> list[dict[str, Any]]:
        """Get all blocks from a page."""
        if not self.client.client:
            raise RuntimeError("Notion client not initialized")

        blocks = []
        has_more = True
        start_cursor = None

        while has_more:
            response = self.client.client.blocks.children.list(
                block_id=page_id, start_cursor=start_cursor
            )
            blocks.extend(response["results"])
            has_more = response["has_more"]
            start_cursor = response.get("next_cursor")

        return blocks

    def validate_database_schema(
        self, database_id: str, sample_files: list[Path]
    ) -> tuple[bool, list[str]]:
        """Validate that database schema matches Markdown frontmatter."""
        warnings = []

        # Get database schema
        if not self.client.client:
            return False, ["Notion client not initialized"]

        try:
            database = self.client.client.databases.retrieve(database_id=database_id)
            db_properties = database["properties"]
        except Exception as e:
            return False, [f"Failed to retrieve database: {e!s}"]

        # Parse sample files to get property names
        all_properties = set()
        for file_path in sample_files[:5]:  # Check up to 5 files
            try:
                parsed = self.parser.parse_file(file_path)
                properties = self.converter.frontmatter_to_properties(
                    parsed.frontmatter
                )
                all_properties.update(properties.keys())
            except Exception:
                continue

        # Check for missing properties
        db_prop_names = {name for name in db_properties.keys()}
        missing_props = all_properties - db_prop_names

        if missing_props:
            warnings.append(
                f"Database missing properties: {', '.join(missing_props)}. "
                "These will be skipped during import."
            )

        return True, warnings
