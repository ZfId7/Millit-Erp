# MERP (Millit ERP)  Codex Rules

BRANCH LOCK
- You are operating ONLY in D:\Millit_ERP_2nd on branch "2nd".
- NEVER commit or push. The user commits/pushes manually.
- Do not run destructive git commands (NO: git clean, git reset --hard, git checkout -- .) unless explicitly asked.

NON-NEGOTIABLE LAWS
- Master BOM drives routing and ops.
- Work Orders = demand, Jobs/Builds = execution.
- Ops queues consume ops; they do not plan.
- Components are manufactured; assemblies explode.
- No hidden routing fallbacks.
- Desktop-first UI.
- Auth: @login_required / @admin_required.
- Explicit deletes (no cascade magic).
- Ledger is LAW: no direct qty mutations.
- Thin routes; business logic in services; defaults/const in config.
- Prefer new files over growing existing ones.

WORKFLOW
- Explain changes before editing files.
- Ask before running shell commands.
- Keep changes minimal and scoped to the request.
