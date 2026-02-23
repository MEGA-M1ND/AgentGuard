# AgentGuard - Quickest Start 🚀

Get AgentGuard running in 3 commands:

## Step 1: Install Backend Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

## Step 2: Setup Database & Environment

```powershell
# Set environment variables (copy-paste all these lines together)
$env:DATABASE_URL = "sqlite:///./agentguard.db"
$env:ADMIN_API_KEY = "admin-secret-key"
$env:CORS_ORIGINS = "http://localhost:3000"

# Run database migrations
alembic upgrade head
```

## Step 3: Start Backend

```powershell
# Start the server (still in backend directory)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend is now running at: **http://localhost:8000**

API docs available at: **http://localhost:8000/docs**

---

## Test It Works

Open a **NEW PowerShell window** and run:

```powershell
cd sdk
pip install -e .

# Set environment variables
$env:AGENTGUARD_URL = "http://localhost:8000"
$env:ADMIN_API_KEY = "admin-secret-key"

# Run the demo
python examples\quickstart.py
```

You should see output showing:
- ✓ Agent created
- ✓ Policy set
- ✓ Enforcement checks
- ✓ Logs submitted

---

## Optional: Start UI

Open **another** PowerShell window:

```powershell
cd ui
npm install
npm run dev
```

UI available at: **http://localhost:3000**

---

## Troubleshooting

### "alembic: command not found"

The dependencies aren't installed. Run:
```powershell
cd backend
pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'app'"

Make sure you're in the `backend` directory when running `uvicorn`.

### Port 8000 already in use

Either stop the other service or change the port:
```powershell
uvicorn app.main:app --reload --port 8001
```

### Database errors

Delete the database and recreate:
```powershell
cd backend
Remove-Item agentguard.db -ErrorAction SilentlyContinue
alembic upgrade head
```

---

## What's Next?

1. ✅ Backend running: http://localhost:8000
2. ✅ Check API docs: http://localhost:8000/docs
3. ✅ Run the demo (see above)
4. ✅ View logs in UI: http://localhost:3000 (if started)
5. Read [README.md](README.md) for full documentation
6. Integrate with your AI agents using the SDK!

---

**Need help?** See [LOCAL_SETUP.md](LOCAL_SETUP.md) for detailed instructions.
