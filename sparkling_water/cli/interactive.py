"""Modern interactive CLI with LLM-driven agent loop."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json
import traceback
import re
import uuid
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.box import ROUNDED
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from duckduckgo_search import DDGS

from ..events.event_bus import EventBus, Event, EventType, Orchestrator
from ..graph.knowledge_graph import KnowledgeGraph
from ..vfs.virtual_filesystem import VirtualFileSystem
from ..router.slm_router import SLMRouter, Task, TaskType
from ..router.tools import TOOLS
from ..core.ast_transformer import ASTTransformationEngine
from ..core.code_editor import CodeEditor, EditIntent, EditOperation
from ..core.project import ProjectManager
from ..providers import ProviderManager, ModelTier


class SparklingWaterCLI:
    """Modern interactive CLI with LLM-driven agent loop."""

    def __init__(self, codebase_path: str = "."):
        self.console = Console()
        self.codebase_path = Path(codebase_path).resolve()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.project_manager = ProjectManager(str(self.codebase_path))
        self.project_manager.initialize()

        # Initialize components
        self.event_bus = EventBus()
        self.orchestrator = Orchestrator(self.event_bus)
        self.knowledge_graph = KnowledgeGraph(db_path=str(self.project_manager.sw_dir / "knowledge_graph.db"))
        self.vfs: Optional[VirtualFileSystem] = None
        self.provider_manager = ProviderManager()
        self.router = SLMRouter(provider_manager=self.provider_manager)
        self.code_editor = CodeEditor()

        # State
        self.indexing_task: Optional[asyncio.Task] = None
        self.indexed = False
        self.chat_history: List[Dict[str, Any]] = []

        # Prompt session
        self.history_file = Path.home() / ".sparkling_water_history"
        self.prompt_session = PromptSession(
            history=FileHistory(str(self.history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )

        # Style
        self.style = Style.from_dict({
            "prompt": "cyan bold",
        })

    def show_banner(self):
        banner = Text()
        banner.append("✨ ", style="bold yellow")
        banner.append("Sparkling Water", style="bold cyan")
        banner.append(" ✨\n", style="bold yellow")
        banner.append("Next-Generation AI Coding Agent", style="italic")

        self.console.print(Panel(banner, border_style="cyan", box=ROUNDED))
        self.console.print(f"[dim]Codebase: {self.codebase_path}[/dim]\n")

    async def auto_index_codebase(self):
        """Automatically index the codebase in the background."""
        await self.knowledge_graph.initialize()

        python_files = list(self.codebase_path.rglob("*.py"))
        if not python_files:
            self.indexed = True
            return

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                await self.knowledge_graph.index_file(str(file_path), content)
            except Exception:
                pass

        self.vfs = VirtualFileSystem(knowledge_graph=self.knowledge_graph, root_path=self.codebase_path)
        self.indexed = True

    async def run(self):
        self.show_banner()
        self.indexing_task = asyncio.create_task(self.auto_index_codebase())
        self.console.print("[bold cyan]How can I help you today?[/bold cyan]")
        self.console.print("[dim]I'm indexing your codebase in the background...[/dim]\n")

        while True:
            try:
                user_input = await self.prompt_session.prompt_async(
                    HTML('<style fg="ansicyan">✨ You</style>: ')
                )
                if not user_input.strip(): continue
                if user_input.lower() in ["exit", "quit"]: break
                await self.agent_loop(user_input)
            except KeyboardInterrupt: continue
            except EOFError: break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                traceback.print_exc()

    async def agent_loop(self, user_input: str):
        """Main LLM-driven agent loop."""
        if not self.indexed:
            with self.console.status("[bold yellow]Finishing indexing...[/bold yellow]"):
                await self.indexing_task

        correlation_id = str(uuid.uuid4())
        self.chat_history.append({"role": "user", "content": user_input})

        await self.orchestrator.publish_event(EventType.TASK_REQUESTED, {"input": user_input}, correlation_id=correlation_id)

        task = await self.router.create_task(user_input)
        decision = await self.router.route_task(task)

        current_messages = [
            {"role": "system", "content": self._get_system_prompt()},
            *self.chat_history[-10:]
        ]

        max_iterations = 15
        success = False
        try:
            for i in range(max_iterations):
                with self.console.status(f"[bold blue]Thinking (Iteration {i+1})...[/bold blue]"):
                    response = await self.provider_manager.chat_completion(
                        messages=current_messages,
                        use_secondary=(decision.model_tier == ModelTier.FRONTIER)
                    )

                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)

                if json_match:
                    try:
                        tool_call_json = json_match.group(1)
                        tool_call = json.loads(tool_call_json)
                        tool_name = tool_call.get("tool")
                        tool_args = tool_call.get("args", {})

                        if tool_name == "run_command":
                            cmd = tool_args.get("command", "")
                            confirm = await self.prompt_session.prompt_async(
                                HTML(f'<style fg="ansiyellow">⚠️ Allow command: {cmd}? (y/n)</style>: ')
                            )
                            if confirm.lower() != 'y':
                                result = "Command rejected by user."
                                current_messages.append({"role": "assistant", "content": response})
                                current_messages.append({"role": "system", "content": f"Tool result: {result}"})
                                continue

                        await self.orchestrator.publish_event(EventType.TOOL_CALL, {"tool": tool_name, "args": tool_args}, correlation_id=correlation_id)
                        self.console.print(f"🔧 [bold blue]Tool Call:[/bold blue] [cyan]{tool_name}[/cyan]")

                        result = await self.execute_tool(tool_name, tool_args)
                        await self.orchestrator.publish_event(EventType.TOOL_RESULT, {"tool": tool_name, "result": result}, correlation_id=correlation_id)
                        self._show_formatted_result(tool_name, result)

                        current_messages.append({"role": "assistant", "content": response})
                        current_messages.append({"role": "system", "content": f"Tool result: {json.dumps(result)}"})
                        continue
                    except Exception as e:
                        current_messages.append({"role": "assistant", "content": response})
                        current_messages.append({"role": "system", "content": f"Error: {e}"})
                        continue

                self.console.print(f"\n[bold blue]✨ Assistant:[/bold blue]")
                self.console.print(Markdown(response))
                self.chat_history.append({"role": "assistant", "content": response})
                success = True
                break
        except Exception as e:
            await self.orchestrator.publish_event(EventType.TASK_FAILED, {"error": str(e)}, correlation_id=correlation_id)
            raise

    def _show_formatted_result(self, tool_name: str, result: Any):
        if tool_name == "read_file" and isinstance(result, str):
            self.console.print(Panel(Syntax(result, "python", theme="monokai"), border_style="dim"))
        elif tool_name == "query_graph" and isinstance(result, list):
            table = Table(box=ROUNDED, border_style="dim")
            table.add_column("Type"); table.add_column("Name"); table.add_column("File")
            for node in result[:10]: table.add_row(node.get("type"), node.get("name"), node.get("file_path"))
            self.console.print(table)
        else:
            res_str = str(result)
            self.console.print(f"✅ [bold green]Result:[/bold green] {res_str[:200]}...")

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
Rules:
1. EXPLORE: list_files/query_graph.
2. PLAN: State PLAN.
3. EXECUTE: JSON block for tool.
4. VERIFY: Read/Test.
Keep thoughts brief. Use AST edits (edit_code) for precision.
"""
