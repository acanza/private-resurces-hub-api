# Copilot Instructions — private-resurces-hub-api

## Change discipline

- Make the smallest change that satisfies the request. One concern per change.
- Prefer editing existing files over creating new ones.
- Never delete or overwrite files that may contain work in progress without asking first.
- Do not refactor, rename, or reformat code that is outside the scope of the current task.
- Do not add comments, docstrings, or type annotations to code you did not change.

---

## Security

- Never hardcode secrets, API keys, passwords, or tokens — not even as placeholders.
- Credentials and environment-specific values belong exclusively in `.env` (git-ignored).
- Never commit `.env` files. The repository must contain a `.env.example` with dummy values.
- Do not log sensitive values (`AWS_SECRET_ACCESS_KEY`, tokens, passwords, `ExpressionAttributeValues`).
- Do not expose internal error messages or stack traces in HTTP responses.
- Validate all external input at system boundaries (HTTP request bodies, query params, path params).

---

## Repository structure

```
.github/
├── copilot-instructions.md   # This file — always-on global rules
├── agents/                   # Custom agent modes
└── skills/                   # On-demand domain knowledge
src/                          # Application source code
tests/                        # Test suite (mirrors src/ structure)
.env.example                  # Env var reference with dummy values
pyproject.toml                # Dependencies, tool config (pytest, ruff)
```

New source modules go under `src/`. New tests go under `tests/` mirroring the same path.

---

## Naming conventions

| Element | Convention | Example |
|---|---|---|
| Files and folders | `snake_case` | `dynamodb_service.py` |
| Classes | `PascalCase` | `ItemResponse` |
| Functions and variables | `snake_case` | `get_item`, `item_id` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_REGION` |
| Environment variables | `UPPER_SNAKE_CASE` | `AWS_REGION` |
| Test files | `test_<module>.py` | `test_router.py` |

---

## Code style

- Linter and formatter: **ruff**. Run `ruff check --fix src` and `ruff format src` before committing.
- No `print()` statements — use the Starlette logger (`request.log`, `fastapi.log`).
- No implicit `Any` in type annotations.
- Python version: **3.12+**. Use `X | Y` unions and `StrEnum` where appropriate.

---

## Skills available for this project

| Task | Skill |
|---|---|
| Scaffold a new router, add endpoints, create schemas | `fastapi-route-scaffolding` |
| S3 client dependency, list/get objects, S3 error handling | `aws-s3-access` |
| DynamoDB dependency, get/put/update items, error handling | `aws-dynamodb-access` |
| Write tests for S3 or DynamoDB routes, set up moto fixtures | `fastapi-aws-testing` |
