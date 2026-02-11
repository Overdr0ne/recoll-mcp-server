# Recoll MCP Server

Natural language interface to your Recoll-indexed filesystem through Claude Desktop.

## Overview

This MCP (Model Context Protocol) server gives Claude AI access to your Recoll search index, enabling natural language queries of your entire indexed filesystem.

## Features

- **Natural Language Search**: Ask Claude to find files using plain English
- **Advanced Filtering**: Search by date range, file type, and more
- **Content Access**: Retrieve full document contents
- **Recent Files**: List recently modified files
- **Fast**: Direct access to Xapian index via Recoll Python API

## Requirements

- Python 3.10+
- Recoll (with Python bindings)
- Claude Desktop
- MCP Python SDK

## Installation

1. Install dependencies:
```bash
pip install mcp
# Recoll Python bindings are usually included with recoll package
```

2. Configure Claude Desktop:

Edit `~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "recoll-search": {
      "command": "python3",
      "args": [
        "/home/sam/src/recoll-mcp-server/recoll_mcp_server.py"
      ],
      "env": {
        "RECOLL_CONFDIR": "/home/sam/.config/recoll"
      }
    }
  }
}
```

3. Restart Claude Desktop

## Usage Examples

Once configured, you can ask Claude:

- "Find my notes about YubiKey from December"
- "Search for PDFs containing 'machine learning'"
- "Show me files I modified this week"
- "Find markdown files about Nextcloud"

## Available Tools

### search_filesystem
Search using keywords or phrases with Boolean operators (AND, OR, NOT).

### search_by_date
Filter results by modification date range.

### search_by_filetype
Filter by file type/mimetype (pdf, markdown, text, etc.).

### get_document_content
Retrieve full content of a specific document.

### list_recent_files
List recently modified files in the index.

## Development

Test the Recoll API directly:
```bash
python test_recoll_api.py
```

## Architecture

```
User (natural language)
    ↓
Claude Desktop (with MCP)
    ↓
Recoll MCP Server (Python)
    ↓
Recoll Python API
    ↓
Xapian Index (your filesystem)
```

## License

Apache 2.0
