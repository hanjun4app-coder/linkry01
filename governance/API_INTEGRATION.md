# API Integration Guide

This document describes how to connect the SafeHome frontend to the backend API.

## Backend Endpoints Required

### 1. Customer Creation (Intake Form Submission)

**Endpoint**: `POST /api/customers`

This endpoint is called when a customer completes the 4-step onboarding form.

**Request Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "elder": {
    "name": "string",
    "age": "number",
    "lives_alone": "boolean",
    "mobility_level": "string (independent|assisted|limited)"
  },
  "family": {
    "email": "string",
    "phone": "string",
    "address": "string"
  },
  "baseline": {
    "wake_up_time": "string (HH:MM)",
    "sleep_time": "string (HH:MM)",
    "shower_time": "string (HH:MM)",
    "bathroom_duration_minutes": "number",
    "night_bathroom_frequency": "number"
  },
  "installation": {
    "preferred_date": "string (YYYY-MM-DD)",
    "preferred_time_window": "string (morning|afternoon|evening)",
    "notes": "string (optional)"
  }
}
```

**Expected Response** (200):
```json
{
  "customer_id": "string",
  "elder_id": "string",
  "family_id": "string",
  "installation_profile_id": "string",
  "message": "Your request has been received"
}
```

**Error Response** (400/422):
```json
{
  "detail": "Invalid email address"
}
```

**Backend Logic**:
- Create customer_profile record
- Create elder_profile record with age, mobility_level
- Create installation_profile with status="pending"
- Create family_reported_baseline with:
  - source = "family_reported"
  - confidence = 0.25
  - learning_phase = true
  - learning_days = 14
- Send confirmation email
- Return IDs for UI redirect

---

### 2. Authentication - Login

**Endpoint**: `POST /api/auth/login`

Standard email/password login for both families and installers.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response** (200):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "string",
  "family_id": "string",
  "role": "family|admin",
  "name": "string"
}
```

**Error** (401):
```json
{
  "detail": "Invalid email or password"
}
```

**Backend Logic**:
- Hash password with bcrypt
- Return JWT token (valid for 24 hours)
- Token should include user_id, family_id, role in payload

---

### 3. Authentication - Forgot Password

**Endpoint**: `POST /api/auth/forgot-password`

**Request**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200):
```json
{
  "message": "Password reset link sent to email"
}
```

**Backend Logic**:
- Generate temporary reset token (valid 1 hour)
- Send email with reset link: `/reset-password?token={token}`
- Do NOT expose token in response

---

### 4. Family Dashboard Data

**Endpoint**: `GET /api/family/dashboard`

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Response** (200):
```json
{
  "family_name": "string",
  "elder_name": "string",
  "status": {
    "is_ok": "boolean",
    "last_activity": "string (human-readable, e.g., '2 minutes ago')",
    "message": "string"
  },
  "recent_alerts": [
    {
      "id": "string",
      "title": "string (user-friendly)",
      "message": "string (3-part: observation + background + action)",
      "level": "string (critical|warning|info)",
      "time": "string (human-readable, e.g., '1 hour ago')",
      "acknowledged": "boolean"
    }
  ]
}
```

**Status Logic**:
- `is_ok = true` if no critical/warning alerts in last 24h
- `last_activity` = human-readable time of last sensor activity
- Include up to 10 most recent alerts

**Alert Message Format** (IMPORTANT):
```
Observation: "We noticed..."
Background: "This is important because..."
Action: "You should..." or "Please..."

Example: "We noticed your mom has been in the bathroom for longer than usual. This is important because extended bathroom visits can indicate a fall. Please check on her."
```

---

### 5. Admin - Get Installations

**Endpoint**: `GET /api/admin/installations?status={status}`

