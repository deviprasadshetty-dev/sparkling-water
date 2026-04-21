"""Virtual File System for progressive disclosure and context management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
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
    expanded_ranges: List[Tuple[int, int]] = field(default_factory=list)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    original_size: int = 0
    original_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "signatures_only": self.signatures_only,
            "expanded_functions": list(self.expanded_functions),
            "expanded_classes": list(self.expanded_classes),
            "expanded_ranges": self.expanded_ranges,
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
        expand_line: Optional[int] = None,
        context_lines: int = 5
    ) -> str:
        """Read a file with progressive disclosure."""
        # Resolve path relative to root
        resolved_path = self._resolve_path(file_path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get or create file view
        async with self._lock:
            if resolved_path.as_posix() not in self.file_views:
                stat = resolved_path.stat()
                try:
                    content_hint = ""
                    if stat.st_size < 1024 * 1024:
                        content_hint = resolved_path.read_text(encoding="utf-8")

                    self.file_views[resolved_path.as_posix()] = FileView(
                        file_path=resolved_path.as_posix(),
                        original_size=stat.st_size,
                        original_tokens=len(content_hint) // 4 if content_hint else stat.st_size // 4
                    )
                except:
                    self.file_views[resolved_path.as_posix()] = FileView(
                        file_path=resolved_path.as_posix(),
                        original_size=stat.st_size,
                        original_tokens=stat.st_size // 4
                    )

            file_view = self.file_views[resolved_path.as_posix()]
            file_view.last_accessed = datetime.utcnow()

        # Update view based on requests
        if expand_function:
            file_view.expanded_functions.add(expand_function)
        if expand_class:
            file_view.expanded_classes.add(expand_class)
        if expand_line is not None:
            start = max(1, expand_line - context_lines)
            end = expand_line + context_lines
            file_view.expanded_ranges.append((start, end))

        # Generate view
        return await self._generate_view(resolved_path, file_view)

    async def _generate_view(self, file_path: Path, file_view: FileView) -> str:
        """Generate the progressive disclosure view of a file."""
        nodes = await self.knowledge_graph.query_nodes(file_path=file_path.as_posix())

        full_content_lines = file_path.read_text(encoding="utf-8").splitlines()
        total_lines = len(full_content_lines)

        if not nodes and not file_view.expanded_ranges:
            # Fallback to snippet if not indexed
            snippet = "\n".join(full_content_lines[:50])
            if total_lines > 50: snippet += f"\n... ({total_lines - 50} more lines)"
            return snippet

        # Build visibility map
        visible = [False] * (total_lines + 1)

        # Ranges
        for start, end in file_view.expanded_ranges:
            for i in range(max(1, start), min(total_lines + 1, end + 1)):
                visible[i] = True

        # Group nodes
        functions = [n for n in nodes if n.type == "function"]
        classes = [n for n in nodes if n.type == "class"]

        # Build view
        view_lines = []

        # We'll use a structural view for everything NOT in expanded ranges
        last_yielded = 0

        # Sort all structural markers
        markers = []
        for n in nodes:
            markers.append((n.line_start, 'start', n))
            markers.append((n.line_end, 'end', n))
        markers.sort()

        # This is a bit complex for a simple VFS, let's keep it clean
        # Rule: If line is visible, show it. Otherwise, if it's a start of a function/class, show signature.

        for i in range(1, total_lines + 1):
            line_content = full_content_lines[i-1]

            if visible[i]:
                view_lines.append(f"{i:4} | {line_content}")
                last_yielded = i
            else:
                # Is it a start of an entity?
                node = next((n for n in nodes if n.line_start == i), None)
                if node:
                    if node.type == "function":
                        if node.name in file_view.expanded_functions:
                            # Auto-expand if requested
                            for j in range(node.line_start, node.line_end + 1): visible[j] = True
                            view_lines.append(f"{i:4} | {line_content} (EXPANDED)")
                        else:
                            view_lines.append(f"{i:4} | def {node.name}(...): ... # {node.line_end - node.line_start + 1} lines")
                    elif node.type == "class":
                         if node.name in file_view.expanded_classes:
                            for j in range(node.line_start, node.line_end + 1): visible[j] = True
                            view_lines.append(f"{i:4} | {line_content} (EXPANDED)")
                         else:
                            view_lines.append(f"{i:4} | class {node.name}: ...")
                else:
                    # Generic ellipsis if we skipped lines
                    if view_lines and not view_lines[-1].startswith("..."):
                        view_lines.append("    ...")

        # Dedup ellipsis
        final_view = []
        for line in view_lines:
            if line == "    ..." and final_view and final_view[-1] == "    ...":
                continue
            final_view.append(line)

        return "\n".join(final_view)

    async def list_directory(self, path: str = ".") -> List[str]:
        """List directory contents."""
        resolved_path = self._resolve_path(path)
        if not resolved_path.exists() or not resolved_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        contents = []
        for item in resolved_path.iterdir():
            if item.name.startswith('.'): continue
            if item.is_dir():
                contents.append(f"{item.name}/")
            else:
                contents.append(item.name)

        return sorted(contents)

    async def get_file_stats(self, file_path: str) -> Dict[str, Any]:
        """Get file statistics."""
        resolved_path = self._resolve_path(file_path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = resolved_path.stat()
        return {
            "path": resolved_path.as_posix(),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_directory": resolved_path.is_dir(),
        }

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the root."""
        try:
            resolved = (self.root_path / path).resolve()
            resolved.relative_to(self.root_path)
            return resolved
        except:
            return (self.root_path / Path(path).name).resolve()
