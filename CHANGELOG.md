# AgentGuard Changelog

## [0.3.0] — 2026-02-23

### Summary
Four new features added: HITL approval demo flow, webhook notifications, policy templates, and a compliance reports dashboard.

---

### Feature 1 — HITL Demo Agent (`--scenario approval`)

**What it does**

Extends the demo agent with a full Human-in-the-Loop terminal experience. Running the demo with `--scenario approval` adds a fifth pipeline step where the agent tries to `delete:database` on `research_findings`. AgentGuard returns `status: "pending"` and the agent waits at an animated spinner until a human approves or denies the request in the UI.

**Files changed**

| File | Change |
|------|--------|
| `sdk/examples/demo_agent.py` | Added `--scenario` flag (`normal` / `approval`), `run_agent_with_approval()` function, `wait_with_spinner()` polling display, `delete_old_research_findings()` helper |
| `sdk/examples/demo_setup.py` | Added `--with-approval` flag that sets a `require_approval` rule for `delete:database → research_findings`; saves `DEMO_ADMIN_KEY` to `.demo_agent.env` so the agent can poll approval status |

**How to run**

```bash
# 1. Set up demo agent with approval policy
python sdk/examples/demo_setup.py --with-approval

# 2. Run the approval scenario
python sdk/examples/demo_agent.py --scenario approval

# 3. Open http://localhost:3000/approvals and click Approve or Deny
#    The terminal unblocks immediately after your decision.
```

**What you see in the terminal**

```
  STEP 5  ·  Human-in-the-Loop checkpoint  →  delete:database
            → Action   :  delete:database
            → Resource :  research_findings
            → Asking AgentGuard …
            ⏳  PENDING  —  Approval required!
            → Approval ID :  ap_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

  ┌──────────────────────────────────────────────────────────┐
  │  A human must approve this action before it proceeds.   │
  │  Open:  http://localhost:3000/approvals                 │
  │  Click Approve or Deny for the pending request.         │
  └──────────────────────────────────────────────────────────┘
            ⠋  Waiting for human decision… (12s)

  [after Approve is clicked]
            ✓  APPROVED by admin-se...  — "Routine cleanup approved"
  STEP 5b  ·  Executing approved delete
            → Removing stale entries for run_id=a1b2c3d4…
            ✓  Deleted 3 rows  (run_id=a1b2c3d4)
```

---

### Feature 2 — Webhook / Slack Notifications

**What it does**

Fires HTTP POST notifications to a configured webhook URL whenever an approval request is created, approved, or denied. Supports any generic JSON webhook receiver and auto-detects Slack incoming webhooks to send properly formatted Slack messages.

**Files changed**

| File | Change |
|------|--------|
| `backend/app/config.py` | Added `WEBHOOK_URL: Optional[str]` and `WEBHOOK_SECRET: Optional[str]` settings |
| `backend/app/utils/webhook.py` | **New** — `send_webhook(event_type, payload)` with background thread delivery, HMAC-SHA256 signing, and Slack message formatting |
| `backend/app/api/enforce.py` | Calls `send_webhook("approval.created", {...})` after an `ApprovalRequest` is created |
| `backend/app/api/approvals.py` | Calls `send_webhook("approval.approved", {...})` and `send_webhook("approval.denied", {...})` after a decision is recorded |

**Configuration** (`backend/.env`)

```dotenv
# Generic webhook (receives JSON)
WEBHOOK_URL=https://your-domain.com/webhooks/agentguard

# Slack incoming webhook (auto-formatted as Slack message)
WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx

# Optional HMAC signing (adds X-AgentGuard-Signature header)
WEBHOOK_SECRET=my-shared-secret
```

**Event payload shapes**

```jsonc
// approval.created
{
  "event": "approval.created",
  "timestamp": "2026-02-23T12:00:00Z",
  "approval_id": "...",
  "agent_id": "agt_xxx",
  "agent_name": "WebResearchBot",
  "action": "delete:database",
  "resource": "research_findings",
  "context": {...}
}

// approval.approved / approval.denied
{
  "event": "approval.approved",
  "timestamp": "2026-02-23T12:01:00Z",
  "approval_id": "...",
  "agent_id": "agt_xxx",
  "agent_name": "WebResearchBot",
  "action": "delete:database",
  "resource": "research_findings",
  "decision_reason": "Routine cleanup approved",
  "decision_by": "admin-se..."
}
```

**Signature verification** (receiver side)

```python
import hmac, hashlib
expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
assert request.headers["X-AgentGuard-Signature"] == f"sha256={expected}"
```

---

### Feature 3 — Policy Templates

**What it does**

