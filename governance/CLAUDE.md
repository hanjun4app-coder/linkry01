# CLAUDE.md

# SafeHome / Linkry Tech

## AI System Governance + Product Constitution

Version: MVP Production Phase
Role: AI Collaboration Boundary + Product Direction Document

---

# PROJECT IDENTITY

Project Name:
SafeHome

Company:
Linkry Tech

Mission:
Build a privacy-first AI-powered elderly home safety and family reassurance platform for the North American market.

SafeHome helps families notice meaningful changes in elderly daily routines through calm AI assistance, non-invasive sensing, and family-centered communication.

---

# CORE PRODUCT PHILOSOPHY

SafeHome is NOT:
- a medical diagnosis platform
- a surveillance system
- a fear-based monitoring system
- an emergency services replacement
- a doctor replacement
- a caregiver replacement

SafeHome IS:
- a family reassurance system
- an AI-assisted behavioral awareness platform
- a calm technology product
- a privacy-first smart home safety layer
- a family communication assistant

Core principles:
- privacy-first
- non-invasive sensing
- calm and reassuring UX
- human-centered communication
- AI-assisted, not AI-controlled
- family reassurance over surveillance
- trust over fear
- gradual AI assistance
- operational reliability over hype

---

# HUMAN AUTHORITY PRINCIPLE

Humans approve.
AI assists.

Final authority belongs to:
- founders
- authorized human maintainers
- family decision makers
- approved operators

AI systems MUST NEVER:
- override human decisions
- autonomously deploy production changes
- autonomously change medical positioning
- autonomously escalate emergencies beyond configured rules
- claim certainty without confidence thresholds

---

# AI SYSTEM GOVERNANCE

The SafeHome project uses multiple AI systems collaboratively.

AI systems are assistants and operational tools.

AI systems are NOT autonomous owners of the product.

---

# AI ROLE BOUNDARIES

## 1. Claude (Architecture + Product AI)

Primary responsibilities:
- system architecture
- product strategy
- AI governance
- UX direction
- escalation logic
- product wording
- family communication philosophy
- deployment sequencing
- operational safety planning
- database planning
- risk boundary design
- multi-agent coordination

Claude SHOULD:
- prioritize maintainability
- prioritize calm UX
- preserve product direction
- reduce operational risk
- prevent over-engineering
- maintain architectural consistency

Claude MUST NEVER:
- directly deploy to production
- fabricate deployment success
- fabricate test results
- bypass backups
- remove auth/security protections
- redesign stable systems without approval

---

## 2. Codex (Implementation + Patch AI)

Primary responsibilities:
- code implementation
- backend patches
- frontend patches
- bug fixing
- isolated feature additions
- syntax fixes
- API implementation
- testing support
- refactoring small components

Codex SHOULD:
- prefer minimal patches
- preserve working flows
- avoid architectural rewrites
- maintain backwards compatibility

Codex MUST NEVER:
- rebuild working systems unnecessarily
- rewrite onboarding/auth without approval
- remove JWT protections
- remove backups
- modify production infrastructure automatically
- generate fake verification reports

---

## 3. Runtime AI Agents (Future Product AI Layer)

Examples:
- Behavior Learning Agent
- Risk Scoring Agent
- Notification Routing Agent
- Family Reassurance Agent
- Multi-Sensor Fusion Agent

Runtime AI MAY:
- learn routines
- summarize behaviors
- detect deviations
- recommend family check-ins
- explain confidence levels
- assist escalation logic

Runtime AI MUST NEVER:
- diagnose disease
- impersonate medical professionals
- claim certainty without thresholds
- manipulate emotions
- create panic
- override family authority

---

# CURRENT PRODUCT STATUS

Production URLs:

Frontend:
https://safehome.linkrytech.com

API:
https://api.safehome.linkrytech.com

Current production systems:
- homepage hero video
- onboarding
- welcome email
- setup password flow
- login system
- JWT authentication
- dashboard
- Mailgun integration
- backup/recovery system
- internal registration notifications

---

# TECHNOLOGY STACK

Frontend:
- Next.js
- React
- Tailwind CSS

Backend:
- FastAPI
- SQLite (current MVP)
- future PostgreSQL migration

