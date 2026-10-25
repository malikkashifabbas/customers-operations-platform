# CLAUDE.md

Guidance for Claude Code (and any AI or developer) working in this repository.

## Start here — every session

1. **Read `MEMORY.md` first.** It is the permanent project history: what is built, why, where, environment facts, gotchas, and the next lesson.
2. Read `docs/learnings.md` when you need the detail behind a lesson.

## After every lesson / feature — mandatory

1. Update `MEMORY.md`: "Last updated" line, **Lesson log**, **Current state**, **Next steps**, and the folder map / environment facts if they changed.
2. Add the new concepts to `docs/learnings.md` as the next "Learning N".
3. Do not commit or push unless the user asks; push from the user's terminal. Scan for secrets first — this repo is public and `.env` must never be committed.

## How to work with the user

- This is a **learning project**: explain every step line by line in **Roman English / Roman Urdu**, spelling out every abbreviation. When the user says "aap khud kar do", do the steps yourself and give a report.
- Code comments are one line max and explain *why*, never restate the code.
- Every model is tenant-scoped (`TenantScopedModel`) and every query filters by tenant — see `MEMORY.md` §3 and Learning 5.
