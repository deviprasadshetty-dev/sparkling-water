"""Virtual File System for progressive disclosure and context management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import asyncio
from datetime import datetime
from ..graph.knowledge_graph import KnowledgeGraph, CodeNode


@dataclass
class FileView:
    """Represents a view of a file with progressive disclosure."""

    file_path: str
    signatures_only: bool = True
    expanded_functions: Set[str] = field(default_factory=set)
    expanded_classes: Set[str] = field(default_factory=set)
    last_accessed: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "signatures_only": self.signatures_only,
            "expanded_functions": list(self.expanded_functions),
            "expanded_classes": list(self.expanded_classes),
            "last_accessed": self.last_accessed.isoformat(),
        }


class VirtualFileSystem:
    """Virtual File System for progressive disclosure."""

    def __init__(self, knowledge_graph: KnowledgeGraph, root_path: str = "."):
        self.knowledge_graph = knowledge_graph
        self.root_path = Path(root_path).resolve()
        self.file_views: Dict[str, FileView] = {}
        self.file_cache: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._token_savings: Dict[str, int] = {}

    async def read_file(
        self,
        file_path: str,
        expand_function: Optional[str] = None,
        expand_class: Optional[str] = None,
    ) -> str:
        """Read a file with progressive disclosure."""
        # Resolve path relative to root
        resolved_path = self._resolve_path(file_path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get or create file view
        async with self._lock:
            if resolved_path.as_posix() not in self.file_views:
                self.file_views[resolved_path.as_posix()] = FileView(
                    file_path=resolved_path.as_posix()
                )

            file_view = self.file_views[resolved_path.as_posix()]
            file_view.last_accessed = datetime.utcnow()

        # Expand specific function or class if requested
        if expand_function:
            file_view.expanded_functions.add(expand_function)
        if expand_class:
            file_view.expanded_classes.add(expand_class)

        # Generate view
        return await self._generate_view(resolved_path, file_view)

    async def _generate_view(self, file_path: Path, file_view: FileView) -> str:
        """Generate the progressive disclosure view of a file."""
        # Get all nodes for this file
        nodes = await self.knowledge_graph.query_nodes(file_path=file_path.as_posix())

        # Group nodes by type
        functions = [n for n in nodes if n.type == "function"]
        classes = [n for n in nodes if n.type == "class"]
        imports = [n for n in nodes if n.type == "import"]

        # Build view
        view_lines = []

        # Add imports
        for imp in sorted(imports, key=lambda x: x.line_start):
            view_lines.append(f"# Line {imp.line_start}: {imp.name}")

        view_lines.append("")

        # Add classes
        for cls in sorted(classes, key=lambda x: x.line_start):
            if cls.name in file_view.expanded_classes:
                # Full class view
                view_lines.append(f"# Class: {cls.name} (lines {cls.line_start}-{cls.line_end})")
                if cls.signature:
                    view_lines.append(cls.signature)
                view_lines.append("")
            else:
                # Signature only
                view_lines.append(f"# Class: {cls.name} (lines {cls.line_start}-{cls.line_end})")
                if cls.docstring:
                    view_lines.append(f"    # {cls.docstring}")
                view_lines.append("")

        # Add functions
        for func in sorted(functions, key=lambda x: x.line_start):
            if func.name in file_view.expanded_functions:
                # Full function view
                view_lines.append(
                    f"# Function: {func.name} (lines {func.line_start}-{func.line_end})"
                )
                if func.signature:
                    view_lines.append(func.signature)
                view_lines.append("")
            else:
                # Signature only
                view_lines.append(
                    f"# Function: {func.name} (lines {func.line_start}-{func.line_end})"
                )
                if func.docstring:
                    view_lines.append(f"    # {func.docstring}")
                view_lines.append("")

        # Calculate token savings
        original_content = file_path.read_text(encoding="utf-8")
        view_content = "\n".join(view_lines)

        # Estimate token savings (rough approximation: 1 token ≈ 4 characters)
        original_tokens = len(original_content) // 4
        view_tokens = len(view_content) // 4
        savings = original_tokens - view_tokens

        if savings > 0:
            self._token_savings[file_path.as_posix()] = savings

        return view_content

    async def expand_function(self, file_path: str, function_name: str) -> str:
        """Expand a specific function in the file view."""
        resolved_path = self._resolve_path(file_path)
        async with self._lock:
            if resolved_path.as_posix() in self.file_views:
                self.file_views[resolved_path.as_posix()].expanded_functions.add(function_name)

        return await self.read_file(resolved_path.as_posix())

    async def expand_class(self, file_path: str, class_name: str) -> str:
        """Expand a specific class in the file view."""
        resolved_path = self._resolve_path(file_path)
        async with self._lock:
            if resolved_path.as_posix() in self.file_views:
                self.file_views[resolved_path.as_posix()].expanded_classes.add(class_name)

        return await self.read_file(resolved_path.as_posix())

    async def collapse_function(self, file_path: str, function_name: str) -> str:
        """Collapse a specific function in the file view."""
        resolved_path = self._resolve_path(file_path)
        async with self._lock:
            if resolved_path.as_posix() in self.file_views:
                self.file_views[resolved_path.as_posix()].expanded_functions.discard(function_name)

        return await self.read_file(resolved_path.as_posix())

    async def collapse_class(self, file_path: str, class_name: str) -> str:
        """Collapse a specific class in the file view."""
        resolved_path = self._resolve_path(file_path)
        async with self._lock:
            if resolved_path.as_posix() in self.file_views:
                self.file_views[resolved_path.as_posix()].expanded_classes.discard(class_name)

        return await self.read_file(resolved_path.as_posix())

    async def list_directory(self, path: str = ".") -> List[str]:
        """List directory contents."""
        resolved_path = self._resolve_path(path)
        if not resolved_path.exists() or not resolved_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        contents = []
        for item in resolved_path.iterdir():
            if item.is_dir():
                contents.append(f"{item.name}/")
            else:
                contents.append(item.name)

        return sorted(contents)

    async def get_file_stats(self, file_path: str) -> Dict[str, any]:
        """Get file statistics."""
        resolved_path = self._resolve_path(file_path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = resolved_path.stat()

        # Get token savings if available
        savings = self._token_savings.get(resolved_path.as_posix(), 0)

        return {
            "path": resolved_path.as_posix(),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "token_savings": savings,
            "is_directory": resolved_path.is_dir(),
        }

    async def get_token_savings(self) -> Dict[str, int]:
        """Get total token savings across all files."""
        return self._token_savings.copy()

    async def clear_cache(self) -> None:
        """Clear file cache."""
        async with self._lock:
            self.file_cache.clear()
            self.file_views.clear()
            self._token_savings.clear()

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the root."""
        resolved = (self.root_path / path).resolve()

        # Ensure the resolved path is within the root
        try:
            resolved.relative_to(self.root_path)
        except ValueError:
            raise ValueError(f"Path {path} is outside the root directory")

        return resolved

    async def get_file_view(self, file_path: str) -> Optional[FileView]:
        """Get the current view of a file."""
        resolved_path = self._resolve_path(file_path)
        async with self._lock:
            return self.file_views.get(resolved_path.as_posix())

    async def set_signatures_only(self, file_path: str, signatures_only: bool) -> str:
        """Set whether to show only signatures for a file."""
        resolved_path = self._resolve_path(file_path)
        async with self._lock:
            if resolved_path.as_posix() in self.file_views:
                self.file_views[resolved_path.as_posix()].signatures_only = signatures_only
                if not signatures_only:
                    # Expand everything
                    self.file_views[resolved_path.as_posix()].expanded_functions.clear()
                    self.file_views[resolved_path.as_posix()].expanded_classes.clear()

        return await self.read_file(resolved_path.as_posix())