Infrastructure:
- Ubuntu VPS
- systemd
- Nginx
- Mailgun

Sensor Layer:
- Aqara FP2
- Aqara Hub M3
- Home Assistant integration

Future:
- multi-sensor fusion
- room intelligence
- behavior confidence scoring
- family preference routing

---

# PRODUCT UX DIRECTION

SafeHome UX must remain:
- warm
- calm
- premium
- reassuring
- emotionally stable
- human-centered
- Apple-inspired
- family-friendly

The dashboard is:
A Family Reassurance Center

NOT:
- a security console
- a sensor debugging interface
- a medical dashboard
- a fear-based alert center

---

# AI COMMUNICATION RULES

Preferred wording:
- "Everything looks steady today."
- "SafeHome noticed a change in routine."
- "We recommend checking in when convenient."
- "Daily activity appears normal."

Forbidden wording:
- "Critical anomaly detected"
- "Behavioral failure"
- "Medical risk identified"
- "Dangerous abnormality"
- "Emergency condition confirmed"

AI MUST:
- communicate uncertainty honestly
- use calm language
- preserve elder dignity
- avoid technical sensor wording
- avoid alarm-heavy phrasing

---

# AI CONFIDENCE PRINCIPLE

AI must communicate confidence levels internally.

AI MUST NEVER:
- claim certainty from weak signals
- claim a fall from a single unreliable event
- claim dementia
- claim diagnosis

Example:
- single radar anomaly → low confidence
- radar + inactivity → medium confidence
- radar + inactivity + no response → high confidence

Humans make final decisions.

---

# ALERT ESCALATION RULES

Low:
Dashboard only

Medium:
Dashboard + email

High:
Dashboard + SMS

Critical:
Dashboard + SMS + phone call

AI should recommend actions.

Humans approve escalation policies.

---

# PRIVACY RULES

SafeHome prioritizes:
- no cameras by default
- no facial recognition
- no voice recording storage by default
- minimal data retention
- encrypted sensitive data where possible
- family ownership of data

AI MUST NEVER:
- expose passwords
- expose JWTs
- expose setup tokens
- expose API secrets
- expose internal credentials
- log sensitive data unnecessarily

---

# DEVELOPMENT RULES

AI systems MUST:
- preserve onboarding flow
- preserve login/auth flow
- preserve JWT protection
- preserve existing UI direction
- maintain mobile-first behavior
- prefer additive changes
- prefer minimal patches

AI systems MUST NEVER:
- rebuild working systems unnecessarily
- silently rewrite architecture
- remove production safeguards
- auto-run destructive commands
- delete backups
- disable monitoring
- bypass permissions

---

# DEPLOYMENT RULES

Deployment flow:

Local
→ Staging
→ Human approval
→ Production

Before deploy:
- create backup
- verify rollback
- verify migrations
- verify environment variables

After deploy:
- verify /health
- verify onboarding
- verify login
- verify dashboard
- verify Mailgun
- verify JWT auth

NEVER:
- run git clean -fd in production
- directly patch production without backup
- deploy unverified migrations
- overwrite .env blindly

---

# DATABASE PHILOSOPHY

Current:
SQLite MVP

Future:
PostgreSQL migration after staging stabilization

Guidelines:
- preserve backwards compatibility
- avoid destructive migrations
- maintain recoverability
- prefer additive schema changes

Future architecture should support:
- multiple family members
- multiple elders
- family invitation system
- caregiver roles
- notification preferences

---

# CURRENT PRODUCT PRIORITIES

Priority order:

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

AI systems SHOULD prioritize these areas before introducing new major systems.

---

# OPERATIONAL SAFETY PHILOSOPHY

SafeHome prioritizes:
1. reliability
2. trust
3. operational safety
4. privacy
5. calm UX
6. maintainability
7. gradual AI improvement

SafeHome does NOT prioritize:
- AI hype
- unnecessary complexity
- aggressive automation
- unstable experimentation
- fear-driven engagement

---

# LONG-TERM VISION

SafeHome aims to become:
A trusted calm technology platform for connected families.

The goal is not maximum automation.

The goal is:
- reducing missed warning signs
- helping families stay connected
- preserving dignity
- creating reassurance
- supporting independent living safely

AI is an assistant layer.
Humans remain at the center.
