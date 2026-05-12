# AI_FILE_GENERATION_RULES.md

# SafeHome AI File Generation Rules

Version: v1.0
Phase: AI-Native Repository Governance

Purpose:
Define when AI systems may create files, where files should be placed, how temporary outputs should be handled, and how to prevent repository clutter.

These rules apply to:
- Claude
- Codex
- Cursor
- AI-generated scripts
- AI-generated documentation
- AI-generated reports
- AI-generated prototypes

---

# CORE PRINCIPLE

AI should create files intentionally.

Every generated file should have:
- a clear purpose
- a correct location
- a responsible owner
- a lifecycle

AI should NOT create files simply because it can.

---

# FILE CREATION RULE

Before creating a new file, AI should ask:

1. Does this file need to exist?
2. Can an existing file be updated instead?
3. Is this production, documentation, governance, experiment, or archive?
4. Will this file still be useful later?
5. Could this create duplicate documentation?

If the answer is unclear:
prefer updating existing files.

---

# ALLOWED FILE CREATION

AI may create files for:

- production code
- tests
- migrations
- governance documents
- official documentation
- deployment scripts
- isolated experiments
- clearly requested deliverables

Only when the user requested or approved the creation.

---

# DISCOURAGED FILE CREATION

AI should avoid creating:

- duplicate summaries
- repeated final reports
- multiple overlapping implementation guides
- excessive markdown files
- unused helper scripts
- abandoned prototype files
- temporary PDFs unless requested

---

# DIRECTORY PLACEMENT RULES

Governance files:
governance/

Official documentation:
docs/

Production backend code:
backend/ or app/

Frontend code:
next-frontend/

Deployment scripts:
scripts/

Infrastructure:
infra/

Experiments:
experiments/

Deprecated files:
archive/

Temporary outputs:
tmp/ or outputs/

---

# NAMING RULES

File names should be:
- clear
- stable
- descriptive
- not overly long

Preferred examples:
- OPS_RULES.md
- AI_CONFIDENCE_RULES.md
- dashboard_status_api_test.py

Avoid:
- FINAL_FINAL_SUMMARY.md
- NEW_NEW_VERSION.md
- COMPLETE_REVISED_LAST.md
- random_patch_123.py

---

# MARKDOWN GENERATION RULE

AI should not generate a new `.md` file unless:

- it is governance
- it is official documentation
- it is requested by the user
- it replaces or consolidates older docs

When possible:
update existing documentation.

---

# TEST FILE RULE

AI may create test files when:
- they validate a real feature
- they are placed in a proper tests directory
- they can be run consistently
- they do not depend on secrets

Temporary test files should be moved to:
experiments/
or deleted after use.

---

# PROTOTYPE RULE

Prototype files must go into:

experiments/

AI must not place unstable prototype files directly into production directories.

---

# PDF / ASSET RULE

AI may generate PDFs, images, or presentation assets only when explicitly requested.

Generated assets should go into:

assets/
or
deliverables/

Not into production code directories.

---

# CLEANUP RULE

After AI-generated work, AI should report:

- files created
- files modified
- files deleted
- files that should be reviewed
- files that may be temporary

---

# GIT STAGING RULE

AI should never recommend:

git add .

unless the repository is clean and the user explicitly approves.

Preferred:
git add specific-file-name

Example:
git add governance/AI_FILE_GENERATION_RULES.md

---

# PRODUCTION SAFETY RULE

AI must never create or modify:

- .env
- production database files
- secrets
- private keys
- backup archives

without explicit human approval.

---

# REPOSITORY SPRAWL WARNING

If AI detects many untracked generated files, it should recommend:

1. stop creating new files
2. inventory existing files
3. classify files
4. archive or delete duplicates
5. commit only intentional files

---

# FINAL PRINCIPLE

AI-generated files should improve clarity.

They should never make the repository harder to understand.
