"""Project manager for Sparkling Water."""

import os
from pathlib import Path
from typing import Optional

class ProjectManager:
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.sw_dir = self.root_path / ".sw"
        self.knowledge_dir = self.sw_dir / "knowledge"

    def initialize(self):
        """Initialize the .sw directory and .gitignore."""
        self.sw_dir.mkdir(exist_ok=True)
        self.knowledge_dir.mkdir(exist_ok=True)

        self._update_gitignore()

    def _update_gitignore(self):
        """Ensure .sw is in .gitignore."""
        gitignore = self.root_path / ".gitignore"
        content = ""
        if gitignore.exists():
            content = gitignore.read_text()

        if ".sw/" not in content:
            with open(gitignore, "a") as f:
                f.write("\n# Sparkling Water\n.sw/\n")

    def save_knowledge(self, filename: str, content: str):
        """Save project knowledge to a markdown file."""
        if not filename.endswith(".md"):
            filename += ".md"

        path = self.knowledge_dir / filename
        path.write_text(content, encoding="utf-8")

    def get_knowledge(self, filename: str) -> Optional[str]:
        """Get project knowledge from a markdown file."""
        if not filename.endswith(".md"):
            filename += ".md"

        path = self.knowledge_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def list_knowledge(self) -> list[str]:
        """List all knowledge files."""
        return [f.name for f in self.knowledge_dir.glob("*.md")]
