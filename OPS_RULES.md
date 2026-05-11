# OPS_RULES.md

# SafeHome Operational Safety Rules

Version: MVP Production Phase

Purpose:
Define operational safety, deployment, backup, rollback, and production protection rules for SafeHome.

These rules apply to:
- humans
- Claude
- Codex
- AI agents
- future maintainers
- deployment workflows

---

# CORE PRINCIPLE

Production stability is more important than deployment speed.

Never sacrifice recoverability for convenience.

---

# ENVIRONMENT HIERARCHY

Required deployment flow:

Local
→ Staging
→ Human approval
→ Production

Production must NEVER be treated as a testing environment.

---

# PRODUCTION SAFETY RULES

NEVER in production:

- run git clean -fd
- delete virtual environments
- delete SQLite databases
- overwrite .env blindly
- run destructive migrations without backup
- deploy untested auth changes
- bypass backups
- disable JWT auth
- disable logging
- disable monitoring
- bypass staging intentionally
- auto-deploy AI-generated changes

---

# REQUIRED PRE-DEPLOY CHECKLIST

Before any production deployment:

1. Create backup
2. Verify rollback exists
3. Verify environment variables
4. Verify database path
5. Verify Mailgun configuration
6. Verify auth configuration
7. Verify JWT configuration
8. Verify service file
9. Run syntax checks
10. Verify health endpoint locally/staging

---

# REQUIRED POST-DEPLOY CHECKLIST

After deployment:

1. Verify /health
2. Verify onboarding
3. Verify setup-password flow
4. Verify login
5. Verify JWT auth
6. Verify dashboard loads
7. Verify Mailgun
8. Verify backups still exist
9. Verify service restart success

Deployment is NOT complete until verification passes.

---

# BACKUP RULES

Always backup before:

- deployments
- migrations
- auth changes
- database changes
- environment changes
- service configuration changes

Minimum backup requirements:
- database
- .env
- systemd service
- application code

---

# ROLLBACK PRINCIPLE

Every deployment must have:
- rollback path
- recoverable backup
- verified restore method

If production breaks:
- rollback first
- debug second

---

# AUTHENTICATION SAFETY RULES

Never:
- remove JWT protection
- bypass auth middleware
- expose setup tokens
- expose reset tokens
- expose passwords
- log sensitive credentials

Auth systems are considered:
CRITICAL INFRASTRUCTURE

---

# DATABASE RULES

SQLite is the current production MVP database.

Never:
- delete production SQLite files
- migrate without backup
- overwrite schema blindly
- run unreviewed migrations

Prefer:
- additive migrations
- backwards compatibility
- recoverability

---

# AI OPERATIONAL RULES

AI systems MUST NEVER:
- claim deployment succeeded without verification
- fabricate test results
- fabricate health checks
- fabricate email delivery confirmation
- auto-run destructive production commands

AI systems SHOULD:
- recommend incremental changes
- prefer minimal patches
- explain operational risks
- prioritize stability

---

# INCIDENT RESPONSE RULE

If production breaks:

Priority order:
1. restore service
2. restore auth
3. restore dashboard
4. restore onboarding
5. investigate root cause

Customer access is prioritized over feature development.

---

# MONITORING RULES

Critical systems:
- onboarding
- login
- JWT auth
- dashboard
- Mailgun
- backups
- /health endpoint

These systems should always be verified after deployments.

---

# SAFEHOME OPERATIONS PHILOSOPHY

SafeHome prioritizes:
1. stability
2. recoverability
3. trust
4. privacy
5. maintainability

NOT:
- fast risky deployment
- aggressive automation
- experimental production changes

---

# FINAL PRINCIPLE

Production systems protect real families.

Operational safety is a product feature.
