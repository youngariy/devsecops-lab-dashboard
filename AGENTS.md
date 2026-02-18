# Repository Guidelines

## Project Structure & Module Organization
This repository is a small monorepo with two apps and shared infra:
- `apps/web`: Next.js 14 + TypeScript dashboard UI (`app/`, `lib/`, `globals.css`).
- `apps/api`: Flask API (`src/app`) with routes, services, repositories, models, and tests in `tests/`.
- `infra/docker`: local orchestration (`docker-compose.yml`, `docker-compose.prod.yml`).
- `infra/nginx`: Nginx templates used by Compose.
- Root files: `.env.example`, `README.md`, `package.json` (workspace-level metadata only).

## Build, Test, and Development Commands
- `docker compose -f infra/docker/docker-compose.yml up --build`: run full local stack (API, web, Nginx on `:8080`).
- `cd apps/web && npm install && npm run dev`: start web app on `:3000`.
- `cd apps/web && npm run build && npm run start`: production-like web build/start.
- `cd apps/web && npm run lint`: run Next.js ESLint checks.
- `cd apps/api && pip install -r requirements.txt && pytest`: run backend tests.
- `cd apps/api && python src/main.py`: run Flask API on `:5000`.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, snake_case for functions/modules, PascalCase for classes.
- TypeScript/React: 2-space indentation, PascalCase components, camelCase variables/functions.
- Keep route and service names explicit (`pipelines.py`, `pipeline_service.py`).
- Prefer small, focused modules; keep business logic in `services/`, not route handlers.

## Testing Guidelines
- Backend tests use `pytest` (`apps/api/pytest.ini` sets `pythonpath=src`).
- Place tests in `apps/api/tests` with names like `test_<feature>.py`.
- Add/extend tests for behavior changes in routes, services, and sync logic.
- No frontend test suite is configured yet; at minimum, run `npm run lint` before PRs.

## Commit & Pull Request Guidelines
- Recent history uses short imperative messages; many commits follow Conventional Commit style (`fix(cd): ...`, `chore(cd): ...`).
- Recommended format: `<type>(<scope>): <summary>` (e.g., `feat(api): add paginated runs endpoint`).
- Keep commits atomic and scoped to one concern.
- PRs should include: purpose, key changes, test/lint evidence, linked issue, and UI screenshots for dashboard changes.

## Security & Configuration Tips
- Copy `.env.example` and set `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_TOKEN`, and `SYNC_TOKEN` for sync features.
- Never commit real tokens/secrets; use environment variables or CI secrets only.
