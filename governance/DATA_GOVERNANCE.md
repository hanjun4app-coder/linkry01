# DATA_GOVERNANCE.md

# SafeHome Data Governance Rules

Version: MVP Production Phase

Purpose:
Define data ownership, retention, privacy, deletion, export, and protection rules for SafeHome.

These rules apply to:
- customer data
- behavioral data
- onboarding data
- family data
- AI-generated summaries
- sensor-derived activity data

---

# CORE PRINCIPLE

Families own their data.

SafeHome exists to protect trust, privacy, and dignity.

Data collection should always be:
- minimal
- purposeful
- privacy-first
- human-centered

---

# DATA OWNERSHIP

Customer families retain ownership of:
- onboarding information
- account information
- behavioral summaries
- notification history
- family configuration
- sensor-derived activity summaries

SafeHome does NOT claim ownership over:
- family behavioral history
- elder routine patterns
- customer-generated configuration

---

# DATA COLLECTION PRINCIPLE

SafeHome should collect:
- only necessary data
- only product-relevant information
- only data required for family reassurance and safety workflows

SafeHome should NOT collect:
- unnecessary personal information
- unrelated behavioral data
- invasive surveillance data
- facial recognition data
- unnecessary voice recordings

---

# PRIVACY PRINCIPLES

SafeHome prioritizes:
- no cameras by default
- no facial recognition
- no continuous voice recording
- non-invasive sensing
- family privacy
- elder dignity

Behavioral awareness should NEVER become surveillance.

---

# CURRENT DATA TYPES

Current system data includes:

Account Data:
- email
- password hash
- onboarding status
- family relationships

Behavioral Data:
- room movement
- inactivity periods
- bathroom duration
- routine timing
- activity summaries

Operational Data:
- login timestamps
- notification history
- onboarding events
- system logs

---

# SENSITIVE DATA RULES

Sensitive data includes:
- passwords
- password hashes
- JWTs
- setup tokens
- reset tokens
- API keys
- Mailgun credentials
- private contact information

Sensitive data MUST NEVER:
- appear in logs
- appear in notifications
- appear in debug outputs
- be exposed to unauthorized users

---

# DATA RETENTION RULES

Recommended MVP retention:

Raw sensor events:
30 days

Behavior summaries:
180 days

Notification history:
180 days

Operational logs:
30 days

Security logs:
90 days

Expired reset/setup tokens:
delete immediately after expiration or use

---

# ACCOUNT DELETION RULES

When account deletion is requested:

1. disable account access
2. revoke tokens
3. remove onboarding tokens
4. schedule data purge
5. purge behavioral history
6. purge notification history

Recommended purge window:
within 14 days

---

# DATA EXPORT PRINCIPLE

Families should eventually be able to:
- export summaries
- export notification history
- export onboarding information

Exports should NEVER include:
- secrets
- internal credentials
- hidden operational metadata

---

# FAMILY ACCESS RULES

Only authorized family members may access:
- dashboard data
- activity summaries
- alerts
- notification history

Future multi-family architecture must preserve:
- role separation
- permission boundaries
- elder privacy

---

# AI DATA ACCESS RULES

AI systems may access:
- anonymized behavioral patterns
- activity summaries
- confidence scores
- notification states

AI systems MUST NEVER:
- expose private customer information
- expose secrets
- expose passwords
- expose setup/reset tokens

AI systems should minimize data exposure whenever possible.

---

# DATA MINIMIZATION PRINCIPLE

If data is not necessary:
do not collect it.

If long-term retention is unnecessary:
delete it.

SafeHome prioritizes:
- trust
- privacy
- dignity
over excessive analytics.

---

# FUTURE COMPLIANCE DIRECTION

Future architecture should support:
- North America privacy expectations
- CCPA-style compliance
- GDPR-inspired deletion/export principles
- auditability
- consent-based sharing

---

# SAFEHOME PRIVACY PHILOSOPHY

The goal is:
family reassurance.

NOT:
behavioral surveillance.

SafeHome should always feel:
- respectful
- calm
- trustworthy
- privacy-conscious

---

# FINAL PRINCIPLE

Elder dignity is more important than data collection.

Trust is a core product feature.
