"""AST-based analyzer for Flask/FastAPI endpoints."""

import ast
from pathlib import Path
from typing import Iterator

Endpoint = tuple[str, str, str]  # (method, path_slug, handler_name)


def _path_to_slug(path: str) -> str:
    """Convert route path to test slug. /validate-email -> validate_email."""
    path = path.strip("/") or "root"
    return path.replace("-", "_").replace("/", "_").replace("<", "").replace(">", "")


def _get_route_info(decorator: ast.expr) -> tuple[str, str] | None:
    """Extract (path, method) from @app.route(path, methods=[...]) or @router.get(path)."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        # router.get("/path") or app.get("/path")
        if isinstance(func, ast.Attribute):
            attr = func.attr.lower()
            if attr in ("get", "post", "put", "patch", "delete", "head", "options"):
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    path = str(decorator.args[0].value)
                    return (path, attr.upper())
        # app.route("/path", methods=["GET"])
        if isinstance(func, ast.Attribute) and func.attr == "route":
            path_val = ""
            method = "GET"
            for i, arg in enumerate(decorator.args):
                if isinstance(arg, ast.Constant):
                    path_val = str(arg.value)
                    break
            for kw in decorator.keywords:
                if kw.arg == "methods" and isinstance(kw.value, ast.List):
                    if kw.value.elts and isinstance(kw.value.elts[0], ast.Constant):
                        method = str(kw.value.elts[0].value).upper()
                    break
            if path_val:
                return (path_val, method)
    return None


def get_endpoints(file_path: Path) -> list[Endpoint]:
    """Extract (method, path_slug, handler_name) for each route in a Flask/FastAPI file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    endpoints: list[Endpoint] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                info = _get_route_info(dec)
                if info:
                    path, method = info
                    slug = _path_to_slug(path)
                    handler = node.name
                    endpoints.append((method, slug, handler))
                    break
    return endpoints


def find_app_files(source_files: list[Path]) -> list[Path]:
    """Filter to files that define HTTP routes."""
    return [p for p in source_files if get_endpoints(p)]
