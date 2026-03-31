"""Code Agent: generates Python function code via LLM."""

from aitest_guard.llm.base import LLMProvider


def generate_code(prompt: str, provider: LLMProvider) -> str:
    """Use LLM to generate a Python function from a natural-language prompt."""
    print(f"🔧 Generating code for: {prompt}")

    llm_prompt = (
        "You are a Python developer. Write a single Python function based on "
        "the following requirement. Return ONLY the Python code, no markdown "
        "fences, no explanation.\n\n"
        f"Requirement: {prompt}"
    )
    code = provider.generate(llm_prompt)
    code = _strip_markdown_fences(code)
    print("✅ Code generated.")
    return code


def _strip_markdown_fences(text: str) -> str:
    """Remove ```python ... ``` wrappers if present."""
    lines = text.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
