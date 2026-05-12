# SafeHome Customer Onboarding Frontend

A clean, trustworthy, mobile-first Next.js application for elderly care monitoring system onboarding and family dashboard.

## Features

- **Landing Page** - Hero section with trust-building messaging, no technical language
- **4-Step Intake Form** - Collects elder information, daily routine, family contact, installation preferences
- **Confirmation Page** - Reassuring next steps and pre-installation checklist
- **Login Page** - Simple email/password authentication with password recovery
- **Family Dashboard** - Status overview, recent alerts, account settings
- **Admin/Installer Page** - Installation request management and scheduling

## Design Philosophy

✓ **Clean & Warm** - Apple/Calm/Healthcare style, lots of whitespace
✓ **No Technical Terms** - No risk_score, motion_level, device_id, anomaly
✓ **Mobile-First** - Responsive design for phone, tablet, desktop
✓ **Trust-Focused** - Clear explanations, no surveillance language, privacy emphasized
✓ **Simple** - MVP scope, no complex features

## Setup

### Prerequisites
- Node.js 14+ and npm

### Installation

```bash
npm install
```

### Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
next-frontend/
├── pages/
│   ├── _app.js              # Global layout and styling
│   ├── index.js             # Landing page
│   ├── onboarding.js        # 4-step intake form
│   ├── onboarding/
│   │   └── done.js          # Confirmation page
│   ├── login.js             # Family/admin login
│   ├── dashboard.js         # Family dashboard
│   └── admin.js             # Installer/admin panel
├── components/
│   ├── Layout.js            # Shared header/footer
│   ├── Button.js            # Reusable button
│   ├── Card.js              # Card component
│   ├── Input.js             # Form input
│   └── Select.js            # Dropdown select
├── styles/
│   └── globals.css          # Global styling
└── public/                  # Static files
```

## Routes

| Route | Purpose | Who |
|-------|---------|-----|
| `/` | Landing page | Public |
| `/onboarding` | Intake form | New customers |
| `/onboarding/done` | Confirmation + checklist | New customers |
| `/login` | Sign in | Existing families, installers |
| `/dashboard` | Family status view | Families |
| `/admin` | Installation management | Installers/admins |

## API Integration Points

### Intake Form Submission
**POST /api/customers**

```json
{
  "elder": {
    "name": "Mom",
    "age": 75,
    "lives_alone": true,
    "mobility_level": "independent"
  },
  "family": {
    "email": "you@example.com",
    "phone": "(555) 123-4567",
    "address": "123 Main St"
  },
  "baseline": {
    "wake_up_time": "07:00",
    "sleep_time": "22:00",
    "shower_time": "08:00",
    "bathroom_duration_minutes": 15,
    "night_bathroom_frequency": 1
  },
  "installation": {
    "preferred_date": "2026-05-15",
    "preferred_time_window": "morning",
    "notes": "Please use back entrance"
  }
}
```

**Response:**
```json
{
  "customer_id": "cust_123",
  "elder_id": "elder_456",
  "family_id": "fam_789",
  "installation_profile_id": "inst_012",
  "message": "Your request has been received"
}
```

### Login
**POST /api/auth/login**

```json
{
  "email": "you@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "token": "eyJhbGc...",
  "role": "family",
  "family_id": "fam_789"
}
```

### Get Dashboard Data
**GET /api/family/dashboard**

Headers:
```
Authorization: Bearer {token}
```

**Response:**
```json
{
  "family_name": "Smith Family",
  "elder_name": "Mom",
  "status": {
    "is_ok": true,
    "last_activity": "2 minutes ago in living room",
    "message": "Everything looks good"
  },
  "recent_alerts": [
    {
      "id": "alert_123",
      "title": "Extended bathroom visit",
      "message": "Mom has been in the bathroom longer than usual. Just checking in?",
      "level": "warning",
      "time": "1 hour ago"
    }
  ]
}
```

### Get Installations (Admin)
**GET /api/admin/installations?status=pending**

Headers:
```
Authorization: Bearer {token}
```

**Response:**
```json
{
  "installations": [
    {
      "id": "inst_123",
      "elder_name": "Mom",
      "family_name": "Smith",
      "family_email": "you@example.com",
      "family_phone": "(555) 123-4567",
      "address": "123 Main St",
      "preferred_date": "2026-05-15",
      "preferred_time_window": "morning",
      "installation_notes": "Please use back entrance"
    }
  ]
}
```

### Confirm Installation (Admin)
**POST /api/admin/installations/{id}/confirm**

Headers:
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Response:**
```json
{
  "status": "confirmed",
  "message": "Installation confirmed. Customer will be notified."
}
```

### Complete Installation (Admin)
**POST /api/admin/installations/{id}/complete**

Headers:
```
Authorization: Bearer {token}
Content-Type: application/json
```

Creates family account and sends password setup email.

**Response:**
```json
{
  "status": "completed",
  "family_account_created": true,
  "password_reset_email_sent": true
}
```

## Environment Variables

Create a `.env.local` file:

```env
# API Base URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Feature flags
NEXT_PUBLIC_PILOT_MODE=true
```

## Authentication Flow

1. **Onboarding**: No authentication needed
   - Customer fills intake form
   - System creates profiles (customer, elder, baseline)
   - Admin reviews and confirms

2. **Post-Installation**: Account creation
   - Installer marks installation complete
   - System creates family account
   - Password reset email sent
   - Family logs in with email/password

3. **Ongoing Access**:
   - Family uses email/password to access dashboard
   - Installer uses admin credentials to manage installations

## Styling

- **No build-time CSS compilation** - Uses plain CSS with simple utility classes
- **Responsive Design** - Mobile-first, works on all screen sizes
- **Color Scheme**:
  - Blue (#2563eb) for primary actions and trust
  - Gray (#1f2937, #4b5563) for text and neutral elements
  - Red for errors, Yellow for warnings, Green for success

## Deployment Options

### Vercel (Recommended)
```bash
# Connect GitHub repo and deploy via Vercel dashboard
# Environment variables set in Vercel dashboard
```

### Docker
```bash
docker build -t safehome-frontend .
docker run -p 3000:3000 safehome-frontend
```

### Traditional Server
```bash
npm run build
npm start
```

## Key Design Decisions

1. **No Pricing Display** - Pilot program messaging instead
2. **Separate Login** - Onboarding ≠ Authentication
3. **4-Step Form Maximum** - Keep intake brief (5 fields per step)
4. **Simple Scheduling** - No calendar integration, manual admin confirmation
5. **Family-Friendly Messaging** - No technical jargon in alerts or status

## Future Enhancements

- [ ] Real calendar integration for installation scheduling
- [ ] Email templates for confirmations
- [ ] Multi-language support
- [ ] Payment integration
- [ ] SMS notifications
- [ ] Wearable integration (if needed)
- [ ] Advanced analytics dashboard for families

## Support

For issues or questions, contact: support@safehome.com
