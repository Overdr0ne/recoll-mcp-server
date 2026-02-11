#!/usr/bin/env python3
"""
Recoll MCP Server - Natural Language Interface to Indexed Filesystem

Provides Claude with access to your Recoll-indexed filesystem through MCP.
Supports natural language queries with semantic understanding.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Any, Sequence
from recoll import recoll
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Set Recoll config directory
os.environ['RECOLL_CONFDIR'] = os.path.expanduser('~/.config/recoll')

# Initialize Recoll database connection
try:
    db = recoll.connect()
except Exception as e:
    print(f"Warning: Could not connect to Recoll database: {e}", flush=True)
    db = None

# Create MCP server instance
server = Server("recoll-search")


def format_doc_result(doc: Any, include_preview: bool = True) -> dict:
    """Format a Recoll document result as a structured dict."""
    result = {
        "filename": doc.filename,
        "url": doc.url,
        "mimetype": doc.mimetype,
        "size": doc.fbytes,
        "mtime": doc.mtime,
        "mtime_readable": datetime.fromtimestamp(int(doc.mtime[1:])).strftime("%Y-%m-%d %H:%M:%S"),
    }

    if include_preview and hasattr(doc, 'abstract'):
        result["preview"] = doc.abstract[:300]

    return result


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available Recoll search tools."""
    return [
        Tool(
            name="search_filesystem",
            description="""Search the indexed filesystem using keywords or phrases.
            Supports Boolean queries (AND, OR, NOT), phrase searches ("exact phrase"),
            and wildcards. Results are ranked by relevance.

            Examples:
            - "todo yubikey" - finds documents with both terms
            - "blog OR post" - finds documents with either term
            - '"exact phrase"' - finds exact phrase match
            - "python NOT django" - excludes documents with django
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query using Recoll syntax (keywords, Boolean operators, phrases)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)",
                        "default": 20,
                    },
                    "include_preview": {
                        "type": "boolean",
                        "description": "Include content preview/abstract in results (default: true)",
                        "default": True,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_by_date",
            description="""Search files filtered by modification date range.
            Useful for finding recent documents or documents from a specific time period.

            Examples:
            - Find notes from last month
            - Find documents modified in 2025
            - Find files changed this week
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (keywords)",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_by_filetype",
            description="""Search files filtered by file type/mimetype.

            Common types:
            - "pdf" or "application/pdf" - PDF documents
            - "text" or "text/*" - All text files
            - "markdown" or "text/markdown" - Markdown files
            - "doc" or "application/msword" - Word documents
            - "image" or "image/*" - All images
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (keywords)",
                    },
                    "filetype": {
                        "type": "string",
                        "description": "File type filter (e.g., 'pdf', 'markdown', 'text', 'image')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["query", "filetype"],
            },
        ),
        Tool(
            name="get_document_content",
            description="""Retrieve the full content of a document by its file URL.
            Use this after a search to get the complete text of a specific document.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "File URL from search results (file:///path/to/file)",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="list_recent_files",
            description="""List recently modified files in the index.
            Useful for seeing what's been recently updated.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days back to search (default: 7)",
                        "default": 7,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 20)",
                        "default": 20,
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
    """Handle tool calls for Recoll searches."""

    if db is None:
        return [TextContent(
            type="text",
            text="Error: Recoll database not available. Check configuration."
        )]

    try:
        if name == "search_filesystem":
            query_str = arguments["query"]
            max_results = arguments.get("max_results", 20)
            include_preview = arguments.get("include_preview", True)

            query = db.query()
            nres = query.execute(query_str)

            results = []
            for i in range(min(max_results, nres)):
                doc = query.fetchone()
                results.append(format_doc_result(doc, include_preview))

            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": query_str,
                    "total_results": nres,
                    "returned_results": len(results),
                    "results": results
                }, indent=2)
            )]

        elif name == "search_by_date":
            query_str = arguments["query"]
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            max_results = arguments.get("max_results", 20)

            # Build date filter
            date_filter = ""
            if start_date and end_date:
                date_filter = f" date:{start_date}/{end_date}"
            elif start_date:
                date_filter = f" date:{start_date}/"
            elif end_date:
                date_filter = f" date:/{end_date}"

            full_query = query_str + date_filter

            query = db.query()
            nres = query.execute(full_query)

            results = []
            for i in range(min(max_results, nres)):
                doc = query.fetchone()
                results.append(format_doc_result(doc))

            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": full_query,
                    "total_results": nres,
                    "returned_results": len(results),
                    "results": results
                }, indent=2)
            )]

        elif name == "search_by_filetype":
            query_str = arguments["query"]
            filetype = arguments["filetype"]
            max_results = arguments.get("max_results", 20)

            # Build type filter
            full_query = f"{query_str} mime:{filetype}"

            query = db.query()
            nres = query.execute(full_query)

            results = []
            for i in range(min(max_results, nres)):
                doc = query.fetchone()
                results.append(format_doc_result(doc))

            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": full_query,
                    "total_results": nres,
                    "returned_results": len(results),
                    "results": results
                }, indent=2)
            )]

        elif name == "get_document_content":
            url = arguments["url"]

            # Extract file path from URL
            if url.startswith("file://"):
                filepath = url[7:]
            else:
                filepath = url

            # Read file content
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "url": url,
                        "filepath": filepath,
                        "content": content[:10000],  # Limit to first 10k chars
                        "truncated": len(content) > 10000
                    }, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error reading file: {e}"
                )]

        elif name == "list_recent_files":
            days = arguments.get("days", 7)
            max_results = arguments.get("max_results", 20)

            # Search for files modified in last N days
            query = db.query()
            nres = query.execute(f"date:{days}d/")

            results = []
            for i in range(min(max_results, nres)):
                doc = query.fetchone()
                results.append(format_doc_result(doc))

            return [TextContent(
                type="text",
                text=json.dumps({
                    "days": days,
                    "total_results": nres,
                    "returned_results": len(results),
                    "results": results
                }, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing search: {str(e)}"
        )]


async def main():
    """Run the Recoll MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="recoll-search",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
