# 🚀 AgentGuard Production Deployment Guide

This guide covers deploying AgentGuard to production with best practices for security, performance, and reliability.

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Configuration](#configuration)
4. [Security Hardening](#security-hardening)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Backup & Disaster Recovery](#backup--disaster-recovery)
7. [Performance Tuning](#performance-tuning)
8. [Deployment Process](#deployment-process)
9. [Post-Deployment Verification](#post-deployment-verification)
10. [Maintenance & Operations](#maintenance--operations)

---

## ✅ Pre-Deployment Checklist

### Security
- [ ] Change default `ADMIN_API_KEY` to a strong, randomly generated value
- [ ] Enable HTTPS/TLS for all traffic
- [ ] Configure firewall rules (only allow necessary ports)
- [ ] Set up VPC/network isolation
- [ ] Enable database encryption at rest
- [ ] Configure database SSL/TLS connections
- [ ] Review and restrict CORS origins
- [ ] Set up secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Enable rate limiting
- [ ] Configure reverse proxy (Nginx, Traefik, AWS ALB)

### Infrastructure
- [ ] Provision production database (PostgreSQL with replication)
- [ ] Set up Redis for rate limiting (replace memory:// storage)
- [ ] Configure load balancer with health checks
- [ ] Set up CDN for static assets (if serving UI)
- [ ] Configure auto-scaling (if needed)
- [ ] Set up container orchestration (Kubernetes, ECS, etc.)

### Monitoring
- [ ] Set up Prometheus metrics collection
- [ ] Configure Grafana dashboards
- [ ] Set up log aggregation (ELK, Datadog, CloudWatch)
- [ ] Configure alerting (PagerDuty, Opsgenie, Slack)
- [ ] Set up uptime monitoring (Pingdom, UptimeRobot)
- [ ] Configure APM (Application Performance Monitoring)

### Backup & DR
- [ ] Configure automated database backups
- [ ] Test backup restoration process
- [ ] Set up database replication (primary-replica)
- [ ] Define RTO (Recovery Time Objective) and RPO (Recovery Point Objective)
- [ ] Document disaster recovery procedures
- [ ] Set up off-site backup storage

### Compliance
- [ ] Review data retention policies
- [ ] Configure log retention (90 days minimum recommended)
- [ ] Set up audit log exports for compliance
- [ ] Review GDPR/CCPA requirements (if applicable)
- [ ] Document data processing procedures

---

## 🏗️ Infrastructure Setup

### 1. Database (PostgreSQL)

#### Recommended Specs (Medium Traffic)
- **Instance**: db.r5.large (2 vCPU, 16GB RAM)
- **Storage**: 100GB SSD with auto-scaling
- **Multi-AZ**: Enabled for high availability
- **Backups**: Daily automated backups, 7-day retention

#### Database Configuration
```sql
-- Create database and user
CREATE DATABASE agentguard;
CREATE USER agentguard WITH ENCRYPTED PASSWORD 'your-secure-password-here';
GRANT ALL PRIVILEGES ON DATABASE agentguard TO agentguard;

-- Enable required extensions
\c agentguard
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

#### Connection Pooling
```bash
# Use PgBouncer for connection pooling
DATABASE_URL=postgresql://agentguard:password@pgbouncer:6432/agentguard
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### 2. Redis (Rate Limiting)

#### Recommended Specs
- **Instance**: cache.t3.medium (2 vCPU, 3.09GB RAM)
- **Multi-AZ**: Enabled
- **Persistence**: RDB snapshots every 6 hours

#### Configuration
```bash
RATE_LIMIT_STORAGE_URI=redis://redis:6379/0
```

### 3. Application Server

#### Recommended Specs (per instance)
- **CPU**: 2-4 vCPUs
- **RAM**: 4-8GB
- **Instances**: 2+ (for high availability)
- **Auto-scaling**: Based on CPU (target 70%)

#### Docker Deployment
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    image: agentguard/backend:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ADMIN_API_KEY=${ADMIN_API_KEY}
      - RATE_LIMIT_STORAGE_URI=${RATE_LIMIT_STORAGE_URI}
      - LOG_LEVEL=WARNING
      - LOG_FORMAT=json
      - METRICS_ENABLED=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env.production`:

```bash
# ===== Database =====
DATABASE_URL=postgresql://agentguard:PASSWORD@db-host:5432/agentguard
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# ===== Authentication =====
ADMIN_API_KEY=<GENERATE-STRONG-KEY-32-CHARS-MIN>

# ===== Server =====
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=WARNING
LOG_FORMAT=json

# ===== CORS =====
CORS_ORIGINS=https://dashboard.yourdomain.com,https://api.yourdomain.com

# ===== Rate Limiting =====
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URI=redis://redis-host:6379/0

# ===== Monitoring =====
METRICS_ENABLED=true
METRICS_PATH=/metrics

# ===== Security =====
ENABLE_HTTPS=true
TRUST_PROXY_HEADERS=true

# ===== Performance =====
REQUEST_TIMEOUT=30
MAX_REQUEST_SIZE=10485760
```

### Generate Secure Admin Key

```bash
# Generate a secure 32-character key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🔒 Security Hardening

### 1. HTTPS/TLS Configuration

#### Nginx Reverse Proxy
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Metrics endpoint (restrict to internal network)
    location /metrics {
        allow 10.0.0.0/8;  # Internal network
        deny all;
        proxy_pass http://backend:8000;
    }
}
```

### 2. Database Security

```sql
-- Restrict permissions
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO agentguard;

-- Enable SSL
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/path/to/server.crt';
ALTER SYSTEM SET ssl_key_file = '/path/to/server.key';

-- Enable audit logging
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_statement = 'mod';  -- Log all modifications
```

### 3. Network Security

#### Firewall Rules (AWS Security Groups)
```yaml
Inbound Rules:
  - Port 443 (HTTPS): 0.0.0.0/0 (public)
  - Port 8000 (Backend): Load Balancer Security Group only
  - Port 5432 (PostgreSQL): Backend Security Group only
  - Port 6379 (Redis): Backend Security Group only

Outbound Rules:
  - All traffic: 0.0.0.0/0 (required for external services)
```

---

## 📊 Monitoring & Alerting

### 1. Prometheus Metrics

#### Available Metrics
```
# HTTP Metrics
agentguard_http_requests_total{method, endpoint, status}
agentguard_http_request_duration_seconds{method, endpoint}
agentguard_http_errors_total{method, endpoint, status}

# Agent Metrics
agentguard_enforcement_total{agent_id, action, allowed}
agentguard_logs_total{agent_id, action, result}
agentguard_policy_evaluations_total{outcome}

# System Metrics
agentguard_active_agents
agentguard_database_connections
agentguard_authentication_failures_total{type}
```

### 2. Grafana Dashboard

Import the provided Grafana dashboard: `monitoring/grafana-dashboard.json`

**Key Panels:**
- Request rate and latency
- Error rate by endpoint
- Agent activity by agent_id
- Policy enforcement (allow/deny ratio)
- Database performance
- Rate limit violations

### 3. Alerting Rules

#### Prometheus Alerts
```yaml
groups:
  - name: agentguard
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(agentguard_http_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: SlowRequests
        expr: histogram_quantile(0.95, rate(agentguard_http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "Slow requests detected"
          description: "P95 latency is {{ $value }} seconds"

      - alert: DatabaseConnectionsHigh
        expr: agentguard_database_connections > 15
        for: 5m
        annotations:
          summary: "Database connections high"

      - alert: HighRateLimitViolations
        expr: rate(agentguard_http_errors_total{status="429"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High rate limit violations"
```

### 4. Log Aggregation

#### Structured JSON Logging
All logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "agentguard",
  "message": "Enforcement check",
  "agent_id": "agt_abc123",
  "action": "read:file",
  "allowed": true,
  "request_id": "req_1234567890"
}
```

#### ELK Stack Configuration
```yaml
# Filebeat config
filebeat.inputs:
  - type: container
    paths:
      - '/var/lib/docker/containers/*/*.log'
    processors:
      - add_docker_metadata: ~
      - decode_json_fields:
          fields: ["message"]
          target: ""

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "agentguard-%{+yyyy.MM.dd}"
```

---

## 💾 Backup & Disaster Recovery

### 1. Database Backups

#### Automated Daily Backups
```bash
#!/bin/bash
# backup.sh

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="agentguard_backup_$TIMESTAMP.sql"

# Create backup
pg_dump -h $DB_HOST -U $DB_USER -d agentguard -F c -f /backups/$BACKUP_FILE

# Upload to S3
aws s3 cp /backups/$BACKUP_FILE s3://your-backup-bucket/agentguard/

# Clean up local backups older than 7 days
find /backups -name "agentguard_backup_*.sql" -mtime +7 -delete

# Clean up S3 backups older than 30 days
aws s3 ls s3://your-backup-bucket/agentguard/ | while read -r line; do
    createDate=$(echo $line | awk {'print $1" "$2'})
    createDate=$(date -d "$createDate" +%s)
    olderThan=$(date --date "30 days ago" +%s)
    if [[ $createDate -lt $olderThan ]]; then
        fileName=$(echo $line | awk {'print $4'})
        aws s3 rm s3://your-backup-bucket/agentguard/$fileName
    fi
done
```

#### Cron Schedule
```bash
# Run daily at 2 AM
0 2 * * * /scripts/backup.sh
```

### 2. Backup Restoration

```bash
# Restore from backup
pg_restore -h $DB_HOST -U $DB_USER -d agentguard -c /path/to/backup.sql

# Or from S3
aws s3 cp s3://your-backup-bucket/agentguard/backup.sql - | pg_restore -h $DB_HOST -U $DB_USER -d agentguard -c
```

### 3. Disaster Recovery Procedure

**RTO: 1 hour | RPO: 24 hours**

1. **Detect outage** (automated monitoring)
2. **Assess impact** (what's down?)
3. **Failover to backup region** (if multi-region setup)
4. **Restore from latest backup** (if database lost)
5. **Verify system integrity** (health checks)
6. **Notify stakeholders** (status page, Slack)
7. **Post-mortem** (document what happened)

---

## ⚡ Performance Tuning

### 1. Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_agents_active ON agents(is_active) WHERE is_active = true;
CREATE INDEX idx_audit_logs_agent_timestamp ON audit_logs(agent_id, timestamp DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_allowed ON audit_logs(allowed);

-- Analyze tables regularly
ANALYZE agents;
ANALYZE audit_logs;
ANALYZE policies;

-- Set autovacuum aggressively for high-write tables
ALTER TABLE audit_logs SET (autovacuum_vacuum_scale_factor = 0.05);
```

### 2. Connection Pooling

Use PgBouncer for connection pooling:

```ini
# pgbouncer.ini
[databases]
agentguard = host=db-host port=5432 dbname=agentguard

[pgbouncer]
listen_addr = *
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
reserve_pool_size = 5
reserve_pool_timeout = 3
```

### 3. Caching Strategy

For read-heavy workloads, add Redis caching:

```python
# Example: Cache agent policies
import redis
import json

redis_client = redis.Redis(host='redis', port=6379, db=0)

def get_policy_cached(agent_id: str):
    # Try cache first
    cached = redis_client.get(f"policy:{agent_id}")
    if cached:
        return json.loads(cached)

    # Fetch from DB
    policy = db.query(Policy).filter(Policy.agent_id == agent_id).first()

    # Cache for 5 minutes
    if policy:
        redis_client.setex(
            f"policy:{agent_id}",
            300,
            json.dumps(policy.to_dict())
        )

    return policy
```

---

## 🚢 Deployment Process

### 1. Pre-Deployment

```bash
# Run tests
cd backend
pytest

# Build Docker image
docker build -t agentguard/backend:v0.1.0 .
docker push agentguard/backend:v0.1.0

# Run database migrations
alembic upgrade head
```

### 2. Blue-Green Deployment

```bash
# Deploy new version (green)
kubectl apply -f k8s/deployment-green.yaml

# Wait for health checks
kubectl wait --for=condition=ready pod -l app=agentguard,version=green --timeout=300s

# Switch traffic to green
kubectl patch service agentguard -p '{"spec":{"selector":{"version":"green"}}}'

# Monitor for issues
kubectl logs -f -l app=agentguard,version=green

# If successful, remove blue deployment
kubectl delete deployment agentguard-blue
```

### 3. Rollback Procedure

```bash
# If issues detected, immediately rollback
kubectl patch service agentguard -p '{"spec":{"selector":{"version":"blue"}}}'

# Investigate green deployment issues
kubectl logs -l app=agentguard,version=green
kubectl describe pods -l app=agentguard,version=green
```

---

## ✔️ Post-Deployment Verification

### Automated Health Checks

```bash
# Basic health
curl https://api.yourdomain.com/health
# Expected: {"status": "healthy"}

# Readiness check
curl https://api.yourdomain.com/health/ready
# Expected: {"status": "ready", "checks": {...}}

# Metrics endpoint (from internal network)
curl https://api.yourdomain.com/metrics
# Expected: Prometheus metrics

# Test enforcement
curl -X POST https://api.yourdomain.com/enforce \
  -H "X-Agent-Key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"action": "read:file", "resource": "test.txt"}'
# Expected: {"allowed": true/false, "reason": "..."}
```

### Smoke Tests

```python
# smoke_tests.py
import requests

BASE_URL = "https://api.yourdomain.com"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_readiness():
    response = requests.get(f"{BASE_URL}/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

def test_enforcement():
    response = requests.post(
        f"{BASE_URL}/enforce",
        headers={"X-Agent-Key": AGENT_KEY},
        json={"action": "read:file", "resource": "test.txt"}
    )
    assert response.status_code == 200
    assert "allowed" in response.json()

if __name__ == "__main__":
    test_health()
    test_readiness()
    test_enforcement()
    print("✅ All smoke tests passed!")
```

---

## 🔧 Maintenance & Operations

### Daily
- [ ] Check error logs for anomalies
- [ ] Review Grafana dashboards
- [ ] Check backup success

### Weekly
- [ ] Review system metrics and trends
- [ ] Check database performance (slow queries)
- [ ] Review rate limit violations
- [ ] Test alerting system

### Monthly
- [ ] Review and rotate API keys (if policy requires)
- [ ] Update dependencies and security patches
- [ ] Review and archive old audit logs
- [ ] Capacity planning review
- [ ] DR drill (test backup restoration)

### Quarterly
- [ ] Security audit
- [ ] Performance optimization review
- [ ] Documentation update
- [ ] Disaster recovery full test

---

## 📞 Support & Escalation

### Severity Levels

**P0 - Critical (< 15 min response)**
- Complete service outage
- Data breach or security incident
- Database corruption

**P1 - High (< 1 hour response)**
- Partial service outage
- Significant performance degradation
- Authentication failures

**P2 - Medium (< 4 hours response)**
- Non-critical feature broken
- Minor performance issues
- Monitoring alerts

**P3 - Low (< 1 day response)**
- Feature requests
- Documentation issues
- Minor bugs

### On-Call Rotation

- Use PagerDuty for alerting
- 24/7 coverage required for production
- Escalation path: Engineer → Team Lead → VP Engineering

---

## 📚 Additional Resources

- [API Documentation](/docs)
- [Architecture Decision Records](./docs/adr/)
- [Runbook](./docs/runbook.md)
- [Security Policy](./SECURITY.md)
- [Contributing Guide](./CONTRIBUTING.md)

---

**Last Updated**: 2024-02-11
**Version**: 0.1.0
**Maintained By**: Engineering Team
