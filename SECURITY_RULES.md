# SECURITY_RULES.md

# SafeHome Security & Access Rules

Version: MVP Production Phase

Purpose:
Define authentication, authorization, credential handling, token safety, secret protection, and operational security rules for SafeHome.

These rules apply to:
- onboarding
- authentication
- JWT systems
- Mailgun integration
- future SMS systems
- future caregiver systems
- AI systems
- deployment workflows

---

# CORE PRINCIPLE

Security protects trust.

SafeHome protects:
- families
- elderly privacy
- behavioral data
- authentication systems
- notification systems

Security should remain:
- calm
- reliable
- maintainable
- human-safe

---

# AUTHENTICATION PRINCIPLE

All customer-facing protected routes MUST require authentication.

Protected systems include:
- dashboard
- alerts
- family settings
- onboarding management
- future caregiver systems
- future elder management systems

JWT protection must NEVER be removed.

---

# PASSWORD RULES

Passwords MUST:
- be hashed
- never be stored in plaintext
- never appear in logs
- never appear in emails
- never appear in notifications

Minimum password requirements:
- minimum 8 characters
- at least one letter
- at least one number

Future recommended:
- password strength meter
- rate limiting
- brute-force protection

---

# JWT RULES

JWTs are considered sensitive credentials.

JWTs MUST NEVER:
- appear in logs
- appear in frontend console output
- appear in email
- appear in notifications
- be exposed publicly

JWT systems should support:
- expiration
- invalidation
- future refresh-token architecture

---

# TOKEN RULES

Sensitive tokens include:
- setup-password tokens
- password reset tokens
- JWTs
- API keys

Sensitive tokens MUST:
- expire
- be single-use when applicable
- never appear in logs
- never appear in frontend debugging output

Expired tokens should be invalid immediately.

---

# PASSWORD RESET RULES

Forgot-password systems MUST:
- avoid exposing whether email exists
- use secure reset tokens
- expire reset tokens
- invalidate used tokens

Correct wording:
"If this email is registered, we’ll send a reset link."

Forbidden:
"This email does not exist."

---

# EMAIL SECURITY RULES

Emails MUST NEVER contain:
- passwords
- password hashes
- JWTs
- setup tokens beyond intended flows
- Mailgun API keys
- internal secrets

Internal registration notifications should contain:
- onboarding details
- customer contact information
- operationally useful information

But NEVER:
- sensitive credentials

---

# SECRET MANAGEMENT RULES

Secrets include:
- JWT secrets
- Mailgun API keys
- database credentials
- environment secrets
- webhook secrets

Secrets MUST:
- remain in .env
- never be committed to git
- never appear in logs
- never appear in frontend code

Production secrets should NEVER be hardcoded.

---

# ACCESS CONTROL RULES

Users may only access:
- their own family dashboard
- authorized elder data
- permitted notification settings

Future systems should support:
- role separation
- family permissions
- caregiver permissions
- installer/admin permissions

---

# RATE LIMITING PRINCIPLE

Future authentication systems should support:
- login rate limiting
- reset-password rate limiting
- onboarding abuse prevention
- API abuse prevention

Security should reduce abuse without creating fear-heavy UX.

---

# AI SECURITY RULES

AI systems MUST NEVER:
- expose secrets
- expose passwords
- expose JWTs
- expose reset tokens
- expose setup tokens
- fabricate security verification
- bypass auth intentionally

AI systems SHOULD:
- preserve auth integrity
- recommend minimal-risk changes
- warn about insecure patterns

---

# LOGGING RULES

Logs should:
- help debugging
- support operational recovery
- avoid sensitive exposure

Logs MUST NEVER include:
- passwords
- JWTs
- secret keys
- setup tokens
- reset tokens
- sensitive customer credentials

---

# PRODUCTION SECURITY RULES

Production systems MUST:
- use HTTPS
- preserve JWT validation
- preserve auth middleware
- preserve role checks
- preserve environment isolation

Never:
- disable auth for convenience
- bypass permissions temporarily
- expose admin/debug routes publicly

---

# FUTURE SECURITY DIRECTION

Future SafeHome systems should support:
- audit logs
- role-based permissions
- family invite permissions
- device authorization
- staged admin access
- anomaly detection for auth abuse

However:
security should remain maintainable and understandable.

---

# SAFEHOME SECURITY PHILOSOPHY

Security exists to protect:
- trust
- dignity
- privacy
- family safety

SafeHome should never feel:
- invasive
- hostile
- paranoid
- surveillance-heavy

Security should remain:
calm, invisible, and reliable.

---

# FINAL PRINCIPLE

Families trust SafeHome with sensitive moments.

Protecting that trust is a core system responsibility.
