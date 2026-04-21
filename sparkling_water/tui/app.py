"""Breakthrough TUI for Sparkling Water."""

import asyncio
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import json
import re
import uuid
import subprocess
import shutil
from duckduckgo_search import DDGS

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, RichLog, Tree, Label, LoadingIndicator, TabbedContent, TabPane, Select
from textual.binding import Binding
from textual.reactive import reactive
from textual.worker import Worker, WorkerState
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED

from ..events.event_bus import EventBus, Event, EventType, Orchestrator
from ..graph.knowledge_graph import KnowledgeGraph
from ..vfs.virtual_filesystem import VirtualFileSystem
from ..router.slm_router import SLMRouter, Task, TaskType
from ..router.tools import TOOLS
from ..core.code_editor import CodeEditor
from ..core.project import ProjectManager
from ..providers import ProviderManager, ModelTier


class SparklingWaterTUI(App):
    """A modern, fast, and accurate AI coding agent TUI."""

    CSS = """
    Screen { background: #1a1b26; }
    #side-bar { width: 30; background: #24283b; border-right: solid #414868; }
    #main-content { width: 1fr; height: 1fr; }
    #chat-container { height: 1fr; padding: 1; background: #1a1b26; }
    #chat-log { height: 1fr; background: #1a1b26; border: none; }
    #input-container { height: 3; border-top: solid #414868; padding-top: 1; }
    #user-input { background: #24283b; border: none; }
    .user-msg { color: #9ece6a; font-weight: bold; }
    .assistant-msg { color: #bb9af7; }
    .tool-msg { color: #e0af68; italic: true; }
    #status-bar { height: 1; background: #24283b; color: #565f89; padding-left: 1; }
    #plan-pane, #diff-pane, #search-pane { background: #1a1b26; padding: 1; overflow-y: auto; }
    #model-select { margin: 1; height: 3; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("ctrl+r", "reindex", "Reindex"),
    ]

    def __init__(self, codebase_path: str = "."):
        super().__init__()
        self.codebase_path = Path(codebase_path).resolve()
        self.project_manager = ProjectManager(str(self.codebase_path))
        self.project_manager.initialize()
        self.knowledge_graph = KnowledgeGraph(db_path=str(self.project_manager.sw_dir / "knowledge_graph.db"))
        self.provider_manager = ProviderManager()
        self.router = SLMRouter(provider_manager=self.provider_manager)
        self.code_editor = CodeEditor()
        self.chat_history = []
        self.tokens_in = self.tokens_out = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="side-bar"):
                yield Label("[bold cyan] 🤖 Model[/bold cyan]")
                yield Select([], id="model-select")
                yield Label("[bold cyan] 📂 Project[/bold cyan]")
                yield Tree("Codebase", id="file-tree")
                yield Label("\n[bold cyan] 📊 Session[/bold cyan]")
                yield Static("Tokens: 0 / 0", id="token-stats")
                yield Label("\n[bold cyan] 🧠 Knowledge[/bold cyan]")
                yield Static("Entities: 0", id="kg-stats")
            with Vertical(id="main-content"):
                with TabbedContent():
                    with TabPane("💬 Chat", id="chat-tab"):
                        with Vertical(id="chat-container"):
                            yield RichLog(id="chat-log", wrap=True, highlight=True, markup=True)
                            with Horizontal(id="input-container"):
                                yield Input(placeholder="Ask Sparkling Water...", id="user-input")
                    with TabPane("📋 Plan", id="plan-tab"):
                        yield Static("No active plan.", id="plan-pane")
                    with TabPane("🔍 Diff", id="diff-tab"):
                        yield Static("No pending changes.", id="diff-pane")
                    with TabPane("🌐 Web", id="search-tab"):
                         yield Static("Web search results will appear here.", id="search-pane")
        yield Static("Ready", id="status-bar")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one("#chat-log").write("[bold blue]✨ Sparkling Water Breakthrough initialized.[/bold blue]")
        try:
            models = await self.provider_manager.get_all_models()
            options = [(f"{p}: {m.name}", f"{p}:{m.id}") for p, ml in models.items() for m in ml]
            self.query_one("#model-select").set_options(options)
            if options: self.query_one("#model-select").value = next((o[1] for o in options if "OpenRouter" in o[0]), options[0][1])
        except: pass
        self.run_worker(self.auto_index())

    async def auto_index(self):
        self.update_status("Indexing...")
        await self.knowledge_graph.initialize()
        files = list(self.codebase_path.rglob("*.py"))
        for f in files:
            try: await self.knowledge_graph.index_file(str(f), f.read_text(encoding="utf-8"))
            except: pass
        self.vfs = VirtualFileSystem(knowledge_graph=self.knowledge_graph, root_path=self.codebase_path)
        stats = await self.knowledge_graph.get_stats()
        self.query_one("#kg-stats").update(f"Files: {stats['files']}\nEntities: {stats['nodes']}")
        self.update_status("Ready")
        self._refresh_tree()

    def _refresh_tree(self):
        tree = self.query_one("#file-tree")
        tree.clear()
        for item in sorted(self.codebase_path.iterdir()):
            if item.name.startswith('.'): continue
            if item.is_dir(): tree.root.add(item.name, expand=False)
            else: tree.root.add_leaf(item.name)

    def update_status(self, msg: str): self.query_one("#status-bar").update(msg)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        if not user_input: return
        self.query_one("#user-input").value = ""
        self.query_one("#chat-log").write(f"\n[user-msg]✨ You:[/user-msg] {user_input}")
        self.run_worker(self.agent_loop(user_input))

    async def agent_loop(self, user_input: str):
        self.chat_history.append({"role": "user", "content": user_input})
        selected = self.query_one("#model-select").value
        force_p = force_m = None
        if selected and ":" in selected: force_p, force_m = selected.split(":", 1)

        current_messages = [{"role": "system", "content": self._get_system_prompt()}, *self.chat_history[-10:]]

        for i in range(15):
            self.update_status(f"Thinking ({i+1})...")
            self.tokens_in += sum(len(m['content']) // 4 for m in current_messages)

            if force_p and force_m:
                provider = self.provider_manager.providers.get(force_p)
                response = await provider.chat_completion(model=force_m, messages=current_messages)
            else:
                response = await self.provider_manager.chat_completion(messages=current_messages)

            self.tokens_out += len(response) // 4
            self.query_one("#token-stats").update(f"Tokens: {self.tokens_in} / {self.tokens_out}")

            plan_match = re.search(r"PLAN:(.*?)(?=```|Tool Call:|$)", response, re.S | re.I)
            if plan_match: self.query_one("#plan-pane").update(Markdown(plan_match.group(1).strip()))

            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.S)
            if json_match:
                try:
                    tool_call = json.loads(json_match.group(1))
                    t_name, t_args = tool_call.get("tool"), tool_call.get("args", {})
                    self.query_one("#chat-log").write(f"[tool-msg]🔧 Call:[/tool-msg] [cyan]{t_name}[/cyan]")
                    result = await self.execute_tool(t_name, t_args)
                    self._show_result(t_name, result)
                    current_messages.append({"role": "assistant", "content": response})
                    current_messages.append({"role": "system", "content": f"Tool result: {json.dumps(result)}"})
                    continue
                except Exception as e:
                    current_messages.append({"role": "system", "content": f"Error: {e}"})
                    continue

            self.query_one("#chat-log").write(f"\n[assistant-msg]🤖 Assistant:[/assistant-msg]")
            self.query_one("#chat-log").write(Markdown(response))
            self.chat_history.append({"role": "assistant", "content": response})
            break
        self.update_status("Ready")

    def _show_result(self, name: str, res: Any):
        log = self.query_one("#chat-log")
        if name == "read_file": log.write(Panel(Syntax(res, "python", theme="monokai"), border_style="dim"))
        elif name == "edit_code" or name == "write_file":
            if res.get("success"):
                log.write(f"✅ [green]Modified {res.get('modified_file')}[/green]")
                if "original_content" in res and "modified_content" in res:
                    diff = self._gen_diff(res["original_content"], res["modified_content"])
                    self.query_one("#diff-pane").update(Syntax(diff, "diff", theme="monokai"))
            else: log.write(f"❌ [red]Error: {res.get('error') or res.get('syntax_error')}[/red]")
        elif name == "web_search":
             res_md = "\n\n".join([f"### [{r['title']}]({r['href']})\n{r['body']}" for r in res])
             self.query_one("#search-pane").update(Markdown(res_md))
             log.write(f"🌐 [blue]Found {len(res)} web results (see Web tab).[/blue]")
        else: log.write(f"[tool-msg]✅ Result:[/tool-msg] {str(res)[:100]}...")

    def _gen_diff(self, old: str, new: str) -> str:
        import difflib
        return "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile="before", tofile="after"))

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        try:
            if name == "list_files": return await self.vfs.list_directory(args.get("path", "."))
            elif name == "read_file": return await self.vfs.read_file(args.get("file_path"), args.get("expand_function"), expand_line=args.get("expand_line"))
            elif name == "query_graph": return [n.to_dict() for n in await self.knowledge_graph.query_nodes(name_pattern=args.get("name_pattern"))]
            elif name == "edit_code":
                intent = await self.code_editor.create_edit_intent(operation="edit", **args)
                return (await self.code_editor.edit_code(intent)).to_dict()
            elif name == "write_file": return (await self.code_editor.write_file(args.get("file_path"), args.get("content"))).to_dict()
            elif name == "delete_path":
                p = Path(args.get("path"))
                if p.is_file(): p.unlink(); return "File deleted."
                elif p.is_dir(): shutil.rmtree(p); return "Directory deleted."
                return "Path not found."
            elif name == "rename_path": os.rename(args.get("old_path"), args.get("new_path")); return "Renamed."
            elif name == "create_directory": Path(args.get("path")).mkdir(parents=True, exist_ok=True); return "Created."
            elif name == "run_command":
                p = await asyncio.create_subprocess_shell(args.get("command"), stdout=-1, stderr=-1)
                o, e = await p.communicate()
                return {"exit_code": p.returncode, "stdout": o.decode(), "stderr": e.decode()}
            elif name == "web_search":
                with DDGS() as ddgs: return [r for r in ddgs.text(args.get("query"), max_results=5)]
            elif name == "save_knowledge": self.project_manager.save_knowledge(args.get("filename"), args.get("content")); return "Saved."
            else: return f"Unknown tool: {name}"
        except Exception as e: return str(e)

    def _get_system_prompt(self) -> str:
        return f"""You are Sparkling Water, an elite AI coding agent.
{json.dumps(TOOLS)}
1. EXPLORE: list_files/query_graph.
2. PLAN: State PLAN.
3. EXECUTE: JSON block for tool.
4. VERIFY: Read/Test.
Be brief, fast, and token-efficient. Use save_knowledge for project details.
"""

    def action_clear_chat(self): self.query_one("#chat-log").clear(); self.chat_history = []
    def action_reindex(self): self.run_worker(self.auto_index())

if __name__ == "__main__": SparklingWaterTUI().run()
