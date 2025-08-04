"""Convert Markdown elements to Notion blocks."""

import copy
import re
from typing import Any

import mistune

# Constants for Notion API limits
NOTION_MAX_TEXT_LENGTH = 2000
NOTION_CODE_BLOCK_BUFFER = 1900  # Leave some buffer for safety


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

    def _convert_paragraph(
        self, node: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Convert paragraph to Notion paragraph block."""
        children = node.get("children", [])

        # Split into lines if contains softbreaks
        lines = self._split_paragraph_lines(children)

        # Check if this contains multiple checkbox lines
        if self._has_multiple_checkbox_lines(lines):
            return self._convert_multiline_checkboxes(lines)

        # Single line - check if it's a checkbox
        full_text = self._extract_text(children)
        checkbox_match = re.match(r"^\[([ x])\]\s*(.*)$", full_text, re.IGNORECASE)

        if checkbox_match:
            return self._create_todo_block(checkbox_match, children)
        else:
            # Regular paragraph
            rich_text = self._convert_inline_elements(children)
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rich_text},
            }

    def _split_paragraph_lines(
        self, children: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Split paragraph children by linebreak (not softbreak) into separate lines."""
        current_line_parts = []
        lines = []

        for child in children:
            if child.get("type") == "linebreak":
                if current_line_parts:
                    lines.append(current_line_parts)
                    current_line_parts = []
            else:
                current_line_parts.append(child)

        # Don't forget the last line
        if current_line_parts:
            lines.append(current_line_parts)

        return lines

    def _has_multiple_checkbox_lines(self, lines: list[list[dict[str, Any]]]) -> bool:
        """Check if we have multiple lines that might contain checkboxes."""
        if len(lines) <= 1:
            return False

        # Check if any line contains checkbox syntax
        for line_parts in lines:
            for part in line_parts:
                text_content = part.get("raw", part.get("text", ""))
                if part.get("type") == "text" and "[" in text_content:
                    return True
        return False

    def _convert_multiline_checkboxes(
        self, lines: list[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Convert multiple lines that may contain checkboxes."""
        blocks = []

        for line_parts in lines:
            line_text = self._extract_line_text(line_parts)
            checkbox_match = re.match(r"^\[([ x])\]\s*(.*)$", line_text, re.IGNORECASE)

            if checkbox_match:
                checked = checkbox_match.group(1).lower() == "x"
                remainder_text = checkbox_match.group(2)
                blocks.append(
                    {
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": NotionBlockConverter._create_rich_text(
                                remainder_text
                            ),
                            "checked": checked,
                        },
                    }
                )
            else:
                # Not a checkbox line, create as paragraph
                rich_text = self._convert_inline_elements(line_parts)
                if rich_text:  # Only add if there's content
                    blocks.append(
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": rich_text},
                        }
                    )

        return (
            blocks
            if blocks
            else {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": []},
            }
        )

    def _extract_line_text(self, line_parts: list[dict[str, Any]]) -> str:
        """Extract plain text from a line's parts."""
        line_text = ""
        for part in line_parts:
            if part.get("type") == "text":
                line_text += part.get("raw", part.get("text", ""))
            elif part.get("type") == "softbreak":
                line_text += " "
            elif part.get("type") == "linebreak":
                line_text += "\n"
            elif part.get("type") in ["strong", "emphasis", "code_span", "codespan"]:
                line_text += self._extract_text(part.get("children", []))
        return line_text

    def _create_todo_block(
        self, checkbox_match: re.Match, children: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Create a to-do block from checkbox match."""
        checked = checkbox_match.group(1).lower() == "x"

        # Process the rich text, removing the checkbox syntax
        modified_children = self._remove_checkbox_syntax(children)
        rich_text = self._convert_inline_elements(modified_children)

        return {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": rich_text,
                "checked": checked,
            },
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
        # Only check for checkbox in bulleted lists
        if list_type != "bulleted_list_item":
            rich_text = self._convert_inline_elements(node.get("children", []))
            return {
                "object": "block",
                "type": list_type,
                list_type: {"rich_text": rich_text},
            }

        # Extract the full text content to check for checkbox pattern
        full_text = self._extract_text(node.get("children", []))
        checkbox_match = re.match(r"^\[([ x])\]\s*(.*)$", full_text, re.IGNORECASE)

        if checkbox_match:
            # This is a checkbox/to-do item
            checked = checkbox_match.group(1).lower() == "x"

            # Process the rich text, removing the checkbox syntax
            modified_children = self._remove_checkbox_syntax(node.get("children", []))
            rich_text = self._convert_inline_elements(modified_children)

            return {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": rich_text,
                    "checked": checked,
                },
            }
        else:
            # Regular list item
            rich_text = self._convert_inline_elements(node.get("children", []))
            return {
                "object": "block",
                "type": list_type,
                list_type: {"rich_text": rich_text},
            }

    def _convert_code_block(
        self, node: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
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

        # Check if code exceeds Notion's 2000 character limit
        if len(code) > NOTION_MAX_TEXT_LENGTH:
            # Split code into multiple blocks
            blocks = []

            # Split code by lines to avoid breaking in the middle of a line
            lines = code.split("\n")
            current_chunk = []
            current_length = 0

            for line in lines:
                # Check if adding this line would exceed the limit
                line_length = len(line) + 1  # +1 for newline
                if (
                    current_length + line_length > NOTION_CODE_BLOCK_BUFFER
                    and current_chunk
                ):
                    # Create a code block for the current chunk
                    blocks.append(
                        {
                            "object": "block",
                            "type": "code",
                            "code": {
                                "rich_text": NotionBlockConverter._create_rich_text(
                                    "\n".join(current_chunk)
                                ),
                                "language": language,
                            },
                        }
                    )
                    current_chunk = [line]
                    current_length = line_length
                else:
                    current_chunk.append(line)
                    current_length += line_length

            # Add the last chunk
            if current_chunk:
                blocks.append(
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": NotionBlockConverter._create_rich_text(
                                "\n".join(current_chunk)
                            ),
                            "language": language,
                        },
                    }
                )

            return blocks
        else:
            # Code is within the limit, return as single block
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

            elif child_type == "softbreak":
                # Convert softbreak (line wrapping) to a single space
                rich_text.append(NotionBlockConverter._create_text_object(" "))

            elif child_type == "linebreak":
                # Convert linebreak (intentional break with two spaces) to line break
                rich_text.append(NotionBlockConverter._create_text_object("\n"))

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
            elif child.get("type") == "softbreak":
                # Convert softbreak to space for text extraction
                text += " "
            elif child.get("type") == "linebreak":
                # Convert linebreak to newline for text extraction
                text += "\n"
            elif child.get("type") in ["codespan", "code_span"]:
                text += child.get("raw", child.get("text", ""))
            elif "children" in child:
                text += self._extract_text(child["children"])
        return text

    def _remove_checkbox_syntax(
        self, children: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove checkbox syntax from the beginning of children nodes."""
        modified_children = copy.deepcopy(children)

        # If children is a direct list of text nodes (paragraph case)
        if children and children[0].get("type") == "text":
            return self._remove_checkbox_from_text_nodes(modified_children)

        # Original logic for nested structures
        return self._remove_checkbox_from_nested_nodes(modified_children)

    def _remove_checkbox_from_text_nodes(
        self, modified_children: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove checkbox syntax from direct text nodes."""
        text_accumulated = ""
        nodes_to_process = []

        for i, child in enumerate(modified_children):
            if child.get("type") != "text":
                break

            text = child.get("raw", child.get("text", ""))
            text_accumulated += text
            nodes_to_process.append(i)

            # Check if we have enough text to match checkbox pattern
            checkbox_match = re.match(
                r"^\[([ x])\]\s*(.*)$", text_accumulated, re.IGNORECASE
            )
            if checkbox_match:
                # Found the checkbox pattern
                remainder = checkbox_match.group(2)

                # Remove all accumulated text nodes except the last
                for idx in reversed(nodes_to_process[:-1]):
                    modified_children.pop(idx)

                # Update the last text node with the remainder
                last_idx = nodes_to_process[-1] - len(nodes_to_process[:-1])
                if last_idx < len(modified_children):
                    modified_children[last_idx]["raw"] = remainder
                    modified_children[last_idx]["text"] = remainder
                break

        return modified_children

    def _remove_checkbox_from_nested_nodes(
        self, modified_children: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove checkbox syntax from nested block structures."""
        for child in modified_children:
            if child.get("type") in ["block_text", "paragraph"]:
                inner_children = child.get("children", [])

                # Process text nodes to remove checkbox syntax
                text_accumulated = ""
                nodes_to_process = []

                for i, inner_child in enumerate(inner_children):
                    if inner_child.get("type") == "text":
                        text = inner_child.get("raw", inner_child.get("text", ""))
                        text_accumulated += text
                        nodes_to_process.append(i)

                        # Check if we have enough text to match checkbox pattern
                        checkbox_match = re.match(
                            r"^\[([ x])\]\s*(.*)$", text_accumulated, re.IGNORECASE
                        )
                        if checkbox_match:
                            # Found the checkbox pattern
                            remainder = checkbox_match.group(2)

                            # Remove all accumulated text nodes
                            for idx in reversed(nodes_to_process[:-1]):
                                inner_children.pop(idx)

                            # Update the last text node with the remainder
                            last_idx = nodes_to_process[-1] - len(nodes_to_process[:-1])
                            inner_children[last_idx]["raw"] = remainder
                            inner_children[last_idx]["text"] = remainder
                            break
                    else:
                        # Non-text node, stop accumulating
                        break

        return modified_children

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
