# ARC backend

Follow the root [installation guide](../README.md#install-and-run) for PostgreSQL,
credentials, cross-platform commands, and the judge walkthrough.

From this directory, with PostgreSQL running, on Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Set `DATABASE_URL` before migration if not using the Docker defaults. On macOS/Linux,
create the venv with `python3.11 -m venv .venv`, copy the environment without
replacing an existing file, and use `.venv/bin/python` for subsequent commands.
No activation or seed is required. Run commands from this directory.

- Health: <http://localhost:8000/api/v1/health>
- API docs: <http://localhost:8000/docs>
- Tests: `.\.venv\Scripts\python.exe -m pytest`
- Lint: `.\.venv\Scripts\python.exe -m ruff check .`

See the complete [environment reference](../README.md#environment-reference).
Keep provider secrets here, never in the frontend. Restart after environment edits.
Keep the API running through workflow execution and payment confirmation.
