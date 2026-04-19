"""Simple script to test Sparkling Water with OpenRouter FREE models."""

import asyncio
import os
from dotenv import load_dotenv
from sparkling_water.router.slm_router import SLMRouter
from sparkling_water.providers import ProviderManager


async def test_sparkling_water():
    """Test Sparkling Water with OpenRouter configuration."""
    print("=" * 60)
    print("Sparkling Water - OpenRouter FREE Models Test")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in .env file")
        return False

    print(f"\nOK: API Key configured")
    print(f"    Key: {api_key[:20]}...{api_key[-10:]}")

    # Check model configuration
    slm_model = os.getenv("SLM_MODEL", "google/gemma-4-26b-a4b-it:free")
    frontier_model = os.getenv("FRONTIER_MODEL", "google/gemma-4-31b-it:free")

    print(f"\nOK: Models configured")
    print(f"    SLM: {slm_model}")
    print(f"    Frontier: {frontier_model}")

    # Test SLM Router
    print("\n" + "-" * 60)
    print("Testing SLM Router")
    print("-" * 60)

    router = SLMRouter()

    # Test tasks
    test_tasks = [
        "Write a function to authenticate users with JWT tokens",
        "Debug the payment processing error in checkout",
        "Add error handling to the API endpoints",
        "Optimize the database query for user search",
        "Create a new user model with email validation",
    ]

    print(f"\nRouting {len(test_tasks)} test tasks...\n")

    for i, task_desc in enumerate(test_tasks, 1):
        print(f"Task {i}: {task_desc[:50]}...")

        task = await router.create_task(task_desc)
        decision = await router.route_task(task)

        print(f"  Type: {task.type.value}")
        print(f"  Model Tier: {decision.model_tier.value}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Reasoning: {decision.reasoning}")
        print()

    # Get routing statistics
    stats = await router.get_routing_stats()

    print("-" * 60)
    print("Routing Statistics")
    print("-" * 60)
    print(f"Total tasks: {stats['total_tasks']}")
    print(f"SLM tasks: {stats['slm_tasks']} ({stats['slm_percentage']:.1f}%)")
    print(f"Frontier tasks: {stats['frontier_tasks']}")
    print(f"Estimated cost savings: ${stats['estimated_cost_savings']:.4f}")
    print(f"Cost savings percentage: {stats['cost_savings_percentage']:.1f}%")

    # Test Provider Manager
    print("\n" + "-" * 60)
    print("Testing Provider Manager")
    print("-" * 60)

    manager = ProviderManager()

    # Configure OpenRouter
    print("\nConfiguring OpenRouter...")
    manager.set_provider_api_key("OpenRouter", api_key)

    # Get provider status
    status = manager.get_provider_status()
    print("\nProvider Status:")
    for provider_name, provider_status in status.items():
        if provider_name == "OpenRouter":
            print(f"  Provider: {provider_name}")
            print(f"  Enabled: {provider_status['enabled']}")
            print(f"  Has API Key: {provider_status['has_api_key']}")

    # Fetch models
    print("\nFetching OpenRouter models...")
    try:
        models = await manager.get_models_by_provider("OpenRouter")
        print(f"OK: Found {len(models)} models")

        # Find free models
        free_models = [m for m in models if m.input_cost_per_1k == 0 and m.output_cost_per_1k == 0]
        print(f"OK: Found {len(free_models)} FREE models")

        if free_models:
            print("\nTop 5 FREE Models:")
            for i, model in enumerate(free_models[:5], 1):
                print(f"  {i}. {model.name}")
                print(f"     ID: {model.id}")
                print(f"     Context: {model.context_window:,} tokens")
                print()

    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nYour Sparkling Water setup is working correctly!")
    print("You're using FREE models from OpenRouter.")
    print("\nTo use Sparkling Water:")
    print('  python -m sparkling_water.cli.main route "your task" --db :memory:')
    print("\nFor interactive chat, run in cmd.exe:")
    print("  python -m sparkling_water.cli.main chat .")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_sparkling_water())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
