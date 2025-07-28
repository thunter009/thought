---
title: Property Filtering Demo
tags:
  - demo
  - import
priority: 3
completed: true
custom_field: "This won't be imported"
another_field: 123
---

# Property Filtering Demo

This file demonstrates how the Markdown import feature now handles properties that don't exist in the target Notion database.

## How it works

The import service will:

1. Fetch the database schema to see what properties exist
2. Filter out any properties from the frontmatter that don't exist in the database
3. Only send valid properties to Notion, preventing the "property does not exist" errors

## Example

If your Notion database only has:
- Title
- Tags

But your Markdown file has:
- title ✅ (will be imported)
- tags ✅ (will be imported)
- priority ❌ (will be skipped)
- completed ❌ (will be skipped)
- custom_field ❌ (will be skipped)

The import will succeed with only the valid properties!