Six built-in policy templates for common agent archetypes, accessible from the Policies UI. Click **Templates** on any agent card, select a template, preview its rules, and apply it to the editor in one click. Rules are fully editable before saving.

**Files changed**

| File | Change |
|------|--------|
| `backend/app/api/policies.py` | Added `POLICY_TEMPLATES` list and `templates_router` with `GET /policy-templates` endpoint |
| `backend/app/main.py` | Registered `policies.templates_router` |
| `ui/src/app/policies/page.tsx` | Added `PolicyTemplate` interface, `templates` state, `fetchTemplates()`, `openTemplateDialog()`, `applyTemplate()`, **Templates** button on agent cards, **Template Dialog** with rule preview |

**Available templates**

| ID | Name | Rules |
|----|------|-------|
| `read-only` | Read-Only Agent | 3 allow (read/list/query `*`), 4 deny (write/delete/execute/send `*`) |
| `research-agent` | Research Agent | 3 allow (search:web, read, write:research_findings), 4 deny (sensitive tables), 1 approval (delete:*) |
| `data-analyst` | Data Analyst | 4 allow (read/query/list/email reports), 3 deny (write/delete/execute) |
| `devops-agent` | DevOps Agent | 4 allow (deploy/restart/read/query metrics), 2 deny (db write, production exec), 2 approval (prod delete/deploy) |
| `customer-support` | Customer Support Agent | 4 allow (read tickets/customers, send email, write tickets), 3 deny (payments/sensitive deletes), 2 approval (write customers, read payments) |
| `full-access-dev` | Full Access (Dev Only) | 1 allow (`*:*`), 0 deny — **never use in production** |

**API endpoint**

```
GET /policy-templates
Authorization: X-ADMIN-KEY

Returns: Array of template objects with id, name, description, tags, allow[], deny[], require_approval[]
```

---

### Feature 4 — Compliance Reports

**What it does**

A new `/reports` page in the UI backed by a `GET /reports/summary` API endpoint. Shows a period-based compliance dashboard with summary stats, daily activity chart, approval funnel, top agents by activity, and top denied actions. Export as JSON for audit packages.

**Files changed**

| File | Change |
|------|--------|
| `backend/app/api/reports.py` | **New** — `GET /reports/summary?days=30` with overview, approvals, top_agents, top_denied_actions, daily_breakdown |
| `backend/app/main.py` | Registered `reports.router` |
| `ui/src/app/reports/page.tsx` | **New** — full compliance dashboard page |
| `ui/src/components/Navigation.tsx` | Added **Reports** nav item (BarChart3 icon), updated version to v0.3.0 |

**API endpoint**

```
GET /reports/summary?days=30
Authorization: X-ADMIN-KEY

Query params:
  days  — look-back window (1-365, default 30)

Returns:
{
  "period_days": 30,
  "generated_at": "...",
  "overview": { "total_actions", "allowed", "denied", "allow_rate", "deny_rate" },
  "approvals": { "total", "pending", "approved", "denied", "approval_rate" },
  "top_agents": [{ "agent_id", "agent_name", "total_actions", "allowed", "denied" }],
  "top_denied_actions": [{ "action", "count" }],
  "daily_breakdown": [{ "date", "total", "allowed", "denied" }]
}
```

**UI features**

- Period selector: 7 / 30 / 90 days
- 4 summary stat cards (total actions, allow %, deny %, pending approvals)
- Daily activity bar chart (green = allowed, red = denied, last 14 days)
- Approval funnel with approval rate progress bar
- Top agents table with per-agent allow/deny bars
- Top denied actions with relative bar chart
- Compliance summary strip with key status badges
- Export to JSON button

---

### Minor changes

- `backend/app/config.py`: Added `WEBHOOK_URL` and `WEBHOOK_SECRET` config fields
- `backend/app/main.py`: Registered `reports.router` and `policies.templates_router`
- `ui/src/components/Navigation.tsx`: Added Reports nav item; version bumped `v0.2.0 → v0.3.0`

---

## [0.2.0] — Previous release

- Human-in-the-Loop Approval Checkpoints (`require_approval` policy rules, `/approvals` API, Approvals UI page)
- AI-Assisted Policy Creation (`POST /agents/{id}/policy/generate` via Claude Haiku, "Generate with AI" dialog in Policies UI)
- Navigation live badge for pending approval count

## [0.1.0] — Initial release

- Agent identity management (create, list, delete agents with API key provisioning)
- Policy engine (allow/deny rules with wildcard matching, default deny)
- Audit logging (append-only, queryable, CSV/JSON export)
- Health/metrics endpoints (Prometheus)
- Rate limiting (SlowAPI)
- Live Demo page with real-time audit trail polling
