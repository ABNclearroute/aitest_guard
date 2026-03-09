"""CLI for aitest-guard."""

import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import typer

from aitest_guard.integration_analyzer import find_app_files
from aitest_guard.integration_checker import (
    check_integration_violations,
    expected_integration_test_name,
    find_integration_test_file,
)
from aitest_guard.policy import Policy, get_config_dir, load_policy, load_policy_dict, write_default_policy
from aitest_guard.scenario_checker import (
    check_violations,
    expected_test_name,
    find_test_file,
)
from aitest_guard.analyzer import find_python_files
from aitest_guard.quality_checker import check_quality_violations
from aitest_guard.weak_detector import detect_weak_tests

app = typer.Typer(
    name="aitest",
    help="AI Test Guard: policy-driven enforcement for AI-safe unit tests",
)


def _get_staged_python_files() -> list[Path]:
    """Return list of staged Python file paths in git repo, or empty if not a repo."""
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path.cwd(),
        )
    except (FileNotFoundError, OSError):
        return []
    if out.returncode != 0:
        return []
    root = Path.cwd()
    return [root / p for p in out.stdout.strip().splitlines() if p.endswith(".py")]


def _get_modified_python_files() -> list[Path]:
    """Return modified Python files (working tree + staged) in git repo."""
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path.cwd(),
        )
        out_cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path.cwd(),
        )
    except (FileNotFoundError, OSError):
        return []
    if out.returncode != 0 and out_cached.returncode != 0:
        return []
    root = Path.cwd()
    paths = set()
    for line in out.stdout.strip().splitlines():
        if line.endswith(".py"):
            paths.add(root / line)
    for line in out_cached.stdout.strip().splitlines():
        if line.endswith(".py"):
            paths.add(root / line)
    return list(paths)


def _get_pr_changed_files(base: str) -> list[Path]:
    """Return Python files changed in current branch vs base (e.g. main)."""
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM", f"{base}...HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path.cwd(),
        )
    except (FileNotFoundError, OSError):
        return []
    if out.returncode != 0:
        return []
    root = Path.cwd()
    return [root / p for p in out.stdout.strip().splitlines() if p.endswith(".py")]


def _is_source_file(p: Path, root: Path) -> bool:
    """Exclude test files, test dirs, and the tool's own package from source analysis."""
    try:
        rel = p.relative_to(root)
    except ValueError:
        return False
    parts = rel.parts
    if "tests" in parts or "test" in parts:
        return False
    if "aitest_guard" in parts:  # Don't analyze the tool itself
        return False
    if p.name.startswith("test_") and p.suffix == ".py":
        return False
    return True


def _get_source_files(policy: Policy, scope_override: str | None = None) -> list[Path]:
    """Get Python files to check. Uses enforcement.scope: staged | full_repo | modified | pr. Optional scope_override."""
    root = Path.cwd()
    scope = scope_override if scope_override is not None else policy.enforcement_scope
    if scope == "full_repo":
        return [p for p in find_python_files(root) if _is_source_file(p, root)]
    if scope == "modified":
        modified = _get_modified_python_files()
        return [p for p in modified if p.exists() and _is_source_file(p, root)]
    if scope == "pr":
        base = policy.enforcement_pr_base
        pr_files = _get_pr_changed_files(base)
        return [p for p in pr_files if p.exists() and _is_source_file(p, root)]
    # scope == staged: only git staged source files
    staged = _get_staged_python_files()
    return [p for p in staged if p.exists() and _is_source_file(p, root)]


def _get_unit_functions(policy: Policy, source: Path) -> list[str]:
    """Get function names from source for unit test checks."""
    from aitest_guard.analyzer import get_public_functions_with_risk

    result = get_public_functions_with_risk(
        source, ignore_private=policy.ignore_private_functions
    )
    return [name for name, _ in result]


def _require_policy() -> tuple[Path, Policy]:
    """Load policy or exit with error. Returns (config_dir, policy)."""
    config_dir = get_config_dir()
    policy = load_policy(config_dir)
    if policy is None:
        typer.echo("Error: No policy found. Run 'aitest init' first.", err=True)
        raise typer.Exit(1)
    return config_dir, policy


@app.command()
def init() -> None:
    """Create .aitest/ and default policy.yaml."""
    config_dir = get_config_dir()
    if (config_dir / "policy.yaml").exists():
        typer.echo(".aitest/policy.yaml already exists. Skipping.")
        return
    write_default_policy(config_dir)
    typer.echo(f"Created {config_dir}/policy.yaml")


