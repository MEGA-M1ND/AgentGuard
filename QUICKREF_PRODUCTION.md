# ⚡ AgentGuard Production Quick Reference

**One-page reference for production operations**

---

## 🚀 Quick Deploy

```bash
# 1. Install dependencies
cd backend && pip install -r requirements.txt

# 2. Configure environment
cp .env.production.example .env.production
# Edit .env.production

# 3. Run migrations
alembic upgrade head

# 4. Start service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🔑 Critical Environment Variables

```bash
# MUST CHANGE
ADMIN_API_KEY=<32-char-random-key>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Rate Limiting
RATE_LIMIT_STORAGE_URI=redis://redis:6379/0

# Production Settings
LOG_LEVEL=WARNING
LOG_FORMAT=json
METRICS_ENABLED=true
```

---

## 🏥 Health Checks

```bash
# Basic health
curl http://localhost:8000/health
# → {"status": "healthy"}

# Readiness (with DB)
curl http://localhost:8000/health/ready
# → {"status": "ready", "checks": {...}}

# Liveness
curl http://localhost:8000/health/live
# → {"status": "alive", "uptime_seconds": 3600}

# Statistics
curl http://localhost:8000/health/stats
# → Agent counts, DB latency, uptime
```

---

## 📊 Monitoring Endpoints

```bash
# Prometheus metrics (restrict to internal network)
curl http://localhost:8000/metrics

# Key metrics:
# - agentguard_http_requests_total
# - agentguard_http_request_duration_seconds
# - agentguard_enforcement_total
# - agentguard_logs_total
# - agentguard_database_connections
```

---

## 🚨 Alert Thresholds

| Alert | Threshold | Severity |
|-------|-----------|----------|
| High error rate | > 5% for 5min | Warning |
| Critical errors | > 10% for 3min | Critical |
| Slow requests | P95 > 1s | Warning |
| Very slow | P95 > 5s | Critical |
| DB connections | > 15/20 | Warning |
| Auth failures | > 0.5/sec | Warning |
| Brute force | > 5/sec | Critical |

---

## ⚡ Rate Limits

| Endpoint Type | Limit | Per |
|---------------|-------|-----|
| Enforcement | 1000/min | Agent |
| Log submission | 1000/min | Agent |
| Admin create | 50/hour | Admin |
| Admin read | 200/hour | Admin |
| Public | 100/min | IP |

**Response**: `429 Too Many Requests`

---

## 🔒 Security Checklist

- [ ] Changed ADMIN_API_KEY
- [ ] Enabled HTTPS
- [ ] Configured firewall
- [ ] Set up VPC
- [ ] Enabled DB encryption
- [ ] Restricted CORS origins
- [ ] Using secrets manager

---

## 💾 Backup

```bash
# Daily backup (2 AM)
0 2 * * * /scripts/backup.sh

# Restore
pg_restore -h $DB_HOST -U $DB_USER -d agentguard backup.sql
```

**Retention**: 7 days local, 30 days S3

---

## 🔄 Deployment Process

```bash
# 1. Run tests
pytest

# 2. Build image
docker build -t agentguard:v0.1.0 .

# 3. Run migrations
alembic upgrade head

# 4. Deploy (blue-green)
kubectl apply -f k8s/deployment-green.yaml

# 5. Switch traffic
kubectl patch service agentguard -p '{"spec":{"selector":{"version":"green"}}}'

# 6. Rollback if needed
kubectl patch service agentguard -p '{"spec":{"selector":{"version":"blue"}}}'
```

---

## 🐛 Troubleshooting

### High Error Rate
```bash
# Check logs
kubectl logs -l app=agentguard --tail=100

# Check metrics
curl http://localhost:8000/metrics | grep error

# Check database
curl http://localhost:8000/health/ready
```

### Slow Performance
```bash
# Check latency
curl http://localhost:8000/metrics | grep duration

# Check DB connections
curl http://localhost:8000/health/stats

# Check slow queries
psql -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10"
```

### Rate Limit Issues
```bash
# Check violations
curl http://localhost:8000/metrics | grep 429

# Check Redis
redis-cli ping
redis-cli info
```

---

## 📞 Emergency Contacts

| Severity | Response Time | Contact |
|----------|---------------|---------|
| P0 (Critical) | < 15 min | PagerDuty |
| P1 (High) | < 1 hour | On-call engineer |
| P2 (Medium) | < 4 hours | Team Slack |
| P3 (Low) | < 1 day | Ticket system |

---

## 📚 Documentation

- 🚀 **Deploy**: [PRODUCTION.md](PRODUCTION.md)
- ✅ **Checklist**: [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
- 📊 **Features**: [PRODUCTION_FEATURES.md](PRODUCTION_FEATURES.md)
- 📖 **Summary**: [SUMMARY_PRODUCTION_READY.md](SUMMARY_PRODUCTION_READY.md)

---

## 🎯 Success Criteria

### Deployment
- [ ] All health checks passing
- [ ] Metrics being collected
- [ ] Logs flowing to aggregator
- [ ] Alerts configured
- [ ] Smoke tests passed

### First 24 Hours
- [ ] Error rate < 1%
- [ ] P95 latency < 500ms
- [ ] No critical alerts
- [ ] Backups running
- [ ] Monitoring working

---

**Print this page and keep it handy!** 📄

**Last Updated**: 2024-02-11 | **Version**: 0.1.0
