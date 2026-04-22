<div align="center">

# ✨ Sparkling Water

### Breakthrough AI Coding Assistant with AST-Based Intelligence & Modern TUI

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Automatically understand your codebase and work smarter, not harder.**

</div>

---

## 🚀 Breakthrough Features

- **LLM-Driven Agent Loop**: Autonomous reasoning and tool-calling for complex tasks.
- **Surgical AST Edits**: Accurate multi-line modifications using LibCST.
- **Modern TUI**: Professional "AI IDE" experience with real-time plans and diffs.
- **99% Token Efficiency**: VFS with progressive disclosure serves only what's needed.
- **Universal Providers**: Support for OpenAI, Anthropic, Gemini, and OpenRouter.

## 📦 Single-Command Installation

The recommended way to install Sparkling Water is via our professional installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/your-org/sparkling-water/main/install.sh | bash
```

Alternatively, you can install via pip:

```bash
pip install sparkling-water
```

Or for development:

```bash
git clone https://github.com/your-org/sparkling-water.git && cd sparkling-water && ./install.sh
```

## 💬 Usage

### Modern TUI (Default)
Launch the breakthrough TUI for a professional, multi-pane experience by simply running:
```bash
sw
```
Or specify a path:
```bash
sw ./my-project
```

### Interactive Chat (Legacy)
Start a conversation with the agent in legacy chat mode:
```bash
sw chat
```

## 🎓 Commands

```bash
sw [path]          # Launch breakthrough TUI (default)
sw chat [path]     # Start interactive legacy agent
sw index [path]    # Build knowledge graph
sw benchmark       # Compare efficiency
```

## 🔧 Configuration

Sparkling Water stores project details, plans, and persistent knowledge in the `.sw/` directory in your project root. This directory is automatically added to your `.gitignore`.

---

<div align="center">
Built with ❤️ for the next generation of developers.
</div>
