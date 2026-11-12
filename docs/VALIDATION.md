# Local validation record

## Verified during the readiness audit

- Commands and environment names checked against package scripts, Python project
  configuration, settings, templates, Compose, routes, and migrations.
- All three Alembic migrations applied to an empty native PostgreSQL 18 database,
  reaching `0003_paypal_sandbox_payments`. Repeating upgrade was safe and Alembic
  reported no schema drift. No seed is needed.
- Backend tests passed: 31 tests, including deterministic workflows and mocked
  PayPal checkout/capture/receipt behavior.
- A publication-candidate scan covered 77 non-ignored files. No matches were
  found for the four configured local provider credential values or the checked
  Google-key/private-key patterns. Only the two `.env.example` templates were
  selected; private environment files were excluded. This is a targeted scan,
  not proof that arbitrary secrets or future Git history are clean.
- Backend Ruff, frontend ESLint, and TypeScript checks passed. An isolated Next.js
  production build passed without overwriting the running development build.
- Existing local integration use established that the workflow can operate with
  external providers; future access, quota, and availability are not guaranteed.

## Limits and pending checks

- Docker is unavailable here. Compose and its health check were inspected, but
  container startup still needs execution on a Docker-equipped machine.
- Checks used installed dependencies. Fresh Python installation and `npm ci`
  must still be performed from the final public clone.
- macOS/Linux commands were reviewed, not executed on those operating systems.
- Automated payment tests mock PayPal. Recheck actual buyer approval and completed
  capture with the final judging configuration.
- Git was initialized after the source audit; no commits exist yet. Scan the
  final staged files and resulting history before publication. A source scan
  cannot establish that future commits are free of secrets.
- Four stages exist; normal planning is deterministic and Gemini enrichment is
  optional and asynchronous.

## Submission changes

Expanded the root README; replaced stale subdirectory instructions; added MIT
LICENSE and submission checklist; expanded ignore rules for secrets, dependencies,
generated files, and logs. No application workflow behavior was changed.
