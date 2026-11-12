# Local setup and configuration reference

For a project overview and quick start, see the [README](../README.md).
This guide preserves the detailed setup, provider diagnostics, environment reference,
and troubleshooting steps.

## Install and run

### 1. Obtain the source

Clone the public repository:

```text
git clone https://github.com/srivastava0811/ARC.git
cd ARC
```

Alternatively, extract the repository ZIP. Open a terminal in the folder containing this README. All commands start there unless a `cd` specifies otherwise.

### 2. Start PostgreSQL

```text
docker compose up -d --wait postgres
docker compose ps
docker compose exec -T postgres pg_isready -U arc -d arc
```

Expect a healthy database and `accepting connections`. Compose creates database `arc`, user `arc`, password `arc`, and a persistent named volume. These credentials are for local development only.

For native PostgreSQL, create a login and an empty database owned by it, then update `DATABASE_URL`. For example, as a PostgreSQL administrator in pgAdmin's Query Tool:

```sql
CREATE ROLE arc WITH LOGIN PASSWORD 'choose-a-local-password';
CREATE DATABASE arc OWNER arc;
```

Run these only if the role/database do not exist. URL-encode special characters in connection-string passwords. Do not overwrite an existing database.

### 3. Install the backend and apply migrations

**Windows PowerShell:**

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

**macOS / Linux:**

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
test -f .env || cp .env.example .env
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
```

The example environment matches Docker. If using another database, edit `DATABASE_URL` **before** migrating. Expected head: `0003_paypal_sandbox_payments (head)`.

**No seed command is required.** ARC creates its workspace on the first request; the synthetic catalog is application-provided. Starting the API does not apply migrations automatically.

### 4. Start the API — terminal A

From `backend/`, leave this command running:

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# macOS / Linux
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [API health](http://localhost:8000/api/v1/health). Expect HTTP 200, `status: "ok"`, and `services.database: "connected"`. [Interactive API documentation](http://localhost:8000/docs) is also available. Health checks connectivity; `alembic current` checks schema version.

### 5. Start the frontend — terminal B

Open a new terminal at the repository root.

**Windows PowerShell:**

```powershell
cd frontend
npm.cmd ci
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

**macOS / Linux:**

```bash
cd frontend
npm ci
test -f .env.local || cp .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open **[http://localhost:3000](http://localhost:3000)**. Use `localhost` consistently in the browser: the default CORS origin and PayPal return URL use it.

The frontend environment should contain only this public configuration:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Explicit Python paths avoid activation and PowerShell execution-policy changes. `npm.cmd` avoids Windows `npm.ps1` restrictions. Run npm commands inside `frontend/`, not the repository root.

### 6. Select a demo configuration

Edit `backend/.env` and restart the API:

| Configuration | `AGENT_MODE` | `CATALOG_PROVIDER` | Credentials |
| --- | --- | --- | --- |
| Reproducible procurement demo | `fixture` | `demo_catalog` | None for recommendations |
| Gemini with stable synthetic products | `gemini` | `demo_catalog` | Gemini key |
| Full external integration | `gemini` | `channel3` | Gemini and Channel3 keys |
| Checkout in any configuration | Either | Either | PayPal Sandbox app credentials and Sandbox buyer |

The first configuration is the default. Gemini with the demo catalog offers predictable products plus AI enrichment. Channel3 demonstrates live research; availability, product evidence, prices, provider access, and quotas can affect results.

## External integrations

Put secrets only in `backend/.env`. Restart the backend after changes; restart Next.js after frontend environment changes. Do not commit keys or place them in `NEXT_PUBLIC_*` variables.

### PayPal Sandbox — required for checkout

1. Sign in to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/).
2. In **Apps & Credentials**, select **Sandbox** and create/select a REST app associated with a Sandbox **Business** seller. Copy its client ID and secret.
3. In **Sandbox Accounts**, create/select a **Personal** buyer and obtain its Sandbox email/password. Use a buyer distinct from the seller, with enough test balance.
4. Configure the backend:

   ```dotenv
   PAYPAL_MODE=sandbox
   PAYPAL_CLIENT_ID=your-sandbox-app-client-id
   PAYPAL_CLIENT_SECRET=your-sandbox-app-secret
   PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
   FRONTEND_ORIGIN=http://localhost:3000
   ```

5. Restart the API. At checkout, sign in with the **Sandbox Personal buyer**, approve, and return to ARC. Keep both application servers running.

Buyer credentials belong on PayPal's Sandbox page, not in ARC's environment. ARC authenticates server-side, creates an order with the selected option's server-calculated amount, and captures after approval. A completed capture is required for a receipt. Test funds are used; no live account or real card is needed.

Official guides: [REST app setup](https://developer.paypal.com/api/get-started/) and [Sandbox accounts](https://developer.paypal.com/sandbox-testing/accounts/).

### Gemini — optional AI enrichment

Create a key in [Google AI Studio](https://aistudio.google.com/apikey), following the [API-key guide](https://aistudio.google.com/docs/api-key). Ensure the project has access and quota for the configured models.

```dotenv
AGENT_MODE=gemini
GEMINI_API_KEY=your-gemini-api-key
```

Keep the example model IDs if available to your project; otherwise choose accessible models supporting structured output. The planner-model setting is used by the diagnostic helper; normal workflow planning is deterministic.

From `backend/`, test the default planner and evaluator models:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_gemini
.\.venv\Scripts\python.exe -m scripts.verify_gemini gemini-3.5-flash
```

