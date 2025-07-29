"""Convert Markdown elements to Notion blocks."""

import re
from typing import Any

import mistune


class NotionBlockConverter:
    """Convert Markdown AST to Notion block format."""

    def __init__(self):
        # Enable table plugin for proper table parsing
        self.parser = mistune.create_markdown(renderer="ast", plugins=["table"])

    def markdown_to_blocks(self, markdown_content: str) -> list[dict[str, Any]]:
        """Convert Markdown content to Notion blocks."""
        ast = self.parser(markdown_content)
        blocks = []

        for node in ast:
            if isinstance(node, dict):
                block = self._convert_node(node)
                if block:
                    if isinstance(block, list):
                        blocks.extend(block)
                    else:
                        blocks.append(block)

        return blocks

    def _convert_node(
        self, node: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Convert a single AST node to Notion block(s)."""
        node_type = node.get("type")

        converters = {
            "heading": self._convert_heading,
            "paragraph": self._convert_paragraph,
            "list": self._convert_list,
            "list_item": self._convert_list_item,
            "code_block": self._convert_code_block,
            "block_code": self._convert_code_block,  # New AST name
            "block_quote": self._convert_quote,
            "table": self._convert_table,
            "hr": self._convert_divider,
            "thematic_break": self._convert_divider,  # New AST name
        }

        if node_type and node_type in converters:
            converter = converters[node_type]
            return converter(node)

        return None

    def _convert_heading(self, node: dict[str, Any]) -> dict[str, Any]:
        """Convert heading to Notion heading block."""
        # Handle new AST structure with attrs
        attrs = node.get("attrs", {})
        level = attrs.get("level", node.get("level", 1))
        text = self._extract_text(node.get("children", []))

        heading_types = {
            1: "heading_1",
            2: "heading_2",
            3: "heading_3",
        }

        block_type = heading_types.get(level, "heading_3")

        return {
            "object": "block",
            "type": block_type,
            block_type: {"rich_text": NotionBlockConverter._create_rich_text(text)},
        }

    def _convert_paragraph(self, node: dict[str, Any]) -> dict[str, Any]:
        """Convert paragraph to Notion paragraph block."""
        rich_text = self._convert_inline_elements(node.get("children", []))

        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text},
        }

    def _convert_list(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert list to Notion list blocks."""
        blocks = []
        # Handle new AST structure with attrs
        attrs = node.get("attrs", {})
        ordered = attrs.get("ordered", node.get("ordered", False))
        list_type = "numbered_list_item" if ordered else "bulleted_list_item"

        for item in node.get("children", []):
            if item.get("type") == "list_item":
                block = self._convert_list_item(item, list_type)
                if block:
                    blocks.append(block)

        return blocks

    def _convert_list_item(
        self, node: dict[str, Any], list_type: str = "bulleted_list_item"
    ) -> dict[str, Any]:
        """Convert list item to Notion list item block."""
        rich_text = self._convert_inline_elements(node.get("children", []))

        return {
            "object": "block",
            "type": list_type,
            list_type: {"rich_text": rich_text},
        }

    def _convert_code_block(self, node: dict[str, Any]) -> dict[str, Any]:
        """Convert code block to Notion code block."""
        # Handle both 'raw' and 'text' fields
        code = node.get("raw", node.get("text", ""))
        # Handle new AST structure
        attrs = node.get("attrs", {})
        language = attrs.get("info", node.get("info", "plain text"))

        # Map common language names to Notion's supported languages
        language_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "yml": "yaml",
            "sh": "bash",
            "": "plain text",
        }

        language = language_map.get(language, language)

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": NotionBlockConverter._create_rich_text(code),
                "language": language,
            },
        }

    def _convert_quote(self, node: dict[str, Any]) -> dict[str, Any]:
        """Convert block quote to Notion quote block."""
        text = self._extract_text_from_children(node.get("children", []))

        return {
            "object": "block",
            "type": "quote",
            "quote": {"rich_text": NotionBlockConverter._create_rich_text(text)},
        }

    def _convert_table(self, node: dict[str, Any]) -> dict[str, Any] | None:
        """Convert table to Notion table block."""
        rows = []

        # Process table children (table_head and table_body)
        for child in node.get("children", []):
            if child.get("type") == "table_head":
                # Process header row(s)
                cells = []
                for cell in child.get("children", []):
                    if cell.get("type") == "table_cell":
                        cell_text = self._extract_text_from_children(
                            cell.get("children", [])
                        )
                        cells.append(NotionBlockConverter._create_rich_text(cell_text))
                if cells:
                    rows.append(cells)
            elif child.get("type") == "table_body":
                # Process data rows
                for row in child.get("children", []):
                    if row.get("type") == "table_row":
                        cells = []
                        for cell in row.get("children", []):
                            if cell.get("type") == "table_cell":
                                cell_text = self._extract_text_from_children(
                                    cell.get("children", [])
                                )
                                cells.append(
                                    NotionBlockConverter._create_rich_text(cell_text)
                                )
                        rows.append(cells)

        if not rows:
            return None

        # Notion tables need to know dimensions upfront
        return {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": len(rows[0]) if rows else 0,
                "has_column_header": True,
                "has_row_header": False,
                "children": [
                    {
                        "object": "block",
                        "type": "table_row",
                        "table_row": {"cells": row},
                    }
                    for row in rows
                ],
            },
        }

    @staticmethod
    def _convert_divider(_node: dict[str, Any]) -> dict[str, Any]:
        """Convert horizontal rule to Notion divider block."""
        return {"object": "block", "type": "divider", "divider": {}}

    def _convert_inline_elements(
        self, children: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert inline elements to rich text."""
        rich_text = []

        for child in children:
            child_type = child.get("type")

            if child_type == "text":
                # Handle both 'raw' and 'text' fields
                text = child.get("raw", child.get("text", ""))
                rich_text.append(NotionBlockConverter._create_text_object(text))

            elif child_type == "strong":
                text = self._extract_text(child.get("children", []))
                rich_text.append(
                    NotionBlockConverter._create_text_object(text, bold=True)
                )

            elif child_type == "emphasis":
                text = self._extract_text(child.get("children", []))
                rich_text.append(
                    NotionBlockConverter._create_text_object(text, italic=True)
                )

            elif child_type in ["code_span", "codespan"]:
                text = child.get("raw", child.get("text", ""))
                rich_text.append(
                    NotionBlockConverter._create_text_object(text, code=True)
                )

            elif child_type == "link":
                text = self._extract_text(child.get("children", []))
                # Handle new AST structure with attrs
                attrs = child.get("attrs", {})
                url = attrs.get("url", child.get("url", ""))
                rich_text.append(
                    NotionBlockConverter._create_text_object(text, url=url)
                )

            elif child_type == "paragraph":
                # Nested paragraph in list item
                rich_text.extend(
                    self._convert_inline_elements(child.get("children", []))
                )

            elif child_type == "block_text":
                # Handle block_text nodes in list items
                rich_text.extend(
                    self._convert_inline_elements(child.get("children", []))
                )

        return rich_text

    def _extract_text(self, children: list[dict[str, Any]]) -> str:
        """Extract plain text from children nodes."""
        text = ""
        for child in children:
            if child.get("type") == "text":
                # Handle both 'raw' and 'text' fields
                text += child.get("raw", child.get("text", ""))
            elif child.get("type") in ["codespan", "code_span"]:
                text += child.get("raw", child.get("text", ""))
            elif "children" in child:
                text += self._extract_text(child["children"])
        return text

    def _extract_text_from_children(self, children: list[dict[str, Any]]) -> str:
        """Extract text from complex children structures."""
        text_parts = []

        for child in children:
            if child.get("type") == "paragraph":
                text_parts.append(self._extract_text(child.get("children", [])))
            elif child.get("type") == "text":
                text_parts.append(child.get("raw", child.get("text", "")))
            elif "children" in child:
                text_parts.append(self._extract_text_from_children(child["children"]))

        return "\n".join(text_parts)

    @staticmethod
    def _create_rich_text(text: str) -> list[dict[str, Any]]:
        """Create rich text array from plain text."""
        if not text:
            return []

        return [NotionBlockConverter._create_text_object(text)]

    @staticmethod
    def _create_text_object(
        text: str,
        bold: bool = False,
        italic: bool = False,
        code: bool = False,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Create a rich text object."""
        text_obj = {
            "type": "text",
            "text": {"content": text},
            "annotations": {
                "bold": bold,
                "italic": italic,
                "strikethrough": False,
                "underline": False,
                "code": code,
                "color": "default",
            },
        }

        if url:
            text_obj["text"]["link"] = {"url": url}

        return text_obj

    def frontmatter_to_properties(self, frontmatter: dict[str, Any]) -> dict[str, Any]:
        """Convert frontmatter to Notion page properties."""
        properties = {}

        for key, value in frontmatter.items():
            # Skip special keys
            if key in {"notion_id", "notion_page_id"}:
                continue

            # Normalize key name (capitalize first letter)
            property_name = key.replace("_", " ").title()

            # Infer property type based on value
            if isinstance(value, list):
                # Multi-select for lists
                properties[property_name] = {
                    "multi_select": [{"name": str(item)} for item in value]
                }
            elif isinstance(value, bool):
                # Checkbox for booleans
                properties[property_name] = {"checkbox": value}
            elif isinstance(value, int | float):
                # Number for numeric values
                properties[property_name] = {"number": value}
            elif isinstance(value, str):
                # Check if it looks like a date
                if re.match(r"^\d{4}-\d{2}-\d{2}", value):
                    properties[property_name] = {"date": {"start": value}}
                else:
                    # Default to rich text
                    properties[property_name] = {
                        "rich_text": NotionBlockConverter._create_rich_text(value)
                    }

        return properties
