# aitest-guard

Policy-driven enforcement engine for AI-safe unit tests. Works with any coding AI (Copilot, Cursor, ChatGPT, etc.). No dashboard, server, or external state. Built for **shift-left** AI testing: feedback before staging, in CI, and in the dev loop.

**Enterprise v2:** Context-aware risk amplification, security governance, requirement ambiguity detection, contract versioning, and granular CI enforcement (block merge/release).

## Install

```bash
pip install -e .
# For LLM generation: pip install aitest-guard[openai]
# For file watching: pip install aitest-guard[watch]
```

## Quick Start

```bash
aitest init          # Create .aitest/ and policy.yaml
aitest check         # Enforce required scenarios (exit 1 if violations)
aitest generate      # Generate missing tests via LLM (if enabled)
aitest suggest       # Quick summary of what to fix (scope: modified)
aitest watch         # Run check on .py changes (requires [watch])
aitest fix           # Improve weak tests via LLM (if enabled)
aitest governance    # Run AI output governance on test files (enterprise)
```

## Shift-Left Features

| Feature | Description |
|---------|-------------|
| **scope: modified** | Check before `git add` — analyze all modified (working + staged) Python files |
| **scope: pr** | CI-focused — only check files changed in the PR vs base branch |
| **aitest suggest** | "What should I fix first?" — compact list of files needing `generate` or `fix` |
| **aitest check -f json** | CI/PR integration — machine-readable output for pipelines |
| **aitest watch** | Continuous feedback — run check when `.py` files change |

## Policy

`.aitest/policy.yaml` configures governance. Run `aitest init` to create the default:

```yaml
# Unit tests: happy_path, invalid_input, exception_case (risk-based optional)
# Integration tests: success_response, client_error, server_error, timeout
# Quality: min_assertions_per_test, require_pytest_raises_for_exceptions
# Risk classification: Tag functions with "aitest: critical" in docstring for stricter rules
```

Key sections: `unit_tests`, `risk_classification`, `integration_tests`, `weak_test_detection`, `assertion_policy`, `coverage`, `enforcement`, `llm`, `ai_output_governance`, `risk_scoring`, `risk_context`, `security_governance`, `requirement_governance`, `audit`, `output_contract`.

**Enforcement scopes** (`enforcement.scope`):

| Scope | When to use |
|-------|-------------|
| `staged` | Pre-commit — only staged files (default) |
| `modified` | During dev — all modified files (working + staged) |
| `full_repo` | Full scan — entire project |
| `pr` | CI/PR — files changed vs `enforcement.pr_base` (default: `main`) |

**Enforcement options** (`enforcement`):

| Option | Description |
|--------|-------------|
| `block_commit` | Block commit when violations exist (default: true) |
| `block_merge` | Block merge when risk_level is HIGH |
| `block_release` | Block release when HIGH risk |
| `require_manual_override_for_high` | Include override token in response for HIGH risk |

**Also:** Weak test detection, AI prompt standardization, AI output validation, optional `aitest fix` for weak tests.

## LLM / OpenAI API Key

To use `aitest generate`, set your OpenAI API key via **environment variable**:

```bash
export OPENAI_API_KEY=sk-your-key-here
aitest generate
```

Or inline for a single run:

```bash
OPENAI_API_KEY=sk-your-key-here aitest generate
```

Then enable LLM in `.aitest/policy.yaml`:

```yaml
llm:
  enabled: true
  provider: openai
  model: gpt-4o-mini
```

**Note:** Do not commit API keys. Use environment variables or a secrets manager, not `policy.yaml`.

## Example API

An example Flask API is in `example_api/` for testing the tool:

```bash
# Install deps
pip install flask

# Initialize aitest-guard (creates .aitest/policy.yaml)
aitest init

# Run check - will report missing scenarios for calculator & validator
aitest check

# Run the API
python run_example.py
```

The `calculator` and `validator` modules have public functions; `tests/` has incomplete coverage so `aitest check` will fail until you add the required scenario tests.

## CI Integration

Use `--format=json` for machine-readable output:

```bash
aitest check --format=json
# or
aitest check -f json
```

Output:

```json
{
  "passed": false,
  "violations": [
    {"file": "example_api/calculator.py", "target": "calculate_total", "kind": "unit", "scenarios": ["exception_case"]}
  ],
  "summary": {"total": 1, "unit": 1, "integration": 0, "weak": 0, "quality": 0}
}
```

For PR-focused runs, set `enforcement.scope: pr` and optionally `enforcement.pr_base: main` (or `origin/main`).

## aitest suggest

Quick "what should I fix first?" for modified files:

```bash
aitest suggest
```

Example output:

```
Suggestions (3 files modified, 2 need action):
  example_api/calculator.py  — 3 missing scenario(s) (run: aitest generate)
  example_api/validator.py   — 1 weak test(s) (run: aitest fix)
  example_api/app.py         — OK
```

## aitest watch

Run `aitest check` automatically when `.py` files change. Uses scope `modified`.

```bash
pip install aitest-guard[watch]
aitest watch
```

Exit with Ctrl+C. Falls back to polling if `watchfiles` is not installed.

## AI Output Governance (Enterprise)

Run `aitest governance` to validate test files against enterprise policies:

```bash
aitest governance                    # Validate test files from current scope
aitest governance tests/             # Validate a directory
aitest governance tests/test_foo.py  # Validate a single file
aitest governance -f json            # JSON output
```

### Governance Validators

| Validator | Policy section | Violation |
|-----------|----------------|-----------|
| Traceability | `ai_output_governance.traceability_policy` | MISSING_TRACEABILITY |
| Edge case ratio | `ai_output_governance.edge_case_policy` | LOW_EDGE_COVERAGE |
| Vague phrases | `ai_output_governance.vague_phrase_policy` | VAGUE_ASSERTION |
| Format | `ai_output_governance.deterministic_format_policy` | FORMAT_VIOLATION |
| Security | `security_governance` | MISSING_SECURITY_TESTS |
| Requirement | `requirement_governance` | AMBIGUOUS_REQUIREMENT, MISSING_ERROR_SPECIFICATION |
| Contract version | `output_contract` | CONTRACT_VERSION_MISMATCH |

### Context-Aware Risk Amplification

Risk scores can be amplified for sensitive modules and critical classifications:

```yaml
risk_context:
  module_multipliers:
    billing: 2.0
    auth: 2.0
    payment: 2.5
  classification_multipliers:
    critical: 2.0
    standard: 1.0
```

Multipliers compound (module × classification) per violation.

### Compliance Response Contract

Governance returns:

```json
{
  "status": "PASS" | "WARN" | "FAIL" | "FAIL_MERGE",
  "enforcement_action": "BLOCK_COMMIT" | "BLOCK_MERGE" | "WARN" | "ALLOW",
  "base_risk_score": 0,
  "final_risk_score": 0,
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "multiplier_details": {},
  "violations": [],
  "recommendations": [],
  "override_token": null
}
```

`override_token` is set when `require_manual_override_for_high` is true and risk is HIGH.

### Audit Configuration

```yaml
audit:
  enabled: true
  retention_days: 90
  include_artifact_snapshot: false
  include_risk_score: true
```

Audit logs go to `logs/audit/audit.jsonl`. Entries older than `retention_days` are pruned automatically.

### Output Contract Versioning

Add `# aitest_contract_version: 1.0` to test files and set `output_contract.enforce_version_match: true` to validate version alignment.

## Pre-Commit

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: aitest-check
      name: AI Test Guard
      entry: aitest check
      language: system
      types: [python]
```

## License

MIT
