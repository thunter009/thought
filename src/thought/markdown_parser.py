"""Markdown parser module for importing Markdown files to Notion."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import frontmatter
    import mistune
except ImportError as e:
    raise ImportError(
        "Required dependencies not installed. Please install: "
        "pip install python-frontmatter mistune"
    ) from e

# Constants
MIN_CODE_FENCE_LENGTH = 3


@dataclass
class MarkdownSection:
    """Represents a section within a Markdown document."""

    level: int
    title: str
    content: str
    start_line: int
    end_line: int
    marker: str | None = None  # For Notion section markers


@dataclass
class ParsedMarkdown:
    """Container for parsed Markdown content and metadata."""

    frontmatter: dict[str, Any]
    content: str
    sections: list[MarkdownSection]
    file_path: Path | None = None

    @property
    def title(self) -> str | None:
        """Extract title from frontmatter or first heading."""
        if "title" in self.frontmatter:
            return self.frontmatter["title"]
        if "name" in self.frontmatter:
            return self.frontmatter["name"]
        if self.sections and self.sections[0].level == 1:
            return self.sections[0].title
        return None

    @property
    def notion_id(self) -> str | None:
        """Extract Notion ID from frontmatter."""
        return self.frontmatter.get("notion_id") or self.frontmatter.get(
            "notion_page_id"
        )


class MarkdownParser:
    """Parser for Markdown files with frontmatter support."""

    SECTION_MARKER_PATTERN = re.compile(
        r"<!--\s*notion-section:\s*([^-]+?)\s*-->", re.IGNORECASE
    )

    def __init__(self):
        self.renderer = mistune.create_markdown(renderer="ast")

    def parse_file(self, file_path: Path) -> ParsedMarkdown:
        """Parse a Markdown file from disk."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        parsed = self.parse_content(content)
        parsed.file_path = file_path
        return parsed

    def parse_content(self, content: str) -> ParsedMarkdown:
        """Parse Markdown content string."""
        # Parse frontmatter
        post = frontmatter.loads(content)
        metadata = post.metadata
        markdown_content = post.content

        # Extract sections
        sections = self._extract_sections(markdown_content)

        return ParsedMarkdown(
            frontmatter=metadata, content=markdown_content, sections=sections
        )

    def _extract_sections(self, content: str) -> list[MarkdownSection]:
        """Extract sections from Markdown content."""
        sections = []
        lines = content.split("\n")

        current_section = None
        section_content = []

        for i, line in enumerate(lines):
            # Check for section marker
            marker_match = self.SECTION_MARKER_PATTERN.match(line)
            marker = marker_match.group(1).strip() if marker_match else None

            # Check for heading
            if line.startswith("#"):
                # Save previous section
                if current_section:
                    current_section.content = "\n".join(section_content).strip()
                    current_section.end_line = i - 1
                    sections.append(current_section)

                # Parse heading
                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip()

                current_section = MarkdownSection(
                    level=level,
                    title=title,
                    content="",
                    start_line=i,
                    end_line=i,
                    marker=marker,
                )
                section_content = []
            elif current_section:
                section_content.append(line)

        # Save last section
        if current_section:
            current_section.content = "\n".join(section_content).strip()
            current_section.end_line = len(lines) - 1
            sections.append(current_section)

        return sections

    def validate_markdown(self, content: str) -> tuple[bool, list[str]]:
        """Validate Markdown syntax and return errors if any."""
        errors = []

        try:
            # Try to parse with mistune
            ast = self.renderer(content)
            if not ast:
                errors.append("Failed to parse Markdown content")
        except Exception as e:
            errors.append(f"Markdown parsing error: {e!s}")

        # Check for common issues
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Check for unclosed code blocks
            if (
                line.strip().startswith("```")
                and len(line.strip()) > MIN_CODE_FENCE_LENGTH
            ):
                # Count backticks to ensure they're closed
                backtick_count = content.count("```")
                if backtick_count % 2 != 0:
                    errors.append(f"Unclosed code block starting at line {i}")

        return len(errors) == 0, errors