Use `.venv/bin/python` on macOS/Linux. If you changed model IDs, test those instead. These commands make real provider requests and consume quota.

### Channel3 — optional live catalog

Obtain API access through [Channel3 for developers](https://trychannel3.com/developers), then configure:

```dotenv
CATALOG_PROVIDER=channel3
CHANNEL3_API_KEY=your-channel3-api-key
CHANNEL3_BASE_URL=https://api.trychannel3.com
```

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_channel3
```

Use `.venv/bin/python` on macOS/Linux. This makes a real search. API success does not guarantee eligible products; ARC filters unsuitable or unverified offers rather than inventing prices.

## Judge walkthrough

For a predictable first run, use `fixture` + `demo_catalog`, with PayPal Sandbox configured for checkout.

1. Open [ARC](http://localhost:3000) and confirm healthy API/database status.
2. Submit **`Find three 27-inch monitors for our office under $600 total.`**
3. Watch Planner, Researcher, Evaluator, and Reporter. All four checks finish before product cards appear.
4. Inspect evidence and tradeoffs. The synthetic StudioView 27-inch option is **$189/unit, $567 for three**. Other 27-inch options exceed the budget; a 24-inch product fails the size constraint. Synthetic data is labeled.
5. Select the eligible option and choose **Review & approve**. Review quantity and total, then continue to PayPal Sandbox.
6. Sign in as the Sandbox Personal buyer and approve. On return, ARC displays payment processing while the API captures the order.
7. Wait for the completed payment/receipt. Check product, quantity, and total. Visit [History](http://localhost:3000/history) to inspect saved requests. A redirect alone is not payment confirmation.
8. Try **`I need 4 wireless keyboards under $200.`** and **`I need 5 mice under $100.`** to demonstrate additional categories. Checkout is optional for these examples.
9. Test clarification with **`Find three monitors under $600 total.`**; answer **`27-inch monitors`** when asked for size.
10. Enable Gemini and/or Channel3, restart the API, and submit a new request to demonstrate live integrations. Results may differ.

Without PayPal credentials, recommendations and clarification still work, but checkout cannot complete. Without Gemini, the workflow does not demonstrate live AI enrichment.

## Environment reference

Run backend commands from `backend/` so `.env` and migration paths resolve. Process environment variables override `.env`. Example files contain safe defaults, not external credentials.

| Backend variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Environment label |
| `DATABASE_URL` | `postgresql+asyncpg://arc:arc@localhost:5432/arc` | Database connection; preserve `+asyncpg` |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Exact CORS/checkout return origin; no trailing slash |
| `LOG_LEVEL` | `INFO` | Logging level |
| `AGENT_MODE` | `fixture` | `fixture` or `gemini` |
| `GEMINI_API_KEY` | Empty | Gemini secret key |
| `GEMINI_PLANNER_MODEL` | `gemini-3.5-flash-lite` | Planner diagnostic model |
| `GEMINI_EVALUATOR_MODEL` | `gemini-3.5-flash` | Evaluation enrichment model |
| `GEMINI_REPORTER_MODEL` | `gemini-3.5-flash-lite` | Report enrichment model |
| `CATALOG_PROVIDER` | `demo_catalog` | `demo_catalog` or `channel3` |
| `CHANNEL3_API_KEY` | Empty | Channel3 secret key |
| `CHANNEL3_BASE_URL` | `https://api.trychannel3.com` | Catalog API origin |
| `CHANNEL3_SEARCH_LIMIT` | `12` | Search limit, 1–30 |
| `CHANNEL3_MINIMUM_MONITOR_PRICE` | `50.00` | Low-price review heuristic, USD/unit; not a market-price guarantee |
| `PAYPAL_MODE` | `sandbox` | Sandbox payment mode |
| `PAYPAL_CLIENT_ID` | Empty | Sandbox REST app identifier; configure server-side |
| `PAYPAL_CLIENT_SECRET` | Empty | Sandbox REST app secret |
| `PAYPAL_BASE_URL` | `https://api-m.sandbox.paypal.com` | Sandbox API origin |

| Frontend variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Browser API address, including `/api/v1` |

Every `NEXT_PUBLIC_*` value is public and can be embedded in frontend builds. No provider secrets belong there.

## Verification

From `backend/`, on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

On macOS/Linux replace the executable with `.venv/bin/python`. Tests use isolated storage and mocked external integrations; they do not verify current provider credentials or a real buyer checkout.

From `frontend/`:

```text
npm run lint
npm run typecheck
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

Use `npm.cmd` in PowerShell. Stop the development frontend before building or starting production in the same folder: both use `.next-arc`. `start` requires a successful build. Keep the API running. There is no root-level build/start command.

Inspect saved agent executions from `backend/`, using your venv's Python and the request UUID:

```text
python -m scripts.inspect_agent_executions <request-uuid>
```

See [validation notes](VALIDATION.md) for completed checks and remaining verification limits.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Docker unavailable | Install/start Docker with Compose v2, or use native PostgreSQL |
| Database authentication failure | Match URL credentials to the actual role. Existing Docker volumes retain their original passwords; changing Compose environment values does not reset them |
| Missing database tables | Run `alembic upgrade head` from `backend/` against the API's database |
| Health reports degraded | Check database service, URL, credentials, and port |
| Windows error 10048 / port occupied | Check whether the existing server already works; stop the old process in its terminal before starting a duplicate |
| Request could not be completed | Check API health/logs, frontend URL including `/api/v1`, and exact CORS origin |
| Research fails | Verify Channel3 access/quota; deliberately select `demo_catalog` for a deterministic demo |
| Gemini result is degraded | Run the diagnostic; check key, model access, and quota. Deterministic recommendations can remain available |
| No eligible products | Inspect evidence; increase total budget or reduce quantity. Live products may not meet constraints |
| PayPal authentication fails | Check Sandbox REST app ID/secret and API URL; restart backend |
| Sandbox buyer login fails | Use a Personal Sandbox buyer distinct from the seller; check its password in the dashboard |
| Return cannot confirm payment | Keep backend/database running, check return origin and saved payment status before retrying |
| Environment edits have no effect | Restart the affected server; do not overwrite an existing `.env` blindly |

### Database port conflicts

If native PostgreSQL owns 5432, use it with its actual credentials, or change the Compose host mapping to `"127.0.0.1:5433:5432"` and set:

```dotenv
DATABASE_URL=postgresql+asyncpg://arc:arc@localhost:5433/arc
```

Restart Compose after editing its mapping, then migrate the database at the updated URL. Do not reset an existing database to solve a port conflict.

### Stop and resume

Use **Ctrl+C** in the frontend/backend terminals. From the root:

```text
docker compose stop postgres
```

The named volume preserves data. Resume with the same database and application startup commands. Do not remove the volume unless you intentionally want to erase local history.

## Security and limitations

- **Single shared workspace:** there is no authentication or tenant isolation. Anyone who can reach the API can operate the demo workspace and trigger configured provider usage or checkout actions. Keep the API bound to `127.0.0.1`; CORS is not authentication. Do not expose this setup publicly.
- **Secrets:** `.env` files are ignored; `.env.example` files are publishable. Keep real keys and buyer logins private. If a credential was ever committed, rotate it and clean history before publication; deleting its current file is insufficient. Use dedicated test credentials and controlled quotas.
- **Persistence:** PostgreSQL preserves records and events, but workflow/enrichment execution runs inside the API process. Restarts can interrupt active work; there is no durable task queue or complete automatic recovery. Avoid `--reload` during judging.
- **Updates:** server-sent events and request polling update the UI. Keep the API alive while processing. Stored history is durable; a running task or open connection is not.
- **Payments:** Sandbox only, explicit buyer approval, server-calculated amounts, and persisted payment records. There is no webhook reconciliation service. Keep the API running from approval through receipt; inspect uncertain payment state before retrying.
- **Scope:** USD, one supported category per request, no shipping/tax calculation or merchant fulfillment. Catalog evidence may be incomplete; monitor price filtering is a heuristic.
