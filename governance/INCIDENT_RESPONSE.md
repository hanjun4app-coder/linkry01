# INCIDENT_RESPONSE.md

# SafeHome Incident Response & Recovery Rules

Version: v1.0
Phase: Production Stability Governance

Purpose:
Define incident classification, recovery procedures, rollback philosophy, operational escalation, and AI behavior during production incidents.

These rules apply to:
- production outages
- auth failures
- deployment failures
- database failures
- sensor failures
- AI escalation failures
- infrastructure incidents

---

# CORE PRINCIPLE

Restore service first.
Debug second.

Customer trust depends on:
- stability
- recovery speed
- calm communication
- operational transparency

---

# INCIDENT PRIORITY LEVELS

## P0 — CRITICAL

Examples:
- production completely offline
- login system broken
- onboarding unusable
- database corruption
- widespread auth failure

Impact:
core customer access unavailable.

Primary objective:
restore service immediately.

---

## P1 — HIGH

Examples:
- dashboard partially broken
- alerts delayed
- Mailgun failure
- degraded escalation system
- partial API failure

Impact:
important features degraded,
but core access still available.

---

## P2 — MEDIUM

Examples:
- UI inconsistencies
- delayed summaries
- notification duplication
- minor dashboard issues

Impact:
non-critical degradation.

---

## P3 — LOW

Examples:
- cosmetic issues
- wording problems
- small UX inconsistencies

Impact:
minimal operational impact.

---

# INCIDENT RESPONSE PRIORITY

Always prioritize:

1. restore production
2. restore auth
3. restore onboarding
4. restore dashboard
5. restore notifications
6. investigate root cause
7. optimize long-term fix

---

# ROLLBACK PRINCIPLE

Rollback is preferred over:
high-risk live debugging.

If production becomes unstable:
- rollback first
- stabilize second
- investigate third

Never continue risky debugging:
on unstable production systems.

---

# BACKUP REQUIREMENTS

Before:
- deployment
- migrations
- auth changes
- infrastructure changes

Always create:
- database backup
- environment backup
- code snapshot
- rollback path

---

# AUTH FAILURE RESPONSE

If login/auth fails:

1. stop additional deployments
2. verify JWT configuration
3. verify environment variables
4. verify auth routes
5. rollback if necessary
6. verify /health
7. verify onboarding
8. verify dashboard access

Auth systems are:
critical infrastructure.

---

# DATABASE FAILURE RESPONSE

If database issues occur:

1. stop schema modifications
2. verify database file
3. verify backup integrity
4. restore latest stable backup if needed
5. verify API access
6. verify onboarding/login

Never:
attempt destructive recovery blindly.

---

# DEPLOYMENT FAILURE RESPONSE

If deployment fails:

1. stop further changes
2. review service logs
3. verify syntax
4. verify environment variables
5. rollback if production unstable
6. verify service restart
7. verify /health

---

# SERVICE FAILURE RESPONSE

If systemd service fails:

1. check service status
2. inspect journal logs
3. verify virtual environment
4. verify executable paths
5. verify dependencies
6. restart safely
7. rollback if necessary

---

# SENSOR INCIDENT RESPONSE

If sensors disconnect:

AI systems SHOULD:
- reduce confidence
- avoid aggressive escalation
- continue observation when possible

AI systems MUST NOT:
assume emergency solely from temporary disconnects.

---

# MAILGUN / EMAIL FAILURE RESPONSE

If email delivery fails:

1. verify Mailgun configuration
2. verify API keys
3. verify DNS/domain
4. preserve dashboard functionality
5. avoid blocking onboarding unnecessarily

Notification failure should NOT:
break core access.

---

# AI INCIDENT BEHAVIOR RULES

During production incidents,
AI systems MUST:
- reduce aggressive escalation
- avoid false certainty
- preserve calm wording
- recommend human review

AI systems MUST NEVER:
- fabricate recovery success
- fabricate health checks
- fabricate deployment verification

---

# HUMAN AUTHORITY DURING INCIDENTS

Humans remain:
final operational authority.

AI may:
- recommend recovery steps
- summarize logs
- suggest rollback

AI MUST NEVER:
- autonomously perform destructive recovery
- bypass approvals
- hide uncertainty

---

# CUSTOMER COMMUNICATION PRINCIPLE

Customer communication during incidents should remain:
- calm
- transparent
- reassuring
- non-technical when possible

Avoid:
- panic wording
- blame-heavy messaging
- engineering jargon

---

# POST-INCIDENT REVIEW PRINCIPLE

After major incidents:

Review:
- root cause
- operational gaps
- governance failures
- monitoring weaknesses
- prevention opportunities

The goal is:
continuous operational improvement.

---

# MONITORING PRIORITIES

Critical systems:
- onboarding
- login
- JWT auth
- dashboard
- /health
- backups
- Mailgun
- database availability

---

# SAFEHOME OPERATIONAL PHILOSOPHY

SafeHome prioritizes:
- recoverability
- trust
- calm operations
- operational transparency
- gradual improvement

NOT:
- reckless debugging
- panic recovery
- risky hotfixes

---

# FINAL PRINCIPLE

Production systems protect real families.

Recovery quality is part of the product experience.
