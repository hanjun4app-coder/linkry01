# PRODUCTION_FILE_RULES.md

# SafeHome Production File Protection Rules

Version: v1.0
Phase: Production Safety Governance

Purpose:
Define production-critical files, protected systems, deployment boundaries, and AI modification limitations across the SafeHome platform.

These rules apply to:
- Claude
- Codex
- developers
- deployment workflows
- production infrastructure
- AI-generated patches

---

# CORE PRINCIPLE

Production systems protect real families.

AI systems should prioritize:
- safety
- stability
- recoverability
- operational trust

NOT:
- aggressive modification
- risky experimentation
- uncontrolled automation

---

# PRODUCTION-CRITICAL FILES

The following are considered:
production-critical.

Examples include:

## Backend Core
- app/main.py
- app/security.py
- app/routes/auth.py
- app/database.py
- app/config.py

## Infrastructure
- nginx.conf
- systemd service files
- deployment scripts
- backup scripts

## Secrets / Environment
- .env
- Mailgun configs
- JWT secrets
- API keys

## Database
- SQLite database files
- migration scripts
- schema definitions

---

# HIGH-RISK MODIFICATION RULE

AI systems MUST treat modifications to production-critical files as:
HIGH RISK.

High-risk modifications require:
- human review
- rollback awareness
- deployment caution
- verification planning

---

# AUTH SYSTEM PROTECTION RULE

Auth systems are:
critical infrastructure.

AI systems MUST NEVER:
- remove JWT protection
- bypass auth
- disable permission checks
- weaken token validation
- expose auth secrets

Auth changes require:
careful review and testing.

---

# ENVIRONMENT FILE RULE

AI systems MUST NEVER:
- overwrite .env blindly
- expose secrets
- generate fake production credentials
- commit secrets to git

Environment changes require:
explicit human approval.

---

# DATABASE SAFETY RULE

AI systems MUST NEVER:
- delete production databases
- reset production schemas
- perform destructive migrations automatically
- modify production data carelessly

Before database modifications:
- create backups
- verify rollback plans
- confirm migration intent

---

# BACKUP REQUIREMENT RULE

Before modifying:
- auth systems
- deployment systems
- infrastructure
- databases
- production configs

Always create:
- backup
- rollback path
- recovery plan

---

# DEPLOYMENT BOUNDARY RULE

AI systems may:
- suggest deployment steps
- generate deployment scripts
- review deployment safety

AI systems MUST NEVER:
- autonomously deploy production changes
- restart production blindly
- modify live infrastructure automatically

Humans remain:
deployment authority.

---

# PRODUCTION DEBUGGING RULE

If production becomes unstable:

Preferred order:
1. stop risky changes
2. stabilize system
3. rollback if needed
4. investigate root cause

AI systems MUST NOT:
continue aggressive debugging on unstable production systems.

---

# HOTFIX RULE

Emergency hotfixes should:
- minimize scope
- preserve rollback capability
- avoid unrelated changes

AI systems SHOULD:
avoid bundling unrelated modifications into production fixes.

---

# STAGING PRINCIPLE

Major changes should ideally pass through:
staging before production.

Examples:
- auth redesign
- escalation logic
- database migrations
- sensor fusion systems

---

# AI CODE GENERATION RULE

AI-generated production code should:
- remain minimal
- preserve existing architecture
- avoid unnecessary rewrites
- avoid hidden behavior changes

AI SHOULD:
prefer incremental changes over massive rewrites.

---

# LOGGING SAFETY RULE

AI systems MUST NEVER:
- expose secrets in logs
- expose tokens
- expose passwords
- expose sensitive family data

Production logging should prioritize:
privacy and security.

---

# PRODUCTION MONITORING RULE

Critical systems should remain monitored:
- onboarding
- login
- dashboard
- backups
- Mailgun
- database access
- /health endpoint

---

# FAILURE RESPONSE PRINCIPLE

When uncertainty exists:
prefer rollback.

When risk exists:
prefer caution.

When production stability is threatened:
protect service first.

---

# SAFEHOME OPERATIONAL PHILOSOPHY

Production reliability is part of:
the product experience.

Families should experience:
- stability
- predictability
- trust
- calm operation

---

# FINAL PRINCIPLE

Production systems should evolve:
carefully,
incrementally,
and safely.
