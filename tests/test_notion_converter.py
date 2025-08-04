"""Tests for the Notion block converter."""

import pytest

from thought.notion_converter import NotionBlockConverter

# Test constants
EXPECTED_HEADING_COUNT = 3
EXPECTED_PARAGRAPH_COUNT = 2
EXPECTED_LIST_ITEM_COUNT = 3
EXPECTED_PRIORITY_VALUE = 5
EXPECTED_TABLE_WIDTH = 2
EXPECTED_TABLE_ROW_COUNT = 3  # Header + 2 data rows
EXPECTED_CHECKBOX_BLOCKS = 6
EXPECTED_BOLD_RICH_TEXT_PARTS = 3  # "Task with ", "bold", " text"
EXPECTED_LINE_WRAPPING_PARAGRAPHS = 3


@pytest.fixture
def converter():
    """Create a NotionBlockConverter instance."""
    return NotionBlockConverter()


class TestNotionBlockConverter:
    """Test NotionBlockConverter functionality."""

    def test_markdown_line_wrapping(self, converter):
        """Test that softbreaks (line wrapping) are converted to spaces while linebreaks are preserved."""
        markdown = """This is a long line that has been wrapped
for markdown linting compliance but should be
a single paragraph in Notion.

This is an intentional
line break that should be preserved.

Another paragraph with wrapped lines
that should flow together."""

        blocks = converter.markdown_to_blocks(markdown)

        # Should have 3 paragraphs
        assert len(blocks) == EXPECTED_LINE_WRAPPING_PARAGRAPHS
        assert all(block["type"] == "paragraph" for block in blocks)

        # First paragraph: wrapped lines should be joined with spaces
        first_rich_text = blocks[0]["paragraph"]["rich_text"]
        first_text = "".join(rt["text"]["content"] for rt in first_rich_text)
        expected_first = "This is a long line that has been wrapped for markdown linting compliance but should be a single paragraph in Notion."
        assert first_text == expected_first

        # Second paragraph: intentional line break should be preserved
        second_rich_text = blocks[1]["paragraph"]["rich_text"]
        second_text = "".join(rt["text"]["content"] for rt in second_rich_text)
        assert "intentional\nline break" in second_text

        # Third paragraph: wrapped lines should be joined
        third_rich_text = blocks[2]["paragraph"]["rich_text"]
        third_text = "".join(rt["text"]["content"] for rt in third_rich_text)
        expected_third = (
            "Another paragraph with wrapped lines that should flow together."
        )
        assert third_text == expected_third

    def test_convert_heading(self, converter):
        """Test heading conversion."""
        markdown = "# Heading 1\n## Heading 2\n### Heading 3"
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == EXPECTED_HEADING_COUNT
        assert blocks[0]["type"] == "heading_1"
        assert blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "Heading 1"

        assert blocks[1]["type"] == "heading_2"
        assert blocks[1]["heading_2"]["rich_text"][0]["text"]["content"] == "Heading 2"

        assert blocks[2]["type"] == "heading_3"
        assert blocks[2]["heading_3"]["rich_text"][0]["text"]["content"] == "Heading 3"

    def test_convert_paragraph(self, converter):
        """Test paragraph conversion."""
        markdown = "This is a simple paragraph.\n\nThis is another paragraph."
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == EXPECTED_PARAGRAPH_COUNT
        assert blocks[0]["type"] == "paragraph"
        assert (
            blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
            == "This is a simple paragraph."
        )
        assert (
            blocks[1]["paragraph"]["rich_text"][0]["text"]["content"]
            == "This is another paragraph."
        )

    def test_convert_list(self, converter):
        """Test list conversion."""
        # Unordered list
        markdown = "- Item 1\n- Item 2\n- Item 3"
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == EXPECTED_LIST_ITEM_COUNT
        assert all(block["type"] == "bulleted_list_item" for block in blocks)
        assert (
            blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"]
            == "Item 1"
        )

        # Ordered list
        markdown = "1. First\n2. Second\n3. Third"
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == EXPECTED_LIST_ITEM_COUNT
        assert all(block["type"] == "numbered_list_item" for block in blocks)
        assert (
            blocks[0]["numbered_list_item"]["rich_text"][0]["text"]["content"]
            == "First"
        )

    def test_convert_code_block(self, converter):
        """Test code block conversion."""
        markdown = '```python\ndef hello():\n    print("Hello, World!")\n```'
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert "def hello():" in blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_convert_quote(self, converter):
        """Test block quote conversion."""
        markdown = "> This is a quote\n> spanning multiple lines"
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "quote"
        assert (
            "This is a quote" in blocks[0]["quote"]["rich_text"][0]["text"]["content"]
        )

    def test_convert_divider(self, converter):
        """Test horizontal rule conversion."""
        markdown = "---"
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "divider"
        assert blocks[0]["divider"] == {}

    def test_inline_formatting(self, converter):
        """Test inline formatting conversion."""
        markdown = "Text with **bold**, *italic*, and `code`."
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        rich_text = blocks[0]["paragraph"]["rich_text"]

        # Find formatted segments
        bold_text = next(t for t in rich_text if t.get("annotations", {}).get("bold"))
        italic_text = next(
            t for t in rich_text if t.get("annotations", {}).get("italic")
        )
        code_text = next(t for t in rich_text if t.get("annotations", {}).get("code"))

        assert bold_text["text"]["content"] == "bold"
        assert italic_text["text"]["content"] == "italic"
        assert code_text["text"]["content"] == "code"

    def test_links(self, converter):
        """Test link conversion."""
        markdown = "Check out [Notion](https://notion.so) for more info."
        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        rich_text = blocks[0]["paragraph"]["rich_text"]

        # Find link
        link_text = next(t for t in rich_text if "link" in t.get("text", {}))
        assert link_text["text"]["content"] == "Notion"
        assert link_text["text"]["link"]["url"] == "https://notion.so"

    def test_frontmatter_to_properties(self, converter):
        """Test frontmatter to properties conversion."""
        frontmatter = {
            "title": "Test Page",
            "tags": ["python", "testing"],
            "completed": True,
            "priority": 5,
            "due_date": "2024-12-31",
            "notion_id": "skip-this",
        }

        properties = converter.frontmatter_to_properties(frontmatter)

        # Check title (rich text)
        assert "Title" in properties
        assert properties["Title"]["rich_text"][0]["text"]["content"] == "Test Page"

        # Check tags (multi-select)
        assert "Tags" in properties
        assert properties["Tags"]["multi_select"] == [
            {"name": "python"},
            {"name": "testing"},
        ]

        # Check completed (checkbox)
        assert "Completed" in properties
        assert properties["Completed"]["checkbox"] is True

        # Check priority (number)
        assert "Priority" in properties
        assert properties["Priority"]["number"] == EXPECTED_PRIORITY_VALUE

        # Check date
        assert "Due Date" in properties
        assert properties["Due Date"]["date"]["start"] == "2024-12-31"

        # Check that notion_id is skipped
        assert "notion_id" not in properties
        assert "Notion Id" not in properties

    def test_complex_document(self, converter):
        """Test conversion of a complex document."""
        markdown = """# Main Title

This is an introduction with **bold** text.

## Features

- Feature 1
- Feature 2 with `code`
- Feature 3

### Code Example

```javascript
const greeting = "Hello, World!";
console.log(greeting);
```

> Important note: This is a quote.

---

## Conclusion

Final paragraph with a [link](https://example.com).
"""

        blocks = converter.markdown_to_blocks(markdown)

        # Verify structure
        block_types = [block["type"] for block in blocks]
        expected_types = [
            "heading_1",
            "paragraph",
            "heading_2",
            "bulleted_list_item",
            "bulleted_list_item",
            "bulleted_list_item",
            "heading_3",
            "code",
            "quote",
            "divider",
            "heading_2",
            "paragraph",
        ]

        assert block_types == expected_types

    def test_empty_content(self, converter):
        """Test handling of empty content."""
        assert converter.markdown_to_blocks("") == []
        assert converter.markdown_to_blocks("   \n  \n  ") == []

    def test_table_conversion(self, converter):
        """Test table conversion."""
        markdown = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |"""

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "table"
        assert blocks[0]["table"]["table_width"] == EXPECTED_TABLE_WIDTH
        assert blocks[0]["table"]["has_column_header"] is True

        # Check table rows
        rows = blocks[0]["table"]["children"]
        assert len(rows) == EXPECTED_TABLE_ROW_COUNT  # Header + 2 data rows

    def test_checkbox_conversion(self, converter):
        """Test checkbox/to-do item conversion."""
        markdown = """- [x] Completed task
