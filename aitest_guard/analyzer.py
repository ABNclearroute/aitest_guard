"""AST-based Python analyzer for extracting public functions."""

import ast
from pathlib import Path
from typing import Generator


def get_public_functions(file_path: Path, ignore_private: bool = True) -> list[str]:
    """Extract public function names from a Python file via AST."""
    result = get_public_functions_with_risk(file_path, ignore_private)
    return [name for name, _ in result]


def get_risk_level(node: ast.FunctionDef) -> str:
    """Detect risk level from docstring. Look for 'aitest: critical' or 'critical'."""
    doc = ast.get_docstring(node)
    if not doc:
        return "standard"
    doc_lower = doc.lower()
    if "aitest: critical" in doc_lower or ":critical" in doc_lower:
        return "critical"
    return "standard"


def get_public_functions_with_risk(
    file_path: Path, ignore_private: bool = True
) -> list[tuple[str, str]]:
    """Extract (function_name, risk_level) from a Python file. risk_level: critical | standard."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    result: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if ignore_private and node.name.startswith("_"):
                continue
            risk = get_risk_level(node)
            result.append((node.name, risk))
    return result


def find_python_files(
    root: Path,
    include_dirs: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> Generator[Path, None, None]:
    """Yield Python files under root, optionally filtered by dir patterns."""
    include = set(include_dirs or ["*"])
    exclude = set(exclude_dirs or ["__pycache__", ".git", ".venv", "venv", "node_modules"])

    for path in root.rglob("*.py"):
        if any(part in exclude for part in path.parts):
            continue
        yield path
