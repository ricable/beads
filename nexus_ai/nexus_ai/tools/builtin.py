"""
NexusAI Built-in Tools

Standard tools available to all agents:
- Search: Web and code search
- Code Interpreter: Execute code safely
- File Operations: Read/write files
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


async def search_tool(
    query: str,
    search_type: str = "web",
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Search tool for web and code search.

    Args:
        query: Search query
        search_type: Type of search (web, code, docs)
        max_results: Maximum number of results

    Returns:
        Search results
    """
    # Mock implementation
    return {
        "query": query,
        "type": search_type,
        "results": [
            {
                "title": f"Result {i + 1} for: {query}",
                "snippet": f"This is a mock result for '{query}'...",
                "url": f"https://example.com/result{i + 1}",
            }
            for i in range(min(max_results, 3))
        ],
    }


search_tool.schema = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"},
        "search_type": {
            "type": "string",
            "enum": ["web", "code", "docs"],
            "description": "Type of search",
        },
        "max_results": {"type": "integer", "description": "Max results to return"},
    },
    "required": ["query"],
}


async def code_interpreter_tool(
    code: str,
    language: str = "python",
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Execute code in a sandboxed environment.

    Args:
        code: Code to execute
        language: Programming language
        timeout: Execution timeout in seconds

    Returns:
        Execution result with stdout, stderr, and return value
    """
    # Mock implementation - in production, use gVisor or similar
    if language != "python":
        return {
            "success": False,
            "error": f"Language '{language}' not supported",
        }

    try:
        # WARNING: This is unsafe - production should use sandboxed execution
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        local_vars: dict[str, Any] = {}

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(code, {"__builtins__": __builtins__}, local_vars)

        return {
            "success": True,
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "variables": {k: str(v)[:100] for k, v in local_vars.items() if not k.startswith("_")},
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


code_interpreter_tool.schema = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "Code to execute"},
        "language": {
            "type": "string",
            "enum": ["python"],
            "description": "Programming language",
        },
        "timeout": {"type": "integer", "description": "Timeout in seconds"},
    },
    "required": ["code"],
}


async def file_operations_tool(
    operation: str,
    path: str,
    content: str | None = None,
) -> dict[str, Any]:
    """
    File system operations.

    Args:
        operation: Operation type (read, write, list, exists)
        path: File path
        content: Content for write operations

    Returns:
        Operation result
    """
    file_path = Path(path)

    try:
        if operation == "read":
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            return {
                "success": True,
                "content": file_path.read_text()[:10000],  # Limit size
                "size": file_path.stat().st_size,
            }

        elif operation == "write":
            if content is None:
                return {"success": False, "error": "Content required for write"}
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return {
                "success": True,
                "path": str(file_path),
                "size": len(content),
            }

        elif operation == "list":
            if not file_path.exists():
                return {"success": False, "error": "Path not found"}
            if file_path.is_file():
                return {"success": True, "files": [str(file_path)]}
            return {
                "success": True,
                "files": [str(p) for p in file_path.iterdir()][:100],
            }

        elif operation == "exists":
            return {
                "success": True,
                "exists": file_path.exists(),
                "is_file": file_path.is_file() if file_path.exists() else False,
                "is_dir": file_path.is_dir() if file_path.exists() else False,
            }

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


file_operations_tool.schema = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["read", "write", "list", "exists"],
            "description": "File operation type",
        },
        "path": {"type": "string", "description": "File path"},
        "content": {"type": "string", "description": "Content for write operation"},
    },
    "required": ["operation", "path"],
}
