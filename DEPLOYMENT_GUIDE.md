# Elderly Care AI System - Security Hardening Deployment Guide

## Overview
This guide walks through deploying critical P0 and P1 security/performance fixes to the elderly care system. All code changes are backward compatible after schema migration.

## Prerequisites
- PostgreSQL 12+ running and accessible
- Python 3.9+
- PyJWT library installed: `pip install PyJWT`
- Home Assistant configured (if using webhook integration)
- Current deployment environment accessible

---

## Phase 1: Environment Setup (Pre-Deployment)

### 1.1 Generate Secure Keys

**Generate SECRET_KEY for JWT signing:**
```bash
python3 -c "import secrets; import base64; key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(); print(f'SECRET_KEY={key}')"
```
Output example:
```
SECRET_KEY=xK8mN9pQ2rR5sT6uV7wX8yZ9aBcDeFgHiJkLmNoPqRs=
```

**Generate API_KEY (for legacy clients if needed):**
```bash
python3 -c "import secrets; import base64; key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(); print(f'API_KEY={key}')"
```

### 1.2 Configure Environment Variables

Edit `.env` file and **replace** these values:

```bash
# Security Secrets (MANDATORY - no defaults allowed)
SECRET_KEY=<paste_generated_SECRET_KEY_here>
API_KEY=<paste_generated_API_KEY_here>

# CORS Configuration (Whitelist, NOT wildcard)
ALLOW_ORIGINS=["http://frontend-domain.com", "https://frontend-domain.com", "http://localhost:3000"]

# Home Assistant Webhook Security (if using HA integration)
HOME_ASSISTANT_WEBHOOK_SECRET=<generate_another_secure_random_32_char_string>
```

**Generate Home Assistant webhook secret:**
```bash
python3 -c "import secrets; secret = secrets.token_hex(32); print(f'HOME_ASSISTANT_WEBHOOK_SECRET={secret}')"
```

### 1.3 Verify No Hardcoded Secrets

Search codebase for any remaining hardcoded values:
```bash
grep -r "change_me_in_production" app/
grep -r "your_" app/
# Should return 0 results
```

---

## Phase 2: Database Migration

### 2.1 Backup Database

**Critical: Always backup before migration**
```bash
# PostgreSQL backup
pg_dump -U elderly_admin -h postgres -d elderly_care > elderly_care_backup_$(date +%Y%m%d_%H%M%S).sql

# Docker container backup
docker exec elderly-care-postgres pg_dump -U elderly_admin elderly_care > backup_$(date +%Y%m%d).sql
```

### 2.2 Apply Migration

**Option A: Direct SQL execution**
```bash
# From container
docker exec elderly-care-postgres psql -U elderly_admin -d elderly_care -f /migrations/001_security_hardening.sql

# Or locally
psql -U elderly_admin -h localhost -d elderly_care < migrations/001_security_hardening.sql
```

**Option B: Python Alembic (if configured)**
```bash
alembic upgrade head
```

### 2.3 Verify Migration Success

```sql
-- Verify multi-tenancy constraints
\d elders
-- Should show: "uq_family_elder" UNIQUE CONSTRAINT (family_id, elder_id)

\d devices
-- Should show: "uq_family_device" UNIQUE CONSTRAINT (family_id, device_id)

-- Verify indexes created
\d alerts
-- Should list: idx_alert_dedup, idx_alert_unacked

-- Test: Verify can't insert duplicate elder in same family
INSERT INTO families VALUES (1, 'test_family_1', 'Test', 'Desc', now(), now());
INSERT INTO elders VALUES (1, 'elderly_1', 'test_family_1', 'John', 80, 'M', '{}', 'collecting', 0, null, now(), now());
INSERT INTO elders VALUES (2, 'elderly_1', 'test_family_1', 'Jane', 75, 'F', '{}', 'collecting', 0, null, now(), now());
-- Should fail with: duplicate key value violates unique constraint "uq_family_elder"
```

---

## Phase 3: Code Deployment

### 3.1 Install Dependencies

```bash
# Add PyJWT if not already installed
pip install PyJWT>=2.8.0

# Update requirements.txt
echo "PyJWT>=2.8.0" >> requirements.txt
```

### 3.2 Deploy Updated Code

