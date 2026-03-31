"""Orchestrator: multi-agent loop that generates code, tests, validates, and improves."""

from aitest_guard.agents.code_agent import generate_code
from aitest_guard.agents.test_agent import generate_tests, improve_tests
from aitest_guard.agents.guard_agent import analyze_tests
from aitest_guard.llm.halo_provider import HaloProvider
from aitest_guard.llm.openai_provider import OpenAIProvider

MAX_ITERATIONS = 3


def _get_provider():
    """Pick LLM provider based on which API key is set.

    Priority: HALO_API_KEY → OPENAI_API_KEY → error.
    """
    import os

    if os.environ.get("HALO_API_KEY"):
        print("🔌 Using Halo AI provider")
        return HaloProvider()

    if os.environ.get("OPENAI_API_KEY"):
        print("🔌 Using OpenAI provider")
        return OpenAIProvider()

    raise RuntimeError(
        "No LLM provider configured. Set one of:\n"
        "  export HALO_API_KEY=your-halo-key\n"
        "  export OPENAI_API_KEY=your-openai-key"
    )


def run_workflow(prompt: str = "write a divide function that handles division by zero"):
    """Run the full code → test → validate → improve loop."""
    print("=" * 60)
    print("  aitest-guard  Multi-Agent Workflow")
    print("=" * 60)

    provider = _get_provider()

    # Step 1: Code Agent generates code
    print("\n--- Step 1: Code Agent ---")
    code = generate_code(prompt, provider)
    print(f"\n{code}\n")

    # Step 2: Test Agent generates tests
    print("\n--- Step 2: Test Agent ---")
    tests = generate_tests(code, provider)
    print(f"\n{tests}\n")

    # Step 3: Guard Agent validates, loop to improve
    for i in range(MAX_ITERATIONS):
        print(f"\n--- Step 3: Guard Agent (iteration {i + 1}/{MAX_ITERATIONS}) ---")
        feedback = analyze_tests(code, tests)

        if feedback["is_valid"]:
            print("\n🎉 Tests passed validation!")
            break

        if i < MAX_ITERATIONS - 1:
            print(f"\n--- Step 4: Improving tests (iteration {i + 1}) ---")
            tests = improve_tests(code, tests, feedback, provider)
            print(f"\n{tests}\n")
    else:
        print("\n⚠️  Max iterations reached. Tests may still have issues.")

    print("\n" + "=" * 60)
    print("  Final Generated Code")
    print("=" * 60)
    print(code)

    print("\n" + "=" * 60)
    print("  Final Tests")
    print("=" * 60)
    print(tests)

    print("\n✅ Workflow complete.")
    return {"code": code, "tests": tests, "feedback": feedback}


if __name__ == "__main__":
    run_workflow()
