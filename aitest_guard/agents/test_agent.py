"""Test Agent: generates and improves pytest tests via LLM."""

from aitest_guard.llm.base import LLMProvider


def generate_tests(code: str, provider: LLMProvider) -> str:
    """Generate pytest tests for the given Python code."""
    print("🧪 Generating tests...")

    prompt = (
        "You are a Python test engineer. Write pytest tests for the following "
        "Python code. Include tests for: happy path, invalid input, edge cases, "
        "and exception handling. Use pytest.raises where appropriate.\n"
        "Return ONLY the Python test code, no markdown fences, no explanation.\n\n"
        f"Code:\n{code}"
    )
    tests = provider.generate(prompt)
    tests = _strip_markdown_fences(tests)
    print("✅ Tests generated.")
    return tests


def improve_tests(
    code: str, tests: str, feedback: dict, provider: LLMProvider
) -> str:
    """Use LLM to fix tests based on guard feedback."""
    print("🔄 Fixing tests based on feedback...")

    issues = []
    for scenario in feedback.get("missing_scenarios", []):
        issues.append(f"- Missing test scenario: {scenario}")
    for weakness in feedback.get("weak_assertions", []):
        issues.append(f"- Weak assertion: {weakness}")

    issues_text = "\n".join(issues) if issues else "- General quality improvements needed"

    prompt = (
        "You are a Python test engineer. The following tests have quality issues. "
        "Fix them and return the COMPLETE improved test file.\n"
        "Return ONLY the Python test code, no markdown fences, no explanation.\n\n"
        f"Original code under test:\n{code}\n\n"
        f"Current tests:\n{tests}\n\n"
        f"Issues found:\n{issues_text}"
    )
    improved = provider.generate(prompt)
    improved = _strip_markdown_fences(improved)
    print("✅ Tests improved.")
    return improved


def _strip_markdown_fences(text: str) -> str:
    """Remove ```python ... ``` wrappers if present."""
    lines = text.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