Replace these files in your deployment:
- `app/config.py` (CORS whitelist, enforced env vars)
- `app/security.py` (NEW - JWT authentication)
- `app/main.py` (PII filtering, webhook signature verification)
- `app/models.py` (composite constraints)
- `app/rules.py` (N+1 query optimization)
- `app/routes/events.py` (JWT verification)
- `app/routes/alerts.py` (JWT verification)

### 3.3 Restart Application

```bash
# Docker container
docker restart elderly-care-api

# Or uvicorn
pkill -f uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Verify startup
docker logs elderly-care-api | grep "✅ Elderly Care Cloud API started"
```

---

## Phase 4: JWT Token Generation & Testing

### 4.1 Obtain Initial JWT Token

Create a temporary token generation script:

```python
# generate_token.py
from app.security import create_access_token
from datetime import timedelta

# Generate token for a family
family_id = "family_001"
device_id = "device_001"
expires_in = timedelta(hours=24)

token = create_access_token(
    family_id=family_id,
    device_id=device_id,
    expires_delta=expires_in
)

print(f"JWT Token: {token}")
print(f"Use in header: Authorization: Bearer {token}")
```

```bash
python generate_token.py
```

### 4.2 Test API Endpoints with JWT

**Query alerts (with JWT):**
```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:8000/api/alerts?family_id=family_001&days=7" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected response (200 OK):**
```json
{
  "total": 5,
  "alerts": [
    {
      "alert_id": "uuid...",
      "elder_id": "elderly_001",
      "alert_type": "inactivity",
      "alert_level": "critical",
      "message": "No activity for 240 minutes",
      "created_at": "2026-04-27T10:30:00"
    }
  ]
}
```

**Test without JWT (should fail 401):**
```bash
curl -X GET "http://localhost:8000/api/alerts?family_id=family_001"
# Expected: 401 Unauthorized
```

### 4.3 Test Home Assistant Webhook Signature Verification

If using Home Assistant integration, test webhook signature:

```python
# test_webhook.py
import hashlib
import hmac
import json
import requests

webhook_secret = "your_HOME_ASSISTANT_WEBHOOK_SECRET"
webhook_url = "http://localhost:8000/webhook/home_assistant"

# Payload
payload = {
    "elder_id": "elderly_001",
    "family_id": "family_001",
    "event_type": "motion",
    "room": "bedroom"
}

body = json.dumps(payload).encode()

# Compute signature
signature = "sha256=" + hmac.new(
    webhook_secret.encode(),
    body,
    hashlib.sha256
).hexdigest()

