# AgentGuard Demo Guide

Complete guide for demonstrating AgentGuard's features.

## Quick Start

### 1. Start the Services

```bash
# Terminal 1: Start Backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Frontend
cd ui
npm run dev
```

### 2. Seed Demo Data

```bash
cd backend
python seed_demo_data.py
```

**Demo Agents Created:**
1. **CustomerSupportBot** - Support Team (read tickets, send emails, but NO delete or payment access)
2. **DataAnalyzer** - Analytics Team (read & query data, but NO modify or payment access)
3. **ContentModerator** - Moderation Team (can delete user content, but NOT official content)

**Save the API Keys from the output!** You'll need them for testing.

Example output:
```
[+] Created agent: CustomerSupportBot (ID: agt_RUCMM3Cj...)
    API Key: agk_YWFWMrPYhkzBMLs1...
```

## Demo Flow

### Step 1: Dashboard Overview (http://localhost:3000)

**What to show:**
- 📊 **Activity Timeline Chart** - Shows allowed vs denied actions over time
- 📊 **Top Actions Chart** - Most frequently used actions
- 📊 **Agent Activity Distribution** - Pie chart showing which agents are most active
- 📊 **Success Metrics** - Overall allow/deny rates
- 🔄 **Refresh Button** - Real-time data updates

**Talking points:**
- "This is your central command center for AI agent governance"
- "You can see at a glance which agents are active, what actions they're taking, and whether policies are blocking unwanted behavior"

### Step 2: Agents Page (http://localhost:3000/agents)

