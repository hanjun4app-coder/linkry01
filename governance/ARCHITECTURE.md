# Frontend Architecture

## Overview

This is a lightweight, MVP-focused Next.js application designed for elderly care monitoring system onboarding and family monitoring. The architecture emphasizes simplicity, clarity, and trust-building over complex features.

## Design Principles

1. **No Technical Jargon** - Users see friendly language, never "risk_score", "motion_level", "device_id"
2. **Mobile-First Responsive** - Works on phone, tablet, desktop
3. **Warm & Trustworthy** - Apple/Calm/Healthcare design style
4. **Minimal State Management** - React hooks only, no Redux/Zustand
5. **Clean Separation** - Onboarding ≠ Authentication
6. **MVP Scope** - No unnecessary features

## Component Hierarchy

```
Layout (header, footer, max-width)
├── Landing Page
│   ├── Hero Section
│   ├── Benefits List
│   ├── How It Works
│   └── Pilot Program CTA
├── Onboarding (4-step form)
│   ├── Progress Bar
│   ├── Form Steps
│   │   ├── About Your Loved One
│   │   ├── Daily Routine
│   │   ├── Contact Information
│   │   └── Installation Scheduling
│   └── Navigation (Back/Next/Submit)
├── Confirmation Page
│   ├── Success Message
│   ├── Next Steps Timeline
│   └── Pre-Installation Checklist
├── Login Page
│   ├── Simple Form
│   └── Forgot Password Link
├── Dashboard (Protected)
│   ├── Status Overview
│   ├── Recent Alerts
│   └── Settings Links
└── Admin Panel (Protected)
    ├── Tab Navigation
    └── Installation Management
```

## State Management

### Onboarding Page
```javascript
const [step, setStep] = useState(1)
const [loading, setLoading] = useState(false)
const [error, setError] = useState('')
const [formData, setFormData] = useState({...})
```

### Login Page
```javascript
const [email, setEmail] = useState('')
const [password, setPassword] = useState('')
const [loading, setLoading] = useState(false)
const [error, setError] = useState('')
const [showForgotPassword, setShowForgotPassword] = useState(false)
```

### Dashboard
```javascript
const [loading, setLoading] = useState(true)
const [familyName, setFamilyName] = useState('')
const [elderName, setElderName] = useState('')
const [status, setStatus] = useState(null)
const [alerts, setAlerts] = useState([])
```

## Data Flow

### Onboarding → Backend

```
User fills form
  ↓
[Step 1] Validation
  ↓
[Step 2] Validation
  ↓
[Step 3] Validation
  ↓
[Step 4] Validation
  ↓
Form Submit → POST /api/customers
  ↓
Success → Redirect to /onboarding/done
  ↓
Error → Show error message
```

### Login → Protected Page

```
User enters email/password
  ↓
POST /api/auth/login
  ↓
Get JWT token
  ↓
Store in localStorage
  ↓
Redirect to /dashboard or /admin
  ↓
GET /api/family/dashboard (with token header)
  ↓
Display dashboard
```

### Protected Routes

Dashboard and Admin pages check for token on mount:
```javascript
useEffect(() => {
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
  }
}, [])
```

## Form Validation

Each step validates before proceeding:

**Step 1: About Your Loved One**
- Name, Age, Lives Alone, Mobility Level all required

**Step 2: Daily Routine**
- Wake time, Sleep time, Shower time, Bathroom duration all required
- Times must be valid HH:MM format

**Step 3: Contact Info**
- Email, Phone, Address required
- Email must contain @

**Step 4: Installation**
- Preferred date and time window required
- Notes optional

## Styling Strategy

### No Tailwind Build Step
- Uses plain CSS instead of utility classes
- `globals.css` contains all styling
- Smaller bundle, faster load time
- Easier to customize without npm

### Color Scheme
```css
Primary Blue: #2563eb
Dark Gray: #111827
Medium Gray: #1f2937
Light Gray: #4b5563
Very Light Gray: #6b7280, #9ca3af, #d1d5db, #e5e7eb, #f3f4f6
Background: #ffffff, #f9fafb, #f3f4f6
```

### Typography
```css
h1: 2.25rem, 700 weight
h2: 1.875rem, 600 weight
h3: 1.25rem, 600 weight
body: 1rem, 400 weight
label: 0.875rem, 500 weight
```

## File Size Targets

- Bundle: < 100KB (gzipped)
- Initial Load: < 2 seconds on 4G
- No third-party analytics
- No heavy dependencies

## API Integration Points

### Onboarding Form
```
POST /api/customers
├── Creates customer_profile
├── Creates elder_profile
├── Creates installation_profile (status="pending")
├── Creates family_reported_baseline
└── Sends confirmation email
```

### Authentication
```
POST /api/auth/login → JWT token
POST /api/auth/forgot-password → Reset email
```

### Family Dashboard
```
GET /api/family/dashboard
├── Family info
├── Elder status
├── Recent alerts (max 10)
└── Last activity timestamp
```

### Admin Panel
```
GET /api/admin/installations?status={status}
POST /api/admin/installations/{id}/confirm
POST /api/admin/installations/{id}/complete
├── Creates family account
├── Sends password setup email
└── Enables monitoring service
```

## Error Handling

### Frontend Errors
- Network errors show generic message
- Validation errors show field-specific message
- API errors show backend message (if safe)
- 401 Unauthorized redirects to /login

### User Feedback
- Red background for errors
- Yellow background for warnings
- Green background for success
- Loading states disable buttons

## Security

### Authentication
- JWT token stored in localStorage
- Token passed in Authorization header
- Token expires after 24 hours
- Invalid token redirects to login

### CORS
- Backend must allow frontend origin
- Simple requests (GET, POST with JSON)
- Credentials: include JWT in header

### Data Validation
- Frontend validates before submit
- Backend must also validate
- No sensitive data in URLs
- No email/phone logged to console

## Performance Optimization

### Code Splitting
- Next.js automatically chunks pages
- Each page loads only needed components

### Lazy Loading
- No unnecessary renders with proper dependencies
- useEffect cleanup functions prevent memory leaks

### Caching
- Static pages (Landing) cached by browser
- Dashboard data refreshed every 30 seconds
- JWT token cached in localStorage

## Responsive Design

### Mobile (< 640px)
- Single column layout
- Large touch targets (44px minimum)
- Full-width buttons
- Stacked progress bar

### Tablet (640px - 1024px)
- 2-column layouts where appropriate
- Sidebar navigation options

### Desktop (> 1024px)
- Full-width layout (max-width: 2xl = 672px content)
- Horizontal navigation
- Hover states on interactive elements

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS 14+, Android 10+)

## Testing Checklist

- [ ] Form validation on all steps
- [ ] Error messages display correctly
- [ ] Loading states work (button disabled, spinner)
- [ ] Token stored and passed with requests
- [ ] Redirect to login if token missing
- [ ] Logout clears token
- [ ] Responsive on mobile/tablet/desktop
- [ ] No console errors or warnings
- [ ] Links navigate correctly
- [ ] API calls use correct URLs and methods
