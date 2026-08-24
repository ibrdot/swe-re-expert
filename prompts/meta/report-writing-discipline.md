# Report Writing Discipline

The report is the deliverable. A bad report wastes the analysis. Here's the discipline that produces reports people act on.

## The 6 sections every report needs

1. **Verdict** (one line) — PASS / CONCERNS / FAIL / BLOCKED (or for RE: CLEAN / SUSPICIOUS / MALICIOUS / INCONCLUSIVE)
2. **Executive summary** (3-5 sentences) — what was analyzed, what was found, what to do
3. **Evidence** — verifiable artifacts (line numbers, offsets, instructions, call sites)
4. **Findings** — prioritized P0-P3, each with: problem, evidence, recommended next step
5. **Limitations** — what wasn't verified, why, what would unblock
6. **Recommended next step** — the smallest safe action for the user

Skip any of these and the report is incomplete. The reader needs all six to act.

## The "executive summary first" rule

The summary goes first, not last. Readers scan the top, decide if they care, then dive deeper.

```
# Audit Report — {{TARGET}}

**Verdict:** CONCERNS

## Executive summary

The order service has a P0 SQL injection at line 23 of user_search.py — the user-supplied
search term is concatenated directly into a query string. The same module has a P1
architecture issue: domain imports from controllers, creating a cycle. Two P2
maintainability issues in the test suite. Recommend: fix the SQLi before next release,
address the architecture in the following sprint.
```

3-4 sentences. Plain English. Verdict + headline findings + recommended action. The reader knows after this whether they need to read on.

## The "evidence table" rule

Don't bury evidence in prose. Use a table:

| # | File:Line | Code | Interpretation |
|---|-----------|------|----------------|
| 1 | user_search.py:23 | `cursor.execute(f"SELECT * FROM users WHERE name = '{q}'")` | User-controlled `q` concatenated into SQL — SQLi |
| 2 | controllers/auth.py:5 | `from domain.user import User` | Controller imports domain — wrong direction |
| 3 | tests/test_auth.py:42 | `mock_query.assert_called_with("SELECT * FROM users WHERE email = 'a@b.com'")` | Test asserts implementation, not behavior — brittle |

Tables are scannable. Prose is not. Use tables for evidence.

## The "findings table" rule

Same for findings:

| Priority | Area | Problem | Evidence | Recommended next step |
|----------|-------|---------|----------|----------------------|
| P0 | Security | SQLi in user_search | user_search.py:23 | Parameterize the query: `cursor.execute("SELECT ... WHERE name = %s", (q,))` |
| P1 | Architecture | Domain imports controllers | controllers/auth.py:5 → domain/user.py | Invert: controllers import domain, not vice versa |
| P2 | Tests | Mock too much | tests/test_auth.py:42 | Use real DB or repository; test through public API |
| P2 | Tests | No edge cases | tests/test_login.py only covers happy path | Add empty/null/unicode/concurrent tests |

Each row: severity, area, specific issue, evidence (location), bounded fix.

## The "no 'End of Report' marker" rule

End the report with the last finding's recommendation. Don't add:
- "===== End of Report ====="
- "------ Conclusion ------"
- "Report complete"

These are artificial. The last finding's recommended next step closes the document naturally.

## The "limitations" rule

List what you didn't verify:

```
## Limitations

- Static-only — didn't run integration tests; recommend running them to confirm the SQLi
  exploit doesn't fail-open due to a different code path.
- Didn't review the test/ directory for additional SQLi patterns; recommend running
  `rg "execute\(f['\"]"` across the whole repo.
- Didn't profile — the perf section is based on static analysis, not measurement.
- The architecture findings assume the team owns all modules shown; if some are owned
  by other teams, ownership ambiguity needs separate review.
```

Honest limitations build trust. Pretending you did more than you did destroys it.

## The "smallest safe next step" rule

The last section of the report is "Recommended next step":

```
## Recommended next step

1. **Immediate** (before next release): Fix the P0 SQLi at user_search.py:23.
   Estimated: 1 PR, 1 line change, 30 minutes including tests.

2. **This sprint**: Address the P1 architecture issue by inverting the domain→controller
   import. Estimated: 2 PRs (extract + invert), 1 day, reversible.

3. **Next sprint**: Address the P2 test issues — improve isolation (function-scoped
   fixtures) and add edge case tests. Estimated: 1 sprint, 3-4 PRs.

4. **Backlog**: Address the P3 style findings via `ruff` and `black` in CI.
```

