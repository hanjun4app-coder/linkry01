# Elderly Care API - JWT Authentication Integration Guide

## Overview

The API now uses **JWT (JSON Web Token)** authentication instead of API keys. This provides stronger security, expiration controls, and per-family isolation.

**Base URL:** `http://api.elderly-care.com` (or `http://localhost:8000` for development)

---

## Authentication

### Obtaining a JWT Token

**Endpoint:** `POST /api/auth/token` (to be implemented)

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "family_id": "family_001",
    "device_id": "mobile_app_001"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

### Using JWT in Requests

Add token to the `Authorization` header:

```bash
curl -X GET http://localhost:8000/api/alerts \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Expiration

- Default expiration: **24 hours**
- When expired, all requests return **401 Unauthorized**
- Client must re-authenticate to obtain a new token

```json
{
  "detail": "Token expired"
}
```

---

## API Endpoints

### 1. Query Alerts

**Endpoint:** `GET /api/alerts`

**Authentication:** Required (JWT)

**Query Parameters:**
- `family_id` (optional): Filter by family. If not provided, uses family from token
- `elder_id` (optional): Filter by specific elder
- `alert_type` (optional): `inactivity`, `bathroom_timeout`, `abnormal_wake`, `night_activity`, `room_pattern_change`
- `alert_level` (optional): `info`, `warning`, `critical`
- `is_acknowledged` (optional): `true` or `false`
- `days` (optional): Number of days to look back (1-90, default 7)
- `limit` (optional): Max results (1-1000, default 100)
- `offset` (optional): Pagination offset (default 0)

**Example:**
```bash
curl -X GET "http://localhost:8000/api/alerts?family_id=family_001&alert_level=critical&days=7&limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**
```json
{
  "total": 5,
  "alerts": [
    {
      "alert_id": "550e8400-e29b-41d4-a716-446655440000",
      "elder_id": "elderly_001",
      "family_id": "family_001",
      "alert_type": "inactivity",
      "alert_level": "critical",
      "message": "长时间无活动：240 分钟无活动记录",
      "details": {
        "threshold_minutes": 240,
        "minutes_without_activity": 245.5,
        "last_activity_time": "2026-04-27T08:30:00",
        "last_activity_location": "bedroom"
      },
      "is_acknowledged": false,
      "created_at": "2026-04-27T12:35:00"
    }
  ],
  "timestamp": "2026-04-27T12:36:00"
}
```

**Error Responses:**

401 Unauthorized (missing/invalid token):
```json
{
  "detail": "Not authenticated"
}
```

403 Forbidden (token not authorized for family):
```json
{
  "detail": "Token not authorized for this family"
}
```

---

### 2. Get Unacknowledged Alerts

**Endpoint:** `GET /api/alerts/unacknowledged`

**Authentication:** Required (JWT)

**Query Parameters:**
- `elder_id` (optional): Filter by specific elder
- `family_id` (optional): Filter by family

**Example:**
```bash
curl -X GET "http://localhost:8000/api/alerts/unacknowledged?family_id=family_001" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**
```json
[
  {
    "alert_id": "550e8400-e29b-41d4-a716-446655440000",
    "alert_type": "inactivity",
    "alert_level": "critical",
    "message": "长时间无活动：240 分钟无活动记录",
    "created_at": "2026-04-27T12:35:00"
  },
  {
    "alert_id": "660e8400-e29b-41d4-a716-446655440001",
    "alert_type": "night_activity",
    "alert_level": "warning",
    "message": "夜间频繁活动：检测到 8 次活动（阈值 5）",
    "created_at": "2026-04-27T03:15:00"
  }
]
```

---

### 3. Acknowledge Alert

**Endpoint:** `POST /api/alerts/{alert_id}/acknowledge`

**Authentication:** Required (JWT)

**Query Parameters:**
- `acknowledged_by` (required): User ID of person acknowledging

**Example:**
```bash
curl -X POST "http://localhost:8000/api/alerts/123/acknowledge?acknowledged_by=user_001" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
{
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_acknowledged": true,
  "acknowledged_at": "2026-04-27T13:00:00",
  "acknowledged_by": "user_001"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Alert not found"
}
```

---

### 4. Get Alert Statistics

**Endpoint:** `GET /api/alerts/{family_id}/statistics`

**Authentication:** Required (JWT)

**Query Parameters:**
- `days` (optional): Number of days to analyze (1-90, default 7)

**Example:**
```bash
curl -X GET "http://localhost:8000/api/alerts/family_001/statistics?days=30" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**
```json
{
  "family_id": "family_001",
  "time_range_days": 30,
  "total_alerts": 42,
  "unacknowledged": 5,
  "acknowledged": 37,
  "by_type": {
    "inactivity": 15,
    "bathroom_timeout": 10,
    "abnormal_wake": 8,
    "night_activity": 6,
    "room_pattern_change": 3
  },
  "by_level": {
    "critical": 5,
    "warning": 20,
    "info": 17
  },
  "timestamp": "2026-04-27T13:05:00"
}
```