Query Parameters:
- `status`: pending | scheduled | completed

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response** (200):
```json
{
  "installations": [
    {
      "id": "string",
      "elder_name": "string",
      "family_name": "string",
      "family_email": "string",
      "family_phone": "string",
      "address": "string",
      "preferred_date": "string (YYYY-MM-DD)",
      "preferred_time_window": "string (morning|afternoon|evening)",
      "installation_notes": "string",
      "status": "string (pending|scheduled|completed)",
      "created_at": "string (ISO 8601)",
      "confirmed_at": "string (ISO 8601, nullable)"
    }
  ]
}
```

---

### 6. Admin - Confirm Installation

**Endpoint**: `POST /api/admin/installations/{id}/confirm`

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request** (optional):
```json
{
  "scheduled_date": "2026-05-15",
  "scheduled_time": "10:00",
  "notes": "string"
}
```

**Response** (200):
```json
{
  "id": "string",
  "status": "scheduled",
  "message": "Installation confirmed. Customer will be notified."
}
```

**Backend Logic**:
- Update installation_profile status to "scheduled"
- Send email to family confirming appointment
- Include pre-installation checklist (WiFi, power, access, someone home)

---

### 7. Admin - Complete Installation

**Endpoint**: `POST /api/admin/installations/{id}/complete`

Called when installer finishes on-site setup.

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request**:
```json
{
  "device_serial_numbers": ["DEV001", "DEV002"],
  "baseline_confirmed": true,
  "baseline_adjustments": {
    "wake_up_time": "07:30",
    "sleep_time": "22:30"
  },
  "notes": "string"
}
```

**Response** (200):
```json
{
  "status": "completed",
  "family_account_created": true,
  "message": "Installation complete. Family account created."
}
```

**Backend Logic**:
- Update installation_profile status to "completed"
- Update baseline with installer's adjustments
- Create family account with temporary password
- Send family password setup email with link to `/login`
- Email should include:
  - Login instructions
  - How to access dashboard
  - First alert explanation
- Enable monitoring service once account is activated

---

## Frontend Implementation Notes

### Storing Auth Token

```javascript
// After login
const response = await fetch('/api/auth/login', {...})
const data = await response.json()
localStorage.setItem('token', data.token)

// In subsequent requests
const token = localStorage.getItem('token')
const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

### Error Handling

```javascript
const response = await fetch(endpoint, {headers})

if (response.status === 401) {
  // Token expired or invalid, redirect to login
  localStorage.removeItem('token')
  router.push('/login')
} else if (!response.ok) {
  const error = await response.json()
  // Show error message
}
```

### Environment Variable Setup

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### API Calls Pattern

```javascript
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const response = await fetch(`${apiUrl}/api/customers`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(formData)
})
```

---

## Security Considerations

1. **HTTPS Only**: Ensure API is HTTPS in production
2. **CORS**: Configure backend to allow frontend domain
3. **Token Expiry**: JWT tokens should expire after 24 hours
4. **Password Reset**: Reset links valid for 1 hour only
5. **Rate Limiting**: Implement on login and password reset endpoints
6. **Input Validation**: Both frontend and backend must validate

---

## Testing the Integration

### 1. Test Intake Form

```bash
curl -X POST http://localhost:8000/api/customers \
  -H "Content-Type: application/json" \
  -d '{
    "elder": {"name": "Test", "age": 75, "lives_alone": true, "mobility_level": "independent"},
    "family": {"email": "test@example.com", "phone": "555-0000", "address": "123 Main"},
    "baseline": {"wake_up_time": "07:00", "sleep_time": "22:00", "shower_time": "08:00", "bathroom_duration_minutes": 15, "night_bathroom_frequency": 1},
    "installation": {"preferred_date": "2026-05-15", "preferred_time_window": "morning", "notes": ""}
  }'
```

### 2. Test Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

### 3. Test Dashboard

```bash
curl -X GET http://localhost:8000/api/family/dashboard \
  -H "Authorization: Bearer {token}"
```

---

## Migration from Placeholder to Real Backend

1. Replace `NEXT_PUBLIC_API_URL` environment variable
2. Test all endpoints with curl first
3. Update error messages in frontend based on actual API responses
4. Add token refresh logic if needed
5. Monitor CORS issues in browser console
