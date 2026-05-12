# REPOSITORY_STRUCTURE.md

# SafeHome Repository Structure Governance

Version: v1.0
Phase: AI-Native Repository Governance

Purpose:
Define repository structure, file organization, production boundaries, documentation placement, and AI-generated artifact management across the SafeHome project.

These rules apply to:
- Claude
- Codex
- developers
- maintainers
- AI-generated files
- future runtime AI systems

---

# CORE PRINCIPLE

Repository clarity improves:
- maintainability
- AI accuracy
- onboarding
- operational safety
- long-term scalability

AI systems should generate:
organized repositories,
NOT repository chaos.

---

# SAFEHOME REPOSITORY PHILOSOPHY

The repository should feel:
- structured
- calm
- understandable
- production-oriented
- maintainable

NOT:
- cluttered
- duplicated
- chaotic
- experiment-heavy
- AI artifact polluted

---

# PRIMARY REPOSITORY STRUCTURE

Recommended long-term structure:

SafeHome/
├── governance/
├── docs/
├── backend/
├── next-frontend/
├── infra/
├── scripts/
├── tests/
├── experiments/
├── archive/
└── assets/

---

# GOVERNANCE DIRECTORY

Purpose:
AI governance and operational boundaries.

Contains:
- AI_STARTUP_CONTEXT.md
- GOVERNANCE_INDEX.md
- CLAUDE.md
- AGENTS.md
- OPS_RULES.md
- SECURITY_RULES.md
- DATA_GOVERNANCE.md
- AI governance systems

Rules:
- governance files should remain stable
- changes require careful review
- avoid duplication

---

# DOCS DIRECTORY

Purpose:
official product and engineering documentation.

Contains:
- architecture docs
- deployment docs
- onboarding docs
- API docs
- implementation guides

Rules:
- official documentation only
- avoid temporary summaries
- avoid duplicated versions

---

# EXPERIMENTS DIRECTORY

Purpose:
AI experiments and temporary prototypes.

Contains:
- prototype logic
- AI experiments
- temporary patches
- exploratory implementations

Rules:
- experiments should NOT mix with production
- unstable files belong here
- experimental AI outputs belong here

---

# ARCHIVE DIRECTORY

Purpose:
old or deprecated files.

Contains:
- outdated docs
- replaced reports
- deprecated experiments
- old implementation summaries

Rules:
- archive instead of deleting important history
- keep repository clean
- preserve historical context when useful

---

# PRODUCTION FILE RULES

Production files should remain:
- minimal
- stable
- clearly identifiable

Production systems include:
- backend APIs
- auth systems
- deployment scripts
- production configs
- dashboard logic

AI systems MUST NOT:
mix experiments directly into production.

---

# DOCUMENTATION LIFECYCLE PRINCIPLE

Not all generated documents should remain permanent.

Temporary AI-generated:
- summaries
- reports
- comparisons
- migration notes

should eventually be:
- consolidated
- archived
- deleted if unnecessary

---

# DUPLICATION RULE

Avoid:
- duplicate summaries
- multiple conflicting guides
- repeated implementation docs
- overlapping README files

AI systems SHOULD:
prefer updating existing docs when possible.

---

# AI FILE GENERATION RULES

AI systems SHOULD:
- generate files intentionally
- place files correctly
- minimize clutter
- explain why files are created

AI systems MUST NOT:
- generate unnecessary markdown explosions
- create excessive duplicate variants
- create abandoned artifacts carelessly

---

# README PRINCIPLE

Major directories should contain:
README.md

Examples:
- governance/README.md
- docs/README.md
- experiments/README.md

README files should explain:
- directory purpose
- structure
- usage
- maintenance expectations

---

# EXPERIMENTAL SAFETY RULE

Experimental systems should remain isolated from:
- production auth
- production deployment
- production databases
- production escalation systems

---

# GOVERNANCE STABILITY RULE

Governance files should evolve:
carefully and gradually.

Avoid:
- constant rewriting
- governance instability
- conflicting AI rules

---

# AI REPOSITORY BEHAVIOR PRINCIPLE

AI systems should behave like:
careful engineering collaborators.

NOT:
uncontrolled file generators.

---

# REPOSITORY CLEANUP PRINCIPLE

Periodic cleanup should:
- archive unused docs
- consolidate duplicates
- reduce clutter
- preserve important history

The goal is:
clarity,
NOT maximum file count.

---

# SAFEHOME ENGINEERING PHILOSOPHY

The repository should support:
- long-term maintainability
- AI collaboration
- human understanding
- production safety
- calm engineering workflows

---

# FINAL PRINCIPLE

A clean repository improves:
trust,
scalability,
and AI effectiveness.