def _collect_violations(policy: Policy, scope_override: str | None = None) -> tuple[list[tuple[Path, str, str, str]], list[Path]]:
    """Collect violations and return (violations, source_files). Violation: (source, target, scenario, kind)."""
    source_files = _get_source_files(policy, scope_override=scope_override)
    if not source_files:
        return [], []

    root = Path.cwd()
    app_files = find_app_files(source_files) if policy.integration_enabled else []
    unit_files = [f for f in source_files if f not in app_files]

    violations: list[tuple[Path, str, str, str]] = []  # (source, target, scenario, kind)

    for source, func, scenario in check_violations(policy, unit_files, root):
        violations.append((source, func, scenario, "unit"))

    for source in unit_files:
        for func in _get_unit_functions(policy, source):
            test_file = find_test_file(source, root)
            for test_name, msg in check_quality_violations(
                policy, source, func, test_file, root
            ):
                violations.append((source, test_name or func, msg, "quality"))

    seen_weak_files: set[Path] = set()
    for source in unit_files:
        test_file = find_test_file(source, root)
        if test_file.exists() and test_file not in seen_weak_files:
            seen_weak_files.add(test_file)
            for test_name, reason, tip in detect_weak_tests(test_file, policy):
                violations.append((source, test_name, f"{reason}\nTip: {tip}", "weak"))
    if policy.integration_enabled and app_files:
        for source in app_files:
            test_file = find_integration_test_file(source, root)
            if test_file.exists() and test_file not in seen_weak_files:
                seen_weak_files.add(test_file)
                for test_name, reason, tip in detect_weak_tests(test_file, policy):
                    violations.append((source, test_name, f"{reason}\nTip: {tip}", "weak"))

    if policy.integration_enabled and app_files:
        for source, handler, scenario in check_integration_violations(
            app_files,
            root,
            policy.integration_scenarios,
            policy.integration_enforce_naming,
            policy.integration_require_docstring,
        ):
            violations.append((source, handler, scenario, "integration"))

    return violations, source_files


def _run_check(
    policy: Policy,
    output_format: str = "text",
    scope_override: str | None = None,
) -> bool:
    """Run unit + integration checks + governance. Returns True if all pass (or strict=False)."""
    root = Path.cwd()
    violations, source_files = _collect_violations(policy, scope_override=scope_override)

    # Collect test files for governance
    test_files: list[Path] = []
    for src in source_files:
        tf = find_test_file(src, root)
        if tf.exists():
            test_files.append(tf)
    if policy.integration_enabled:
        app_files = find_app_files(source_files)
        for src in app_files:
            tf = find_integration_test_file(src, root)
            if tf.exists():
                test_files.append(tf)
    test_files = list(dict.fromkeys(test_files))

    # Fallback: if no test files found from source mapping, discover tests/ directory
    if not test_files and (root / "tests").exists():
        test_files = sorted((root / "tests").rglob("test_*.py"))

    # Run governance on test files
    config_dir = get_config_dir()
    policy_dict = load_policy_dict(config_dir)
    governance_results: list[dict] = []
    any_governance_fail = False
    if policy_dict and test_files:
        from aitest_guard.governance import validate_file_governance

        llm_provider = None
        llm_gov = policy_dict.get("llm_governance", {})
        if llm_gov.get("enabled", False):
            try:
                policy_obj = load_policy(config_dir)
                if policy_obj:
                    from aitest_guard.generator import get_llm_provider
                    llm_provider = get_llm_provider(policy_obj)
            except Exception:
                pass

        enforcement = policy_dict.get("enforcement", {})
        mode = enforcement.get("mode", "strict")
        for tf in test_files:
            result = validate_file_governance(
                tf, policy_dict, policy_name="policy", enforcement_mode=mode,
                llm_provider=llm_provider,
            )
            try:
                result["file"] = str(tf.relative_to(root))
            except ValueError:
                result["file"] = str(tf)
            governance_results.append(result)
            if result["status"] in ("FAIL", "FAIL_MERGE"):
                any_governance_fail = True

    if not source_files and not test_files:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": True,
            "summary": {"total_violations": 0, "unit": 0, "integration": 0, "weak": 0, "quality": 0},
            "policy_checks": {"violations": []},
            "ai_governance": [],
        }
        if output_format == "json":
            typer.echo(json.dumps(report, indent=2))
        else:
            typer.echo("No Python files to check.")
        return True, report

    strict = policy.enforcement_mode == "strict"
    has_scenario_violations = bool(violations)
    scenario_pass = not (strict and has_scenario_violations)
    governance_pass = not any_governance_fail
    all_pass = scenario_pass and governance_pass

    if not violations and not any_governance_fail:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": True,
            "summary": {"total_violations": 0, "unit": 0, "integration": 0, "weak": 0, "quality": 0},
            "policy_checks": {"violations": []},
            "ai_governance": [{"file": r["file"], "status": r["status"], "risk_score": r["risk_score"], "risk_level": r["risk_level"], "violations": [], "recommendations": r.get("recommendations", [])} for r in governance_results],
        }
        if output_format == "json":
            typer.echo(json.dumps(report, indent=2))
        else:
            typer.echo("All required scenarios present (unit + integration).")
            if governance_results:
                typer.echo(f"Governance: {len(governance_results)} test file(s) PASS.")
        return True, report
    groups: dict[tuple[Path, str, str], list[str]] = defaultdict(list)
    for source, target, scenario, kind in violations:
        groups[(source, target, kind)].append(scenario)

    summary_counts: dict[str, int] = defaultdict(int)
    for _, _, _, kind in violations:
        summary_counts[kind] += 1

    report = _build_report_dict(root, violations, groups, summary_counts, governance_results, all_pass)

    if output_format == "json":
        typer.echo(json.dumps(report, indent=2))
        return all_pass, report

    # Text output: readable report
    total = len(violations)
    text = _format_readable_report(root, groups, governance_results, all_pass, total)
    typer.echo(text)
    return all_pass, report


