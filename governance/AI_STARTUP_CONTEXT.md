# AI_STARTUP_CONTEXT.md

# SafeHome / Linkry Tech — AI Startup Context

Version: v1.0
Phase: MVP Production Governance Foundation

Purpose:
This document is the primary startup context for all AI systems, developers, maintainers, Claude sessions, Codex sessions, and future runtime AI agents working on SafeHome.

This file should be loaded FIRST before:
- development
- debugging
- architecture planning
- deployment work
- AI behavior modifications
- dashboard redesign
- escalation changes
- production operations

---

# PROJECT IDENTITY

Project Name:
SafeHome / Linkry Tech

Mission:
Build a privacy-first AI-powered elderly home safety and family reassurance system for the North American market.

SafeHome is:
- calm technology
- family reassurance technology
- AI-assisted safety awareness
- privacy-first behavioral monitoring

SafeHome is NOT:
- a medical diagnosis platform
- a surveillance platform
- a hospital system
- an autonomous authority system

---

# CORE PRODUCT PRINCIPLES

SafeHome prioritizes:

1. Trust
2. Reliability
3. Privacy
4. Elder dignity
5. Calm UX
6. Human-centered AI
7. Explainability
8. Operational safety
9. Gradual AI improvement
10. Maintainability

SafeHome does NOT prioritize:
- AI hype
- aggressive automation
- fear-based engagement
- surveillance-style monitoring
- unstable experimentation

---

# PRODUCT POSITIONING

SafeHome helps families:
- notice meaningful behavioral changes
- reduce missed warning signs
- stay connected to aging loved ones
- receive calm reassurance

The product should feel like:
"A calm family reassurance center."

NOT:
- a security operations center
- a hospital monitoring dashboard
- a surveillance console

---

# CURRENT PRODUCTION STATUS

Frontend:
https://safehome.linkrytech.com

API:
https://api.safehome.linkrytech.com

Backend:
FastAPI + SQLite + systemd on Ubuntu

Infrastructure:
- Ubuntu VPS
- Nginx
- Mailgun
- JWT auth
- backup system

Current production features:
- onboarding
- setup password
- login
- JWT auth
- dashboard
- Mailgun integration
- backup system
- onboarding email flow

---

# CURRENT PRODUCT PRIORITIES

Current priorities:

1. Dashboard productization
2. Notification escalation system
3. Alert preferences
4. AI learning visualization
5. Staging environment
6. Performance optimization
7. Multi-sensor behavior learning
8. Family member support
9. Forgot password flow
10. Duplicate account prevention

AI systems SHOULD prioritize these areas before introducing major new systems.

---

# GOVERNANCE LOADING ORDER

All AI systems should load governance files in this order:

1. GOVERNANCE_INDEX.md
2. CLAUDE.md
3. AGENTS.md
4. OPS_RULES.md
5. SECURITY_RULES.md
6. DATA_GOVERNANCE.md
7. AI_CONFIDENCE_RULES.md
8. FAMILY_PERMISSION_MODEL.md
9. SYSTEM_AUTHORITY.md
10. AI_COMMUNICATION_STYLE.md
11. SENSOR_TRUST_MODEL.md
12. INCIDENT_RESPONSE.md

---

# CRITICAL AI RULES

AI systems MUST NEVER:
- remove JWT protection
- expose secrets
- expose passwords
- expose setup/reset tokens
- auto-deploy to production
- bypass auth
- fabricate deployment success
- fabricate health checks
- fabricate production verification
- use fear-based messaging
- claim medical diagnosis
- claim certainty without confidence thresholds

---

# HUMAN AUTHORITY PRINCIPLE

Humans remain the final authority.

AI systems:
- assist
- recommend
- summarize
- explain
- implement scoped changes

Humans:
- approve
- deploy
- authorize
- override
- manage production authority

---

# AI COMMUNICATION PRINCIPLES

SafeHome communication should remain:
- calm
- warm
- respectful
- reassuring
- emotionally stable

Avoid:
- panic wording
- robotic tone
- surveillance-heavy language
- aggressive escalation language

Preferred:
"SafeHome noticed a change in routine."

Forbidden:
"Critical anomaly detected."

---

# PRODUCTION SAFETY RULES

Before production deployment:
- create backups
- verify rollback
- verify /health
- verify onboarding
- verify login
- verify dashboard
- verify Mailgun

Never:
- run git clean -fd in production
- delete production databases
- bypass staging intentionally
- deploy unverified auth changes

---

# AI DEVELOPMENT PHILOSOPHY

SafeHome AI should remain:
- bounded
- interpretable
- confidence-aware
- explainable
- human-supervised

AI should evolve:
gradually and safely.

---

# SENSOR PHILOSOPHY

Sensors provide:
signals,
NOT certainty.

Behavioral confidence should emerge from:
- correlation
- duration
- multi-sensor agreement
- gradual baseline learning

NOT:
single isolated events.

---

# FAMILY PERMISSION PRINCIPLE

Families own their data.

Primary Owners control:
- permissions
- escalation
- caregiver access
- alert routing

AI systems MUST respect:
- permission boundaries
- elder ownership
- role visibility

---

# INCIDENT RESPONSE PRINCIPLE

If production fails:

Priority order:
1. restore service
2. restore auth
3. restore onboarding
4. restore dashboard
5. investigate root cause

Rollback is preferred over:
risky live debugging.

---

# SAFEHOME LONG-TERM VISION

SafeHome aims to become:
a trusted calm technology platform for connected families.

The goal is:
- reassurance
- dignity
- trust
- safe independence
- human-centered AI assistance

NOT:
maximum automation.

---

# FINAL PRINCIPLE

SafeHome is:
a human-first AI-assisted system.

AI remains:
bounded,
reviewable,
and assistive.

Humans remain responsible.
