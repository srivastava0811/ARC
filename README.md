# ARC — Autonomous Resource Coordinator

**Turn a procurement request into evidence-backed recommendations and an approved PayPal Sandbox payment.**

Built for the PayPal AI Hackathon · [MIT licensed](LICENSE) · Runs locally

[Getting started](#getting-started) · [Demo walkthrough](#demo-walkthrough) · [Documentation](#architecture-and-documentation)

## Overview

Small teams often compare products, check budgets, and coordinate purchase approval across separate tools. ARC brings those steps into one workspace: describe what you need, inspect the recommendations and supporting evidence, and approve a Sandbox checkout.

ARC separates product eligibility and pricing checks from AI-generated explanations. This keeps purchasing constraints explicit while Gemini helps explain the choices. The buyer remains in control of payment approval.

## Key features

- **Natural-language requests** for monitors, keyboards, and mice, with clarification when required information is missing.
- **Four specialized stages** with visible progress: Planner, Researcher, Evaluator, and Reporter.
- **Product discovery and comparison** through Channel3 or a clearly labeled synthetic demo catalog.
- **Constraint-aware evaluation** of quantity, total USD budget, screen size, and supported connectivity requirements.
- **Gemini enrichment** for candidate explanations, report summaries, and limitations.
- **Human approval and PayPal Sandbox checkout**, with server-calculated amounts and payment confirmation on return.
- **Persistent reports, receipts, and request history** in PostgreSQL, plus stored agent execution records for inspection.

## How ARC works

```mermaid
flowchart TD
    U[User request] --> P[Planner: extract requirements]
    P --> R[Researcher: discover products]
    R --> E[Evaluator: check constraints and rank]
    E --> T[Reporter: present recommendations]
    T --> H[Human review and approval]
    H --> S[PayPal Sandbox approval and capture]
    S --> D[Receipt and procurement history]
    C[Channel3 or demo catalog] --> R
    E -. explanation enrichment .-> G[Gemini]
    T -. summary enrichment .-> G
```

| Agent | Responsibility |
| --- | --- |
| Planner | Parses category, quantity, budget, and constraints; requests clarification when needed. |
| Researcher | Retrieves products from the selected catalog and normalizes their evidence. |
| Evaluator | Applies deterministic eligibility checks and scoring; optionally uses Gemini to explain the results. |
| Reporter | Produces the recommendation report; optionally uses Gemini to summarize the evidence and limitations. |

The agents are **orchestration stages, not four independent LLM calls**. Normal request planning is deterministic. With `AGENT_MODE=gemini`, evaluation and report enrichment run after the initial recommendations are saved. Gemini cannot change eligibility, scores, or prices. If enrichment fails, deterministic results can remain available; a Channel3 failure never silently substitutes demo products.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| AI | Gemini through the Google Gen AI SDK |
| Product discovery | Channel3 API or synthetic demo catalog |
| Database | PostgreSQL with asyncpg |
| Payments | PayPal Sandbox REST API: OAuth, order creation, approval, capture |
| Live updates | Server-sent events and request polling |

<a id="install-and-run"></a>

## Getting started

### Prerequisites

- **Python 3.11+** and pip; Python 3.11 is the verified baseline.
- **Node.js 22+** and npm; use an active LTS release.
- **Docker with Compose v2**, running, or a native PostgreSQL installation.
- Git, a modern browser, and internet access for installation and enabled integrations.

No editor extensions are required. Ports **3000**, **8000**, and **5432** should be available.

### 1. Clone and start PostgreSQL

```text
git clone https://github.com/srivastava0811/ARC.git
cd ARC
docker compose up -d --wait postgres
docker compose exec -T postgres pg_isready -U arc -d arc
```

Compose creates PostgreSQL 16 with database/user/password `arc` and a persistent volume. Expect `accepting connections`. These credentials are for local development only. If 5432 is occupied, use the [native database or alternate-port instructions](docs/LOCAL_SETUP.md#database-port-conflicts).

### 2. Configure and start the backend

Run one of these blocks from the repository root. The example environment matches the Docker database; edit `DATABASE_URL` before migration if using another database.

**Windows PowerShell:**

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**macOS / Linux:**

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
test -f .env || cp .env.example .env
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Leave this terminal running. **No seed command is needed**: ARC creates the workspace on the first request. Migrations must be applied explicitly; expected head is `0003_paypal_sandbox_payments`.

Check [API health](http://localhost:8000/api/v1/health) for `status: "ok"` and `services.database: "connected"`. Browse the [interactive API docs](http://localhost:8000/docs).

### 3. Configure and start the frontend

Open a **second terminal at the repository root**.

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

Open **[http://localhost:3000](http://localhost:3000)** for the landing page and choose **Launch ARC**, or go directly to the [workspace](http://localhost:3000/workspace). Use `localhost` consistently to match CORS and PayPal return URLs.

<a id="environment-reference"></a>

## Environment variables

The templates are [backend/.env.example](backend/.env.example) and [frontend/.env.example](frontend/.env.example). Copy them as shown above; keep real credentials out of Git. Restart the affected server after environment changes.

| File | Essential configuration |
| --- | --- |
| `backend/.env` | `DATABASE_URL=postgresql+asyncpg://arc:arc@localhost:5432/arc` |
| `backend/.env` | `FRONTEND_ORIGIN=http://localhost:3000` |
| `frontend/.env.local` | `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` |

### Choose a mode

| Mode | Backend settings | External access needed |
| --- | --- | --- |
| Deterministic demo, default | `AGENT_MODE=fixture`, `CATALOG_PROVIDER=demo_catalog` | None for recommendations; products are synthetic |
| AI with predictable products | `AGENT_MODE=gemini`, `CATALOG_PROVIDER=demo_catalog` | Gemini key |
| AI and live product discovery | `AGENT_MODE=gemini`, `CATALOG_PROVIDER=channel3` | Gemini and Channel3 keys |
| Sandbox checkout in any mode | PayPal settings below | Sandbox REST app and a Sandbox buyer |

**Gemini:** Obtain a key from [Google AI Studio](https://aistudio.google.com/apikey) and set `GEMINI_API_KEY` in the backend. Confirm access/quota for the model IDs in the example file; change them if necessary.

**Channel3:** Obtain access through [Channel3 for developers](https://trychannel3.com/developers) and set `CHANNEL3_API_KEY`. Live prices, evidence, and availability may produce different results from the demo.

**PayPal Sandbox:** In the [Developer Dashboard](https://developer.paypal.com/dashboard/), select **Sandbox** under **Apps & Credentials** and create/select a REST app associated with a Sandbox **Business** seller. Put its credentials in `backend/.env`:

```dotenv
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your-sandbox-app-client-id
PAYPAL_CLIENT_SECRET=your-sandbox-app-secret
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
```

Create/select a separate **Personal** buyer under **Sandbox Accounts**, with sufficient test balance. Use that account's email/password **on PayPal's Sandbox checkout page**, not in ARC's environment. See [PayPal's account guide](https://developer.paypal.com/sandbox-testing/accounts/).

Provider keys and PayPal credentials belong **only in the backend**. Every `NEXT_PUBLIC_*` value is public. The [full setup reference](docs/LOCAL_SETUP.md) covers all environment variables, native PostgreSQL, provider checks, and troubleshooting.

## Demo walkthrough

Use `fixture` + `demo_catalog` for predictable products; configure PayPal Sandbox to include checkout. Enable Gemini for AI enrichment, or Channel3 for live research.

1. Open the [ARC workspace](http://localhost:3000/workspace) and submit **`Find three 27-inch monitors for our office under $600 total.`**
2. Watch the four stages complete, then inspect the product evidence and tradeoffs. In the synthetic catalog, **StudioView 27 4K** costs **$189 per unit / $567 for three**. Larger totals fail the budget check; a 24-inch model fails the size requirement.
3. Select the eligible option and choose **Review & approve**. Review the quantity and total, then continue to PayPal Sandbox.
4. Sign in as the Sandbox **Personal buyer** and approve. Keep both servers running while returning to ARC's payment-processing screen.
5. Wait for the completed capture and receipt. Confirm the product, quantity, and total, then open [History](http://localhost:3000/history). A redirect alone does not confirm payment.

Additional requests: **`I need 4 wireless keyboards under $200.`** or **`I need 5 mice under $100.`** To test clarification, request **`Find three monitors under $600 total.`** and supply **`27-inch monitors`** when asked for size.

Without provider keys, the default mode demonstrates procurement but not live AI/catalog calls. Without PayPal credentials, recommendations work but checkout cannot complete.

## Architecture and documentation

| Resource | Contents |
| --- | --- |
| [Local setup reference](docs/LOCAL_SETUP.md) | Full configuration, native PostgreSQL, diagnostics, troubleshooting, and security |
| [Backend guide](backend/README.md) / [Frontend guide](frontend/README.md) | Directory-specific commands |
| [Workflow orchestration](backend/app/services/workflow.py) | Stage execution, persistence, and optional enrichment |
| [PayPal integration](backend/app/services/paypal.py) | Server-side OAuth, order creation, and capture |

## Limitations

- **Sandbox payments only.** Transactions use test funds. Channel3 discovery does not provide third-party merchant checkout or fulfillment. Prices exclude shipping and tax.
- **Focused product support.** One category per request: monitors, keyboards, or mice; USD budgets. Catalog evidence may be incomplete, and low monitor price filtering is a heuristic.
- **Local shared workspace.** There is no authentication or tenant isolation. Keep the API on `127.0.0.1`; CORS is not access control. Anyone with API access can trigger configured provider usage and checkout actions.
- **Process-bound execution.** PostgreSQL preserves records, but active workflows/enrichment can be interrupted by an API restart. There is no durable task queue or webhook-based payment reconciliation. Keep servers running through receipt confirmation and inspect uncertain payment state before retrying.
- **External access required for integrations.** Models, quotas, and catalog availability vary. Use your own provider credentials and keep keys and buyer passwords private.

## License

[MIT](LICENSE). Third-party dependencies and external services retain their respective licenses and terms.
