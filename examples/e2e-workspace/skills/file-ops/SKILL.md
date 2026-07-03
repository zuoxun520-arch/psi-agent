---
name: file-ops
description: "File operations via MCP — read, write, edit (patch), search (grep), list directories."
---

# File Operations (Filesystem MCP)

Use the FS MCP server for all file interactions. One server covers read, write, edit (patch), search, and directory listing.

## Quick start

```
# Discover tools
call_mcp("FS", "list_mcp_tools", "")

# Expected tools:
# read_file, write_file, edit_file, search_files, list_directory,
# create_directory, move_file, directory_tree, ...
```

## Common patterns

### Read a file
```
call_mcp("FS", "read_file", '{"path": "/absolute/path/to/file.py"}')
```

### Write a file (create or overwrite)
```
call_mcp("FS", "write_file", '{"path": "/absolute/path/to/output.txt", "content": "file contents here"}')
```

### Edit a file (patch — exact string replacement)
```
call_mcp("FS", "edit_file", '{"path": "/path/to/file", "edits": [{"oldText": "line to replace", "newText": "new line content"}]}')
```

### Search files (grep/regex)
```
call_mcp("FS", "search_files", '{"path": "/project/src", "pattern": "TODO|FIXME", "fileTypes": ".py"}')
```

### List directory
```
call_mcp("FS", "list_directory", '{"path": "/project/src"}')
```

### Directory tree
```
call_mcp("FS", "directory_tree", '{"path": "/project"}')
```

## Editing workflow
1. `read_file` to see current content
2. `edit_file` with exact `oldText` / `newText` pair
3. `read_file` again to verify the change

## Search workflow
1. Start broad: `search_files` with a pattern
2. Narrow down: `read_file` on hits
3. Refine: more specific pattern if needed

## Requirements
- Node.js must be installed.
- Configure: `MCP_FS_COMMAND="npx"` and `MCP_FS_ARGS='["-y", "@modelcontextprotocol/server-filesystem", "/allowed/directory"]'`.
- The directory in ARGS is the root that FS can access. Set it to a broad enough path.