# Send request
response = requests.post(
    webhook_url,
    json=payload,
    headers={"X-HA-Webhook-Signature": signature}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
# Expected: 200 {"status": "success", ...}

# Test invalid signature (should fail 401)
response = requests.post(
    webhook_url,
    json=payload,
    headers={"X-HA-Webhook-Signature": "sha256=invalid"}
)
# Expected: 401 Unauthorized
```

---

## Phase 5: CORS Configuration

### 5.1 Update ALLOW_ORIGINS for Production

In `.env`:
```bash
# Development
ALLOW_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Production - use actual domain names
ALLOW_ORIGINS=["https://app.elderly-care.com", "https://dashboard.elderly-care.com"]
```

### 5.2 Verify CORS Works

```bash
# From allowed origin
curl -X OPTIONS http://localhost:8000/api/alerts \
  -H "Origin: http://localhost:3000" \
  -v
# Should see: access-control-allow-origin: http://localhost:3000

# From disallowed origin
curl -X OPTIONS http://localhost:8000/api/alerts \
  -H "Origin: http://attacker.com" \
  -v
# Should NOT see CORS headers
```

---

## Phase 6: Logging & Monitoring

### 6.1 Verify PII Filtering Active

Check logs don't contain sensitive data:
```bash
docker logs elderly-care-api | grep -E "(EMAIL_MASKED|IP_MASKED|PHONE_MASKED)"
# Should find masked entries, not raw PII

docker logs elderly-care-api | grep -E "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
# Should return 0 results (IPs are masked)
```

### 6.2 Monitor Error Logging

Errors should NOT contain stack traces:
```bash
docker logs elderly-care-api | grep "INTERNAL_ERROR"
# Should see: error_id, error_code but NOT detailed traceback
```

---

## Phase 7: Performance Verification

### 7.1 Verify N+1 Query Fix

Monitor query count for room pattern detection:

```python
# Before fix: ~50ms with 1000+ queries
# After fix: ~5ms with 1-2 queries

# In Sentry or APM tool, check transaction:
# "check_room_pattern_change" should show single database query
```

### 7.2 Index Usage Validation

```sql
-- Check if indexes are actually being used
EXPLAIN ANALYZE 
SELECT * FROM alerts 
WHERE family_id = 'family_001' AND is_acknowledged = false 
ORDER BY created_at DESC;

-- Should see: "Index Scan using idx_alert_unacked"
```

---

## Phase 8: Client Migration (If Applicable)

### 8.1 Update Client Code

Old (API Key):
```javascript
headers: {
  'X-API-Key': 'your_api_key'
}
```

New (JWT):
```javascript
headers: {
  'Authorization': `Bearer ${jwtToken}`
}
```

### 8.2 Token Refresh Strategy

Tokens expire after 24 hours by default. Implement refresh:

```python
# In app/security.py, add refresh_token endpoint
@app.post("/api/auth/refresh")
def refresh_token(current_token: TokenPayload = Depends(verify_token)):
    new_token = create_access_token(
        family_id=current_token.family_id,
        device_id=current_token.device_id
    )
    return {"access_token": new_token, "token_type": "bearer"}
```

---

## Rollback Plan (If Needed)

### Rollback Database
```bash
# Restore from backup
psql -U elderly_admin -d elderly_care < elderly_care_backup_YYYYMMDD_HHMMSS.sql
```

### Rollback Code
```bash
# Revert to previous Docker image
docker run -d --name elderly-care-api \
  -e DATABASE_URL=postgresql+psycopg2://elderly_admin:$PG_PASSWORD@postgres:5432/elderly_care \
  elderly-care-api:v1.0
```

---

## Verification Checklist

- [ ] Environment variables set (SECRET_KEY, API_KEY, ALLOW_ORIGINS)
- [ ] Database backup created
- [ ] Migration script executed successfully
- [ ] Multi-tenancy constraints verified
- [ ] Alert indexes created
- [ ] Code deployed to all instances
- [ ] Application restarted successfully
- [ ] JWT token generation tested
- [ ] API endpoints respond with JWT
- [ ] Requests without JWT return 401
- [ ] CORS allows configured origins only
- [ ] CORS rejects disallowed origins
- [ ] Logs contain no raw PII/IPs/emails
- [ ] Error responses don't expose stack traces
- [ ] Home Assistant webhook signature verification works
- [ ] Room pattern detection performance improved
- [ ] No 'change_me_in_production' values remain in code

---

## Troubleshooting

### Token Verification Fails
```
Error: "Invalid token" or "Token expired"
```
**Solution:**
- Verify SECRET_KEY matches in config
- Check token not expired: `token.exp < now()`
- Ensure JWT library version >= 2.8.0

### CORS Errors
```
Error: "Access to XMLHttpRequest blocked by CORS policy"
```
**Solution:**
- Check ALLOW_ORIGINS contains your frontend domain
- Verify using HTTPS in production (change http to https)
- Restart API after changing ALLOW_ORIGINS

### Migration Fails on Constraint
```
Error: "duplicate key value violates unique constraint"
```
**Solution:**
- Existing data has duplicates across families
- Run data cleanup: `SELECT family_id, elder_id, COUNT(*) FROM elders GROUP BY family_id, elder_id HAVING COUNT(*) > 1`
- Remove duplicates before re-running migration

### Webhook Returns 401
```
Error: "Invalid signature"
```
**Solution:**
- Verify HOME_ASSISTANT_WEBHOOK_SECRET matches in both .env and HA config
- Ensure Home Assistant is computing: `sha256(SECRET + body)`
- Check request body encoding (must be exact JSON)

---

## Security Checklist

- [ ] All environment variables enforced (no defaults)
- [ ] CORS using whitelist, not wildcard
- [ ] HMAC-SHA256 signature verification on webhooks
- [ ] JWT tokens required for all API endpoints
- [ ] No stack traces in error responses
- [ ] PII filtered from all logs
- [ ] Database uses composite unique constraints
- [ ] Row-level locking prevents alert race conditions
- [ ] Database backups encrypted and stored securely

---

## Support & Questions

For issues during deployment:
1. Check logs: `docker logs elderly-care-api`
2. Verify all environment variables set
3. Confirm database migration succeeded
4. Test endpoints with curl before frontend integration
5. Review error_id from error responses in application logs

---

**Deployment Date:** 2026-04-27  
**Security Level:** Critical P0/P1 Fixes  
**Estimated Downtime:** 5-10 minutes (database migration only)
