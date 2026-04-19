# OpenRouter Setup Guide

This guide will help you configure Sparkling Water to use OpenRouter as your AI provider.

## Prerequisites

1. **OpenRouter Account**: Sign up at [https://openrouter.ai](https://openrouter.ai)
2. **API Key**: Get your API key from [https://openrouter.ai/keys](https://openrouter.ai/keys)
3. **Credits**: Add credits to your OpenRouter account

## Quick Setup (3 Methods)

### Method 1: Interactive CLI (Recommended)

```bash
# Start the interactive CLI
python -m sparkling_water.cli.main chat

# Configure OpenRouter
/config OpenRouter your-api-key-here

# Select a model
/select OpenRouter openai/gpt-4o-mini slm

# Start using it
Write a function to authenticate users
```

### Method 2: Environment Variables

Create a `.env` file in your project root:

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Model Selection
SLM_MODEL=openai/gpt-4o-mini
FRONTIER_MODEL=anthropic/claude-3.5-sonnet

# Database Configuration
DATABASE_PATH=:memory:

# Performance Configuration
MAX_CONTEXT_TOKENS=4000
ENABLE_PROGRESSIVE_DISCLOSURE=true
```

### Method 3: Configuration File

Create a `.sparkling_water_providers.json` file in your home directory:

```json
{
  "providers": {
    "OpenRouter": {
      "api_key": "your-openrouter-api-key-here",
      "enabled": true,
      "primary_model": "openai/gpt-4o-mini",
      "secondary_model": "anthropic/claude-3.5-sonnet"
    }
  },
  "model_selection": {
    "primary_provider": "OpenRouter",
    "primary_model": "openai/gpt-4o-mini",
    "secondary_provider": "OpenRouter",
    "secondary_model": "anthropic/claude-3.5-sonnet"
  }
}
```

## Available OpenRouter Models

### SLM (Small Language Models) - Fast & Cheap

| Model | ID | Cost (per 1K tokens) | Context |
|-------|-----|---------------------|---------|
| GPT-4o Mini | `openai/gpt-4o-mini` | $0.00015 / $0.0006 | 128K |
| Llama 3.1 8B | `meta-llama/llama-3.1-8b-instruct` | $0.00005 / $0.00005 | 128K |
| Mistral 7B | `mistralai/mistral-7b-instruct` | $0.00007 / $0.00007 | 32K |

### Medium Models - Balanced Performance

| Model | ID | Cost (per 1K tokens) | Context |
|-------|-----|---------------------|---------|
| GPT-4o | `openai/gpt-4o` | $0.005 / $0.015 | 128K |
| Claude 3.5 Sonnet | `anthropic/claude-3.5-sonnet` | $0.003 / $0.015 | 200K |
| Llama 3.1 70B | `meta-llama/llama-3.1-70b-instruct` | $0.00059 / $0.00079 | 128K |

### Frontier Models - Maximum Capability

| Model | ID | Cost (per 1K tokens) | Context |
|-------|-----|---------------------|---------|
| GPT-4 Turbo | `openai/gpt-4-turbo` | $0.01 / $0.03 | 128K |
| Claude 3 Opus | `anthropic/claude-3-opus` | $0.015 / $0.075 | 200K |
| Gemini Pro | `google/gemini-pro` | $0.0005 / $0.0015 | 32K |

## Recommended Configurations

### Budget-Friendly Setup

```bash
/config OpenRouter your-api-key-here
/select OpenRouter openai/gpt-4o-mini slm
```

**Cost**: ~$0.00075 per 1K tokens
**Best for**: Simple tasks, code generation, quick edits

### Balanced Performance

```bash
/config OpenRouter your-api-key-here
/select OpenRouter openai/gpt-4o medium
```

**Cost**: ~$0.01 per 1K tokens
**Best for**: Complex tasks, debugging, code analysis

### Maximum Capability

```bash
/config OpenRouter your-api-key-here
/select OpenRouter anthropic/claude-3.5-sonnet frontier
```

**Cost**: ~$0.018 per 1K tokens
**Best for**: Complex reasoning, architectural decisions, deep debugging

## Dual-Provider Setup

Use OpenRouter for SLM tasks and another provider for frontier tasks:

```bash
# Configure OpenRouter for SLM
/config OpenRouter your-openrouter-key-here

# Configure Claude for frontier
/config Claude your-anthropic-key-here

# Select dual setup
/select OpenRouter openai/gpt-4o-mini slm Claude claude-3-5-sonnet-20241022 frontier
```

## Testing Your Setup

```bash
# Start the CLI
python -m sparkling_water.cli.main chat

# Check provider status
/providers

# View available models
/models OpenRouter

# Test with a simple task
Write a function to calculate fibonacci numbers
```

## Cost Estimation

### Example: Codebase Analysis

**Task**: Analyze a 100-file codebase

**Traditional Approach**:
- Context: 412,000 tokens
- Cost (GPT-4o): $2.06

**Sparkling Water with OpenRouter**:
- Context: 3,400 tokens (99.2% reduction)
- Cost (GPT-4o Mini): $0.00255
- **Savings**: 99.9%

### Example: Code Generation

**Task**: Generate 10 functions

**Traditional Approach**:
- Context: 50,000 tokens
- Cost (GPT-4o): $0.25

**Sparkling Water with OpenRouter**:
- Context: 5,000 tokens (90% reduction)
- Cost (GPT-4o Mini): $0.00375
- **Savings**: 98.5%

## Troubleshooting

### API Key Not Working

```bash
# Verify your API key
/config OpenRouter your-api-key-here

# Check provider status
/providers

# Test with a simple query
/models OpenRouter
```

### Model Not Available

```bash
# Refresh model list
/models OpenRouter

# Try a different model
/select OpenRouter openai/gpt-4o-mini slm
```

### Rate Limiting

OpenRouter has rate limits based on your plan. If you encounter rate limiting:

1. Upgrade your OpenRouter plan
2. Use a cheaper model (SLM)
3. Implement retry logic in your code

## Advanced Configuration

### Custom Model Selection

```bash
# Select specific models for different tiers
/select OpenRouter meta-llama/llama-3.1-8b-instruct slm OpenRouter openai/gpt-4o medium
```

### Environment-Specific Configuration

Create different `.env` files for different environments:

```bash
# .env.development
OPENROUTER_API_KEY=dev-key-here
SLM_MODEL=openai/gpt-4o-mini

# .env.production
OPENROUTER_API_KEY=prod-key-here
SLM_MODEL=openai/gpt-4o
```

Load the appropriate environment:

```bash
# Development
export $(cat .env.development | xargs)
python -m sparkling_water.cli.main chat

# Production
export $(cat .env.production | xargs)
python -m sparkling_water.cli.main chat
```

## Monitoring Usage

OpenRouter provides usage statistics at [https://openrouter.ai/activity](https://openrouter.ai/activity)

Monitor your:
- Token usage
- Cost breakdown
- Model performance
- Rate limit status

## Best Practices

1. **Start with SLM**: Use `openai/gpt-4o-mini` for most tasks
2. **Upgrade when needed**: Switch to frontier models only for complex tasks
3. **Monitor costs**: Check OpenRouter dashboard regularly
4. **Use progressive disclosure**: Let Sparkling Water optimize context
5. **Cache results**: Enable caching for repeated queries

## Getting Help

- **OpenRouter Documentation**: [https://openrouter.ai/docs](https://openrouter.ai/docs)
- **OpenRouter Discord**: [https://discord.gg/openrouter](https://discord.gg/openrouter)
- **Sparkling Water Issues**: [https://github.com/deviprasadshetty-dev/sparkling-water-/issues](https://github.com/deviprasadshetty-dev/sparkling-water-/issues)

## Next Steps

1. ✅ Get your OpenRouter API key
2. ✅ Configure Sparkling Water with OpenRouter
3. ✅ Select your preferred model
4. ✅ Test with a simple task
5. ✅ Start coding smarter!

---

**Ready to get started?**

```bash
python -m sparkling_water.cli.main chat
/config OpenRouter your-api-key-here
/select OpenRouter openai/gpt-4o-mini slm
```

Happy coding! 🚀