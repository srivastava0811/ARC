# ARC frontend

Next.js workspace for procurement, workflow progress, recommendations, Sandbox
checkout, receipts, and history. Follow the root [setup guide](../README.md#install-and-run)
to start PostgreSQL and FastAPI first.

From this directory, on Windows PowerShell:

```powershell
npm.cmd ci
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

On macOS/Linux use `npm` and `test -f .env.local || cp .env.example .env.local`.
Open <http://localhost:3000>. The frontend environment contains only:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Never place provider keys or PayPal credentials in frontend files. Restart Next.js
after environment edits.

Verify with `npm run lint`, `npm run typecheck`, and `npm run build`. Production
startup is `npm run start -- --hostname 127.0.0.1 --port 3000` after building.
Stop development before building in the same folder; both use `.next-arc`.
Use `npm.cmd` on Windows if PowerShell blocks `npm.ps1`.
