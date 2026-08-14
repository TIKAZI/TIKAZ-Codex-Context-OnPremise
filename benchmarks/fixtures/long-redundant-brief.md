# Migration evidence

Release v5.8.0 is scheduled for 2026-11-15. Back up the database, then run `python db_migrate.py --release v5.8.0`. The required verification marker is MIGRATION_OK_58.

# Brand background

The design system uses a calm blue visual direction and a consistent spacing rhythm across public pages. This material is useful to a design review but irrelevant to a database migration.

# Editorial notes

Writers should prefer concise headings, direct verbs, and short examples. The editorial style does not change the migration command or its rollback evidence.

# Community introduction

The project welcomes reproducible bug reports and focused proposals. Contributors should explain the observed behavior and expected outcome before submitting a change.

# Product positioning

The toolkit helps people prepare task-specific context for coding assistants. Its public story emphasizes local control, traceability, and honest measurement.

# Visual language

Interface surfaces favor strong typographic hierarchy, restrained decoration, and generous whitespace. Cards should remain readable on narrow screens.

# Documentation maintenance

Documentation examples should be tested when possible. Stale screenshots and obsolete setup notes should be removed during a planned documentation pass.

# Release communication

Release notes should separate user-visible changes, fixes, known limitations, and upgrade guidance. Marketing copy must not replace technical evidence.

# Support workflow

Support requests are triaged by reproducibility, impact, and available evidence. Vague reports are returned for clarification rather than guessed at.

# Repeated product positioning

The toolkit helps people prepare task-specific context for coding assistants. Its public story emphasizes local control, traceability, and honest measurement.

# Migration rollback

If the migration verification fails, preserve the original logs and restore from the pre-migration backup. Do not improvise a new command from surrounding prose.