---

### 5. Get Elder's Unacknowledged Count

**Endpoint:** `GET /api/alerts/elder/{elder_id}/unacknowledged-count`

**Authentication:** Required (JWT)

**Query Parameters:**
- `family_id` (required): Family ID

**Example:**
```bash
curl -X GET "http://localhost:8000/api/alerts/elder/elderly_001/unacknowledged-count?family_id=family_001" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**
```json
{
  "elder_id": "elderly_001",
  "family_id": "family_001",
  "total_unacknowledged": 3,
  "critical": 1,
  "warning": 2,
  "info": 0,
  "timestamp": "2026-04-27T13:06:00"
}
```

---

### 6. Create Event

**Endpoint:** `POST /api/events`

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "elder_id": "elderly_001",
  "family_id": "family_001",
  "device_id": "aqara_fp2_001",
  "device_type": "aqara_fp2",
  "event_type": "motion",
  "event_value": {
    "distance": 2.5,
    "presence": true
  },
  "room": "bedroom",
  "location_name": "bedroom_window",
  "confidence": 0.95,
  "timestamp": "2026-04-27T12:30:00"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "elder_id": "elderly_001",
    "family_id": "family_001",
    "device_id": "aqara_fp2_001",
    "device_type": "aqara_fp2",
    "event_type": "motion",
    "event_value": {"distance": 2.5},
    "room": "bedroom",
    "timestamp": "2026-04-27T12:30:00"
  }'
```

**Response (201 Created):**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "family_id": "family_001",
  "elder_id": "elderly_001",
  "device_id": "aqara_fp2_001",
  "event_type": "motion",
  "room": "bedroom",
  "timestamp": "2026-04-27T12:30:00",
  "created_at": "2026-04-27T12:31:00"
}
```

---

## Error Handling

### Standard Error Response Format

All errors follow this format:

```json
{
  "success": false,
  "error_code": "ERROR_TYPE",
  "error_message": "Human-readable error message",
  "error_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-04-27T13:00:00"
}
```

### Common Error Codes

| HTTP Status | Error Code | Meaning |
|-------------|-----------|---------|
| 400 | INVALID_PARAMETER | Invalid query parameter or request body |
| 401 | UNAUTHORIZED | Missing or invalid JWT token |
| 403 | FORBIDDEN | Token not authorized for requested family/resource |
| 404 | NOT_FOUND | Resource not found (alert, event, etc.) |
| 500 | INTERNAL_ERROR | Server error (use error_id for support) |

### PII Protection

The API **never logs personally identifiable information**. If you see an error, the error message is generic and safe to log on the client side. Use the `error_id` to report issues to support.

```bash
Error response:
{
  "error_code": "INTERNAL_ERROR",
  "error_message": "Internal server error",
  "error_id": "550e8400-e29b-41d4-a716-446655440000"
}

# Support team uses error_id to look up detailed server logs
```

---

## Integration Examples

### JavaScript/TypeScript (Frontend)

```typescript
const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
const API_BASE = 'http://localhost:8000';

