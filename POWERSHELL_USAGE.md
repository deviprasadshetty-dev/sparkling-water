# Sparkling Water - PowerShell Usage Guide

Since you're running in PowerShell, the interactive `chat` command won't work (it requires cmd.exe). However, you can still use most of Sparkling Water's functionality!

## Working Commands in PowerShell

### 1. Demo
```bash
python -m sparkling_water.cli.main demo
```
Shows an overview of Sparkling Water capabilities.

### 2. Route Tasks
```bash
# Route a coding task
python -m sparkling_water.cli.main route "Write a function to authenticate users" --db :memory:

# Route a debugging task
python -m sparkling_water.cli.main route "Debug the payment processing error" --db :memory:

# Route a refactoring task
python -m sparkling_water.cli.main route "Optimize the database query" --db :memory:
```

### 3. Show Help
```bash
# Show all commands
python -m sparkling_water.cli.main --help

# Show help for specific command
python -m sparkling_water.cli.main route --help
```

## Commands with Limitations

### Index (Has Issues)
```bash
# This command has database initialization issues in PowerShell
python -m sparkling_water.cli.main index sparkling_water --db :memory:
```

### Chat (Requires cmd.exe)
```bash
# This won't work in PowerShell - requires cmd.exe
python -m sparkling_water.cli.main chat .
```

## For Interactive Chat

To use the interactive chat mode, you need to run it in cmd.exe:

```bash
# Open cmd.exe and run:
cd D:\brain\research\autonomius\modelrouter
python -m sparkling_water.cli.main chat .
```

## Your Current Configuration

Your `.env` file is configured with:
- **API Key**: OpenRouter (configured)
- **SLM Model**: `google/gemma-4-26b-a4b-it:free` (FREE!)
- **Frontier Model**: `google/gemma-4-31b-it:free` (FREE!)

## Testing Your Setup

```bash
# Test routing with different tasks
python -m sparkling_water.cli.main route "Create a user authentication system" --db :memory:
python -m sparkling_water.cli.main route "Add error handling to API" --db :memory:
python -m sparkling_water.cli.main route "Refactor database queries" --db :memory:
```

## Next Steps

1. ✅ Your OpenRouter API key is configured
2. ✅ FREE models are selected
3. ✅ Route command works in PowerShell
4. ⚠️ For interactive chat, use cmd.exe

## Alternative: Use Python Script

You can also create a Python script to use Sparkling Water programmatically:

```python
import asyncio
from sparkling_water.router.slm_router import SLMRouter

async def main():
    router = SLMRouter()
    task = await router.create_task("Write a function to authenticate users")
    decision = await router.route_task(task)
    print(f"Task: {task.description}")
    print(f"Model: {decision.model_tier.value}")
    print(f"Confidence: {decision.confidence}")

asyncio.run(main())
```

Save this as `test_sw.py` and run:
```bash
python test_sw.py
```

## Summary

**Works in PowerShell:**
- ✅ `demo` - Show capabilities
- ✅ `route` - Route tasks and show decisions
- ✅ `--help` - Show help

**Requires cmd.exe:**
- ❌ `chat` - Interactive mode
- ⚠️ `index` - Has database issues

**Your setup is ready!** Just use the `route` command to test task routing with your FREE OpenRouter models.