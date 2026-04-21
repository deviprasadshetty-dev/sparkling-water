"""Tool definitions for the AI agent."""

from typing import List, Dict, Any

TOOLS = [
    {
        "name": "list_files",
        "description": "List files in a directory",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the directory (default: current directory)",
                }
            },
        },
    },
    {
        "name": "read_file",
        "description": "Read a file with progressive disclosure. Shows a structural view (signatures) by default. Use expand_function or expand_line to see specific implementation.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
                "expand_function": {
                    "type": "string",
                    "description": "Name of a function to fully expand and read",
                },
                "expand_class": {
                    "type": "string",
                    "description": "Name of a class to fully expand and read",
                },
                "expand_line": {
                    "type": "integer",
                    "description": "A specific line number to expand with surrounding context",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Number of lines of context to show around expand_line (default: 5)",
                }
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "query_graph",
        "description": "Query the knowledge graph for code entities (functions, classes, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "node_type": {
                    "type": "string",
                    "enum": ["function", "class", "import"],
                    "description": "Type of code entity to search for",
                },
                "name_pattern": {
                    "type": "string",
                    "description": "Partial name of the entity to find",
                },
            },
        },
    },
    {
        "name": "edit_code",
        "description": "Edit code in a file using AST-based surgical modification",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "target_function": {"type": "string", "description": "Name of the function to edit"},
                "target_class": {"type": "string", "description": "Name of the class to edit"},
                "new_content": {"type": "string", "description": "The new code content"},
            },
            "required": ["file_path", "new_content"],
        },
    },
    {
        "name": "write_file",
        "description": "Write a completely new file or overwrite an existing one",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "delete_path",
        "description": "Delete a file, folder, function, or class.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file or directory to delete"},
                "target_function": {"type": "string", "description": "Name of the function to delete within a file"},
                "target_class": {"type": "string", "description": "Name of the class to delete within a file"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "rename_path",
        "description": "Rename or move a file or directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "old_path": {"type": "string", "description": "Current path"},
                "new_path": {"type": "string", "description": "New path"},
            },
            "required": ["old_path", "new_path"],
        },
    },
    {
        "name": "create_directory",
        "description": "Create a new directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the directory to create"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command in the terminal.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "search_text",
        "description": "Search for a string across all files (grep).",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "The text pattern to search for"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo (no API key required).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_knowledge",
        "description": "Save project details to .sw/knowledge/.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Markdown filename"},
                "content": {"type": "string", "description": "Markdown content"},
            },
            "required": ["filename", "content"],
        },
    }
]