- [X] Another completed task (uppercase)
- [ ] Incomplete task
- Regular list item
- [x] Task with **bold** text
- [ ] Task with `inline code`"""

        blocks = converter.markdown_to_blocks(markdown)

        # Verify we have the expected number of blocks
        assert len(blocks) == EXPECTED_CHECKBOX_BLOCKS

        # First block: completed checkbox
        assert blocks[0]["type"] == "to_do"
        assert blocks[0]["to_do"]["checked"] is True
        assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "Completed task"

        # Second block: completed checkbox (uppercase X)
        assert blocks[1]["type"] == "to_do"
        assert blocks[1]["to_do"]["checked"] is True
        assert (
            blocks[1]["to_do"]["rich_text"][0]["text"]["content"]
            == "Another completed task (uppercase)"
        )

        # Third block: incomplete checkbox
        assert blocks[2]["type"] == "to_do"
        assert blocks[2]["to_do"]["checked"] is False
        assert (
            blocks[2]["to_do"]["rich_text"][0]["text"]["content"] == "Incomplete task"
        )

        # Fourth block: regular list item
        assert blocks[3]["type"] == "bulleted_list_item"
        assert (
            blocks[3]["bulleted_list_item"]["rich_text"][0]["text"]["content"]
            == "Regular list item"
        )

        # Fifth block: checkbox with bold text
        assert blocks[4]["type"] == "to_do"
        assert blocks[4]["to_do"]["checked"] is True
        # Check that bold formatting is preserved
        rich_text = blocks[4]["to_do"]["rich_text"]
        assert len(rich_text) == EXPECTED_BOLD_RICH_TEXT_PARTS
        assert rich_text[1]["annotations"]["bold"] is True
        assert rich_text[1]["text"]["content"] == "bold"

        # Sixth block: checkbox with inline code
        assert blocks[5]["type"] == "to_do"
        assert blocks[5]["to_do"]["checked"] is False
        # Check that code formatting is preserved
        rich_text = blocks[5]["to_do"]["rich_text"]
        has_code = any(item["annotations"]["code"] for item in rich_text)
        assert has_code