**What to show:**
- Click **Create New Agent** button
- Fill in agent details (name, team, environment)
- **IMPORTANT**: Copy the API key when shown (it's only displayed once!)
- View all agents in the system
- Show agent cards with status badges

**Talking points:**
- "Creating an agent is simple - just provide a name and team"
- "Each agent gets a unique API key for authentication"
- "You can see all your agents at a glance with their status"

### Step 3: Policies Page (http://localhost:3000/policies)

**What to show:**
- Select an agent (e.g., CustomerSupportBot)
- Show existing policy with Allow and Deny rules
- Click **Edit Policy** to modify
- Add a new rule using the quick-add buttons
- Click **Preview JSON** to see the raw policy
- Save the policy

**Example Policy Explanation:**
```
CustomerSupportBot:
✅ ALLOW:
   - read:ticket (any resource)
   - read:customer (any resource)
   - send:email (support/* only)
   - update:ticket (any resource)

❌ DENY:
   - delete:* (can't delete anything)
   - read:payment (no payment data access)
   - update:customer (can't modify customers)
```

**Talking points:**
- "Policies use a deny-first approach for security"
- "You can use wildcards (*) for flexible rules"
- "Resource patterns let you restrict access to specific paths"

### Step 4: Test Actions (http://localhost:3000/test) ⭐ NEW!

**What to show:**
This is your **live policy enforcement** demonstration!

1. **Select Agent**: Choose CustomerSupportBot
2. **Enter API Key**: Paste the API key you saved from creation/seeder
3. **Try Allowed Action**:
   - Action: `read:ticket`
   - Resource: `ticket-12345`
   - Click "Test Action"
   - ✅ **Result**: Action Allowed!

4. **Try Denied Action**:
   - Action: `delete:ticket`
   - Resource: `ticket-12345`
   - Click "Test Action"
   - ❌ **Result**: Action Denied! (Shows reason: "Denied by rule: delete:* on *")

5. **Try Sample Actions**:
   - Click on sample actions in the right panel
   - Show how different actions are handled differently

**Talking points:**
- "This is where you can test policies in real-time before deploying to production"
- "Watch how the policy engine evaluates each request instantly"
- "Every test creates an audit log entry for compliance tracking"

### Step 5: Audit Logs (http://localhost:3000/logs)

**What to show:**
- Show the full audit trail
- Use **Date Range Filter** to filter logs
- Use **Agent Filter** to see specific agent activity
- Click **Export CSV** or **Export JSON** for compliance reports
- Click on a row to **expand** and see full details (context, metadata)

**Talking points:**
- "Every action is logged - allowed or denied"
- "Full audit trail for compliance and security investigations"
- "Export capabilities for reporting to auditors or management"

## Demo Scenarios

### Scenario 1: Security Violation Caught
```
Agent: CustomerSupportBot
Action: read:payment
Resource: credit-card-data

Result: ❌ DENIED
Reason: "Denied by rule: read:payment on *"

Story: "A support agent tried to access payment information, but our policy blocked it. This prevents data breaches from social engineering attacks."
```

### Scenario 2: Legitimate Access Granted
```
Agent: CustomerSupportBot
Action: read:ticket
Resource: ticket-12345

Result: ✅ ALLOWED
Reason: "Allowed by rule: read:ticket on *"

Story: "The agent can access support tickets as expected for their role. The system grants access only to what's needed."
```

### Scenario 3: Resource-Specific Restriction
```
Agent: ContentModerator
Action: delete:content
Resource: official/announcement

Result: ❌ DENIED
Reason: "Denied by rule: delete:content on official/*"

Story: "Content moderators can delete user-generated spam, but they can't accidentally delete official content. Resource patterns give you fine-grained control."
```

## API Keys Reference

After running the seeder, save these keys:

```
CustomerSupportBot: agk_YWFWMrPYhkzBMLs1... (from seeder output line 6)
DataAnalyzer: agk_XbTfXeAsgVD9b-vk... (from seeder output line 8)
ContentModerator: agk_KYoXUFVELyquu1-c... (from seeder output line 10)
```

## Key Features to Highlight

### 1. Real-Time Policy Enforcement ⚡
- Instant decision making (< 10ms typically)
- No delays in application workflow

### 2. Flexible Policy Language 🎯
- Wildcard support (`*`)
- Resource path patterns (`support/*`)
- Case-insensitive matching
- Natural language action formats

### 3. Complete Audit Trail 📋
- Every action logged (allowed or denied)
- Exportable for compliance
- Searchable and filterable
- Expandable for full context

### 4. Production-Ready Dashboard 📊
- Beautiful charts and visualizations
- Real-time updates
- Toast notifications
- Responsive design

### 5. Live Testing Environment 🧪
- Test policies before deployment
- Sample actions for quick demos
- Immediate feedback
- Creates real audit logs

## Troubleshooting

### UI Not Loading
```bash
# Check if services are running
curl http://localhost:8000/health
curl http://localhost:3000
```

### No Data in Dashboard
```bash
# Re-run the seeder
cd backend
python seed_demo_data.py
```

### Test Action Not Working
- Make sure you copied the full API key (starts with `agk_`)
- Check that the agent has a policy configured
- Verify the backend is running on port 8000

## LinkedIn Demo Checklist

For creating LinkedIn assets:

- [ ] Run seeder to populate data
- [ ] Take screenshots of:
  - [ ] Dashboard with charts
  - [ ] Test Action page showing ALLOWED result
  - [ ] Test Action page showing DENIED result
  - [ ] Audit Logs page with filters
- [ ] Record 60-second video showing:
  1. Dashboard overview (10s)
  2. Create agent (10s)
  3. Set policy (15s)
  4. Test allowed action (10s)
  5. Test denied action (10s)
  6. Show audit log (5s)

## Next Steps

### Priority 4: Production Readiness
- [ ] Add dark mode toggle
- [ ] Set up real-time log updates (WebSocket/polling)
- [ ] Add policy templates library
- [ ] Implement role-based admin access
- [ ] Add agent API key rotation
- [ ] Set up monitoring alerts

### Future Enhancements
- [ ] Multi-tenant support
- [ ] Advanced analytics (ML-based anomaly detection)
- [ ] Policy versioning and rollback
- [ ] Approval workflows for sensitive actions
- [ ] Integration with external identity providers (OAuth, SAML)

---

**AgentGuard** - Enterprise AI Governance Made Simple