def _build_report_dict(
    root: Path,
    violations: list[tuple[Path, str, str, str]],
    groups: dict[tuple[Path, str, str], list[str]],
    summary_counts: dict[str, int],
    governance_results: list[dict],
    all_pass: bool,
) -> dict:
    """Build structured report for JSON output."""
    json_violations = []
    for (source, target, kind), scenarios in sorted(groups.items()):
        try:
            rel = str(source.relative_to(root))
        except ValueError:
            rel = str(source)
        json_violations.append({
            "file": rel,
            "target": target,
            "kind": kind,
            "scenarios": sorted(scenarios),
        })
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": all_pass,
        "summary": {
            "total_violations": len(violations),
            "unit": summary_counts.get("unit", 0),
            "integration": summary_counts.get("integration", 0),
            "weak": summary_counts.get("weak", 0),
            "quality": summary_counts.get("quality", 0),
        },
        "policy_checks": {"violations": json_violations},
        "ai_governance": [
            {
                "file": r["file"],
                "status": r["status"],
                "risk_score": r["risk_score"],
                "risk_level": r["risk_level"],
                "violations": [{"code": v.code.value, "message": v.message} for v in r["violations"]],
                "recommendations": r.get("recommendations", []),
            }
            for r in governance_results
        ],
    }


def _format_readable_report(
    root: Path,
    groups: dict[tuple[Path, str, str], list[str]],
    governance_results: list[dict],
    all_pass: bool,
    total: int,
) -> str:
    """Format report as readable text."""
    lines: list[str] = []
    lines.append("")
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║  AITEST GUARD – Policy & AI Governance Report               ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")
    status = "PASS" if all_pass else "FAIL"
    lines.append(f"  Overall: {status}")
    lines.append(f"  Violations: {total}")
    lines.append("")
    lines.append("  ─── Policy checks (scenarios, quality, weak tests) ───")
    lines.append("")

    for (source, target, kind), scenarios in sorted(groups.items()):
        try:
            rel = str(source.relative_to(root))
        except ValueError:
            rel = str(source)
        kind_label = f" [{kind}]" if kind != "unit" else ""
        lines.append(f"  📁 {rel}{kind_label}")
        if kind != "weak":
            lines.append(f"     {target}()")
        for scenario in sorted(scenarios):
            if kind == "weak":
                lines.append(f"     ⚠ Weak test: {target}")
                for line in scenario.split("\n"):
                    lines.append(f"       {line}")
            elif kind == "quality":
                lines.append(f"     → {scenario}")
            elif kind == "integration":
                expected = expected_integration_test_name(target, scenario)
                lines.append(f"     → missing {expected}")
            else:
                expected = expected_test_name(target, scenario)
                lines.append(f"     → missing {expected}")
        lines.append("")

    lines.append("  ─── AI governance (risk scoring, validators) ───")
    lines.append("")
    if governance_results:
        for r in governance_results:
            icon = "✓" if r["status"] == "PASS" else ("!" if r["status"] == "WARN" else "✗")
            lines.append(f"  {icon} {r['file']}")
            lines.append(f"     Status: {r['status']}  │  Risk: {r['risk_score']} ({r['risk_level']})")
            for v in r["violations"]:
                code = v.code.value if hasattr(v.code, "value") else str(v.code)
                lines.append(f"     • [{code}] {v.message}")
            for rec in r.get("recommendations", []):
                lines.append(f"     → {rec}")
            lines.append("")
    else:
        lines.append("  No test files found to run governance.")
        lines.append("  Add tests (e.g. tests/test_<module>.py) to see results.")
        lines.append("")
    return "\n".join(lines)