// Fetch unacknowledged alerts
async function getUnacknowledgedAlerts(familyId: string) {
  const response = await fetch(
    `${API_BASE}/api/alerts/unacknowledged?family_id=${familyId}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${TOKEN}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (response.status === 401) {
    // Token expired, redirect to login
    window.location.href = '/login';
    return;
  }

  const alerts = await response.json();
  return alerts;
}

// Acknowledge an alert
async function acknowledgeAlert(alertId: string, userId: string) {
  const response = await fetch(
    `${API_BASE}/api/alerts/${alertId}/acknowledge?acknowledged_by=${userId}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${TOKEN}`,
        'Content-Type': 'application/json'
      }
    }
  );

  return await response.json();
}
```

### Python (Backend/Integration)

```python
import requests
import json
from datetime import datetime, timedelta

TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
API_BASE = 'http://localhost:8000'

# Get critical alerts for a family
def get_critical_alerts(family_id, days=7):
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        f'{API_BASE}/api/alerts',
        params={
            'family_id': family_id,
            'alert_level': 'critical',
            'days': days
        },
        headers=headers
    )
    
    if response.status_code == 401:
        raise Exception('Token expired, need re-authentication')
    
    response.raise_for_status()
    return response.json()

# Report an event
def report_event(elder_id, family_id, event_type, room):
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'elder_id': elder_id,
        'family_id': family_id,
        'device_id': 'python_client_001',
        'device_type': 'custom',
        'event_type': event_type,
        'room': room,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    response = requests.post(
        f'{API_BASE}/api/events',
        json=payload,
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()
```

### cURL Examples

```bash
# Set token as environment variable
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
FAMILY_ID="family_001"

# Get critical alerts from last 30 days
curl -X GET "http://localhost:8000/api/alerts?family_id=$FAMILY_ID&alert_level=critical&days=30" \
  -H "Authorization: Bearer $TOKEN"

# Get alert statistics
curl -X GET "http://localhost:8000/api/alerts/$FAMILY_ID/statistics?days=30" \
  -H "Authorization: Bearer $TOKEN"

# Acknowledge an alert
curl -X POST "http://localhost:8000/api/alerts/123/acknowledge?acknowledged_by=admin_user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Create a motion event
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "elder_id": "elderly_001",
    "family_id": "family_001",
    "device_id": "motion_sensor_001",
    "device_type": "aqara_fp2",
    "event_type": "motion",
    "room": "living_room",
    "timestamp": "2026-04-27T14:30:00"
  }'
```

---

## Health & Status Endpoints

These endpoints don't require authentication:

### API Status
```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "name": "Elderly Care Cloud API",
  "version": "2.0.0",
  "endpoints": {
    "events": "/api/events",
    "alerts": "/api/alerts",
    "patterns": "/api/patterns"
  }
}
```

### Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok"
}
```

### Version Info
```bash
curl http://localhost:8000/version
```

**Response:**
```json
{
  "version": "2.0.0",
  "environment": "production"
}
```

---

## Rate Limiting & Pagination

### Pagination

Use `limit` and `offset` for large result sets:

```bash
# Get first 50 alerts
curl "http://localhost:8000/api/alerts?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Get next 50 alerts
curl "http://localhost:8000/api/alerts?limit=50&offset=50" \
  -H "Authorization: Bearer $TOKEN"
```

### Best Practices

1. **Always use JWT for all requests** - API key authentication is deprecated
2. **Handle 401 responses** - Token may expire; re-authenticate when needed
3. **Validate response timestamps** - Verify server time sync with client
4. **Paginate large queries** - Don't request all alerts at once; use limit/offset
5. **Log error_id for support** - Never log full error details (may contain PII)
6. **Retry with backoff** - On 5xx errors, implement exponential backoff

---

## Support

- **Documentation:** Full API docs available at `/docs` endpoint
- **Issues:** Use error_id from error responses for support tickets
- **Security:** Report vulnerabilities via security team (not GitHub issues)
- **Rate Limiting:** No hard limits, but please use pagination for large queries

---

**Last Updated:** 2026-04-27  
**API Version:** 2.0.0  
**Authentication Method:** JWT (Bearer Token)