Each step:
- Ordered (1, 2, 3...)
- Bounded (PR count, time estimate)
- Reversible (or noted if not)
- Prerequisite-aware (step 2 only makes sense after step 1)

## The "plain English" rule

The report should be readable by someone who isn't a senior engineer. Don't:

- Drop pattern names without explanation ("Singleton anti-pattern" — explain why)
- Use acronyms without first-use ("SAST" — define on first use)
- Assume the reader knows the codebase as well as you do

Do:
- Explain the consequence of each finding in plain English
- Use the actual code (quote it)
- Show the fix (don't just say "use parameterized queries" — show the diff)

## The "no decorative citations" rule

Cite sources that directly support the recommendation:

❌ "See OWASP Top 10 for more" — link to OWASP homepage (decorative)
✅ "See OWASP SQL Injection Prevention Cheat Sheet, section 'Use of Prepared Statements'" — link to specific section

Open the link yourself. Verify it supports the mechanism you're proposing, not just the general defect category. If it doesn't, find a better source or omit.

## The "don't pad" rule

If a section only has 1-2 findings, that's OK. Don't pad it with weak findings to make it look fuller. Quality > quantity.

A report with 3 strong P0 findings is better than a report with 3 strong P0 findings + 10 weak P3 nitpicks. The nitpicks dilute the signal.

## The "let findings speak" rule

Don't editorialize:

❌ "This is a serious issue that the team should address urgently."
✅ "P0: SQLi in user_search.py:23 — directly exploitable, allows auth bypass."

The severity (P0) and the consequence (auth bypass) tell the reader it's serious. Editorializing adds noise.

## The "be honest about uncertainty" rule

When you don't know, say so:

- "I couldn't confirm X because [reason]. Marking as SUSPECTED."
- "Y is based on a hypothesis from static signals; needs dynamic confirmation."
- "Z is BLOCKED — required evidence is unavailable. Would unblock with [action]."

Don't bluff. A reader who trusts your "high-confidence" finding and gets burned will not trust your next report.

## The "audience-aware" rule

Tailor the report:

- **Engineering team**: detailed findings, code diffs, time estimates. They'll act on it.
- **Engineering manager**: executive summary + verdict + estimated effort. They'll prioritize.
- **Security team**: full security section with OWASP mapping. They'll track it.
- **Compliance / audit**: scope confirmation + verdict + limitations. They'll file it.

Same findings, different framing. The data is the same; the emphasis changes.

## The "verifiability" rule

Every claim in the report should be checkable by the reader:

- Open the file at the line you cite → see the code you claim is there
- Disassemble at the offset you cite → see the instruction you claim is there
- Run the grep command you cite → see the same output you claim

If the reader can't verify in <5 minutes, the claim is too vague. Tighten it.

## The "use the templates" rule

Use the templates in `assets/`:
- `assets/report_code_audit.md` for code review
- `assets/report_architecture.md` for architecture audit
- `assets/report_binary_analysis.md` for RE binary analysis
- `assets/report_malware_triage.md` for malware triage

The templates enforce the structure. Deviation should be additive (extra sections for specific cases), not subtractive (skip limitations).

## The "length budget" rule

A report should be:

- **Brief review** (single PR): 1-2 pages
- **Module audit**: 3-5 pages
- **Full codebase audit**: 5-10 pages
- **Binary analysis**: 3-7 pages
- **Malware triage**: 5-10 pages

If you're way over, you're padding. If you're way under, you're missing sections.

## The "review your own report" rule

Before submitting, re-read your report as if you were the reader:

- Does the executive summary tell me what to do?
- Can I verify each finding in 5 minutes?
- Are the recommendations bounded and reversible?
- Are the limitations honest?
- Is the next step concrete?

If any answer is "no", revise.

## Output

The report is the deliverable. It should:
- Lead with the verdict
- Have a scannable executive summary
- Use tables for evidence and findings
- Have honest limitations
- End with concrete next steps
- Be verifiable by the reader in 5 minutes per finding

Without these, the report is opinion, not analysis.