@app.command()
def check(
    output_format: str = typer.Option("text", "--format", "-f", help="Output format: text (default) or json"),
    output_file: Path | None = typer.Option(None, "--output", "-o", help="Write JSON report to file"),
) -> None:
    """Run all policy checks and verification: scenarios, quality, weak tests, governance. Exit 1 if violations."""
    _, policy = _require_policy()
    all_pass, report = _run_check(policy, output_format=output_format)

    if output_file is not None:
        output_file = Path(output_file)
        output_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        typer.secho(f"Report written to {output_file}", fg="green")

    if not all_pass:
        raise typer.Exit(1)


@app.command()
def suggest() -> None:
    """Suggest which modified files need attention (missing scenarios, weak tests)."""
    _, policy = _require_policy()
    root = Path.cwd()
    violations, source_files = _collect_violations(policy, scope_override="modified")

    if not source_files:
        typer.echo("No modified Python files to suggest.")
        return

    # Group violations by source file
    by_file: dict[Path, dict[str, list]] = defaultdict(lambda: {"missing": [], "weak": []})
    for source, target, scenario, kind in violations:
        if kind == "weak":
            by_file[source]["weak"].append(target)
        else:
            by_file[source]["missing"].append((target, scenario))

    total = len(source_files)
    need_action = len(by_file)
    typer.echo(f"Suggestions ({total} file(s) modified, {need_action} need action):")
    typer.echo("")

    for source in sorted(source_files):
        try:
            rel = str(source.relative_to(root))
        except ValueError:
            rel = str(source)
        info = by_file[source]
        missing_count = len(info["missing"])
        weak_count = len(set(info["weak"]))
        if missing_count > 0 and weak_count > 0:
            typer.secho(f"  {rel}  — {missing_count} missing scenario(s), {weak_count} weak test(s)", err=False)
        elif missing_count > 0:
            typer.secho(f"  {rel}  — {missing_count} missing scenario(s)", err=False)
        elif weak_count > 0:
            typer.secho(f"  {rel}  — {weak_count} weak test(s)", err=False)
        else:
            typer.secho(f"  {rel}  — OK", err=False)


@app.command()
def watch() -> None:
    """Watch for .py changes and run check (scope: modified). Ctrl+C to exit."""
    import time

    _, policy = _require_policy()
    root = Path.cwd()

    def _run_check_on_modified() -> bool:
        return _run_check(policy, output_format="text", scope_override="modified")

    typer.echo("Watching for .py file changes (scope: modified). Ctrl+C to exit.")
    typer.echo("")

    try:
        from watchfiles import watch
        # Use watchfiles; FileChange = (Change, path_str)
        last_run = 0.0
        for changes in watch(root, ignore_permission_denied=True):
            if not changes:
                continue
            # Filter to .py files
            py_changes = [p for _, p in changes if p.endswith(".py")]
            if not py_changes:
                continue
            now = time.monotonic()
            if now - last_run < 1.0:
                continue
            last_run = now
            typer.echo(f"[{time.strftime('%H:%M:%S')}] Change detected, running check...")
            _run_check_on_modified()
            typer.echo("")
    except ImportError:
        typer.echo("Install optional 'watch' extra: pip install aitest-guard[watch]")
        typer.echo("Falling back to polling (every 2s).")
        last_mtimes: dict[Path, float] = {}
        while True:
            try:
                time.sleep(2)
                changed = False
                for p in root.rglob("*.py"):
                    if ".git" in p.parts or "__pycache__" in p.parts:
                        continue
                    try:
                        m = p.stat().st_mtime
                        if last_mtimes.get(p) != m:
                            last_mtimes[p] = m
                            changed = True
                    except OSError:
                        pass
                if changed and last_mtimes:
                    typer.echo(f"[{time.strftime('%H:%M:%S')}] Change detected, running check...")
                    _run_check_on_modified()
                    typer.echo("")
            except KeyboardInterrupt:
                break


def main() -> None:
    app()


if __name__ == "__main__":
    main()
