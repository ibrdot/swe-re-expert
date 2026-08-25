# Report Writing Discipline

The report is the deliverable. A bad report wastes the analysis. Here's the discipline that produces reports people act on. This is the difference between analysis that gets read and analysis that gets ignored.

---

## The Core Principle: Reports Are for Action, Not for Archiving

The sole purpose of a report is to **drive action**. Every word, every section, every finding should be designed to help the reader understand what to do next. If it doesn't help the reader act, it doesn't belong in the report.

**Good Reports**:
- Are **read** by the intended audience
- **Drive decisions** and actions
- **Build trust** in the analyst
- **Provide value** that exceeds their cost

**Bad Reports**:
- Sit on a shelf (or in a digital folder) unread
- Are ignored because they're too long, too vague, or too hard to understand
- Destroy trust because they contain errors or exaggerations
- Cost more to produce than the value they provide

**The Analyst's Mantra**: "Will this help the reader take action? If not, cut it."

---

## The 6 Sections Every Report Needs

Every report, regardless of type (code audit, binary analysis, malware triage, architecture review), must contain these 6 sections. Skip any of these and the report is incomplete.

### 1. \u2610 **Verdict** (one line)

**Purpose**: Give the reader the bottom line immediately.

**Format**: Single word or short phrase that conveys the overall assessment.

**Verdict Options**:

**For SWE (Software Engineering)**:
| Verdict | Meaning | When to Use |
|---------|---------|-------------|
| `PASS` | No significant issues found | Clean codebase, minor findings only |
| `CONCERNS` | Issues found, but not blockers | P2/P3 findings, action recommended |
| `FAIL` | Significant issues that must be addressed | P0/P1 findings, blocks release |
| `BLOCKED` | Cannot complete analysis | Missing access, information, or resources |

**For RE (Reverse Engineering)**:
| Verdict | Meaning | When to Use |
|---------|---------|-------------|
| `CLEAN` | No suspicious indicators found | Benign binary, no issues |
| `SUSPICIOUS` | Suspicious indicators, but not confirmed | Uncertain findings, needs more analysis |
| `MALICIOUS` | Confirmed malicious behavior | Clear evidence of malware |
| `INCONCLUSIVE` | Cannot determine intent | Conflicting evidence, blocked analysis |

**For Architecture Reviews**:
| Verdict | Meaning | When to Use |
|---------|---------|-------------|
| `HEALTHY` | Architecture is sound | Minor issues only |
| `DEGRADING` | Architecture has issues that will cause problems | P2 findings, needs attention |
| `CRITICAL` | Architecture has serious issues | P0/P1 findings, needs immediate action |
| `UNKNOWN` | Cannot assess architecture | Missing information |

**Placement**: The verdict goes at the **very top** of the report, before anything else.

**Examples**:
```markdown
# Code Audit Report \u2014 Payment Service

**Verdict:** FAIL

# Binary Analysis Report \u2014 sample.exe

**Verdict:** SUSPICIOUS

# Architecture Review \u2014 Order System

**Verdict:** DEGRADING
```

**Why This Matters**: Busy readers often only read the first few lines. The verdict tells them everything they need to know about the overall assessment.

---

### 2. \u2610 **Executive Summary** (3-5 sentences)

**Purpose**: Give the reader a high-level overview of what was analyzed, what was found, and what to do about it.

**Format**: 3-5 sentences, plain English, no jargon. Structure:
1. What was analyzed (scope)
2. What was found (headline findings)
3. What to do (recommended actions)

**Executive Summary Template**:
```
The [what was analyzed] was analyzed on [date] using [methodology]. 
[Headline finding 1] was discovered, which [impact]. 
Additionally, [headline finding 2] and [headline finding 3] were identified. 
Recommend: [recommended action 1], [recommended action 2], and [recommended action 3].
```

**Examples**:

**SWE Example**:
```
The order service (12K LOC, Python) was analyzed on 2024-01-15 using static analysis and manual code review. 
A P0 SQL injection vulnerability was discovered at user_search.py:23, which allows auth bypass. 
The service also has a P1 architecture issue with circular dependencies between domain and controller layers. 
Two P2 maintainability issues were found in the test suite. 
Recommend: fix the SQLi before next release, address the architecture in the following sprint, and clean up tests as time permits.
```

**RE Example**:
```
The binary sample.exe (1.2MB, PE32+) was analyzed on 2024-01-15 using static and dynamic analysis. 
SUSPECTED Emotet malware variant was identified based on mutex patterns, imports, and string signatures. 
The sample uses custom packing (not Themida or UPX) and has anti-debugging techniques. 
C2 communication uses HTTP POST to hxxp://evil[.]com/api/data. 
Recommend: submit SHA-256 to MalwareBazaar for confirmation, run in sandbox for behavioral analysis.
```

**Architecture Example**:
```
The order system architecture was reviewed on 2024-01-15 using dependency analysis and code inspection. 
P1 circular dependencies were found between the order, payment, and inventory services. 
P2 tight coupling exists between the presentation and domain layers. 
The system has P3 technical debt in the form of duplicate code and dead dependencies. 
Recommend: break circular dependencies this quarter, address layer violations next quarter.
```

**Why This Matters**: The executive summary is often the **only part** of the report that senior stakeholders read. It must contain everything they need to understand the situation and make decisions.

**Anti-Patterns**:
- \u274c Too long (>5 sentences)
- \u274c Too technical (jargon, acronyms without explanation)
- \u274c Too vague ("some issues were found")
- \u274c Buries the lead (starts with methodology instead of findings)

**Pro Tip**: Write the executive summary **last**, after you've written the rest of the report. This ensures you know exactly what the headline findings are.

---

### 3. \u2610 **Evidence** \u2014 Verifiable Artifacts

**Purpose**: Provide concrete, verifiable proof for every claim in the report.

**Format**: Use tables for scannability. Every evidence item must be:
- **Specific**: Exact location (file:line or offset)
- **Verifiable**: Reader can check it themselves
- **Relevant**: Directly supports a finding
- **Quoted**: Exact code, instruction, or string

**Evidence Table Template**:
```markdown
| # | Location | Artifact | Interpretation |
|---|----------|----------|----------------|
| 1 | user_search.py:23 | `cursor.execute(f"SELECT * FROM users WHERE name = '{q}'")` | User-controlled `q` concatenated into SQL \u2014 SQLi |
| 2 | controllers/auth.py:5 | `from domain.user import User` | Controller imports domain \u2014 layer violation |
| 3 | .text:0x401234 | `call rax ; rax = CreateRemoteThread` | Suspicious API call for code injection |
```

**Evidence Types by Report Type**:

**SWE Reports**:
- Code snippets (with file:line)
- Test output
- Build errors
- Linter warnings
- Coverage reports
- Performance metrics

**RE Reports**:
- Disassembly snippets (with offset)
- Hex dumps
- String extracts
- Import tables
- Section information
- Entropy values

**Architecture Reports**:
- Dependency graphs
- Module diagrams
- Layer violation evidence
- Coupling metrics
- Build order issues

**Evidence Requirements**:
1. **For every finding**, there must be at least one piece of evidence
2. **For P0/P1 findings**, there must be multiple pieces of evidence
3. **Evidence must be verifiable** in <5 minutes by the reader
4. **Evidence must be quoted exactly** (not paraphrased)

**Anti-Patterns**:
- \u274c "The code has a SQL injection vulnerability" (no evidence)
- \u274c "There are issues in the auth module" (vague location)
- \u274c "The binary is suspicious" (no specific evidence)
- \u274c Buried in prose (hard to find)

**Pro Tip**: Use the **"5-minute verification"** test. For each piece of evidence, ask: "Can the reader verify this in 5 minutes or less?" If not, the evidence isn't specific enough.

---

### 4. \u2610 **Findings** \u2014 Prioritized Issues

**Purpose**: Present the issues found, ordered by priority, with enough detail for the reader to understand and act on them.

**Format**: Table format for scannability. Each finding must include:
- **Priority**: P0, P1, P2, P3
- **ID**: Unique identifier for tracking
- **Issue**: Clear description of the problem
- **Location**: Specific file:line or offset
- **Evidence**: Reference to evidence section
- **Impact**: What happens if unaddressed
- **Recommendation**: Specific, bounded action to take

**Findings Table Template**:
```markdown
| Priority | ID | Issue | Location | Evidence | Impact | Recommendation |
|----------|-----|-------|----------|----------|--------|----------------|
| P0 | F-001 | SQL injection | user_search.py:23 | E-001, E-002 | Auth bypass | Parameterize query |
| P1 | F-002 | Circular dependency | domain/user.py:1, controllers/auth.py:5 | E-003 | Build/test issues | Extract interface |
| P2 | F-003 | Duplicate code | utils/dates.py:23, helpers/datetime.py:8 | E-004 | Maintenance burden | Consolidate |
```

**Finding Details**:
Each finding in the table should have a corresponding detailed section:

```markdown
### P0: SQL Injection in User Search (F-001)

**Location**: user_search.py:23

**Evidence**:
- E-001: `cursor.execute(f"SELECT * FROM users WHERE name LIKE '%{q}%'")`
- E-002: `q` is from `request.args.get('q')` at line 12

**Impact**: Allows authentication bypass via `' OR '1'='1` injection

**Risk**: Critical (CVSS 9.8, affects all users)

**Recommendation**:
```python
# Current:
cursor.execute(f"SELECT * FROM users WHERE name LIKE '%{q}%'")

# Recommended:
cursor.execute("SELECT * FROM users WHERE name LIKE %s", (f"%{q}%",))
```

**Effort**: 30 minutes
**PRs**: 1
**Tests**: Existing tests should catch; add regression test
**Rollback**: `git revert <commit-hash>`
**Dependencies**: None
**Owner**: Backend team
**Deadline**: Before next release
```

**Finding Prioritization**:
| Priority | Criteria | Examples |
|----------|----------|----------|
| P0 | Blocks release, causes data loss, security hole, crash | SQLi, auth bypass, memory leak, data corruption |
| P1 | Will cause recurring pain, correctness bug, security issue, change amplification | Race condition, missing validation, tight coupling, N+1 queries |
| P2 | Slows future work, maintainability issue, dead code in active module | Duplicate code, long methods, no tests, style violations (with team agreement) |
| P3 | Cosmetic, not worth doing now | Style preferences, minor inconsistencies, dead code in unused module |

**Finding Requirements**:
1. **Specific**: Clear what the issue is
2. **Located**: Exact file:line or offset
3. **Evidenced**: Proof that the issue exists
4. **Impactful**: Why it matters
5. **Actionable**: What to do about it
6. **Bounded**: Scoped, estimated, reversible

**Anti-Patterns**:
- \u274c Vague descriptions ("There are issues in the auth module")
- \u274c No location ("The code has a bug")
- \u274c No evidence ("Trust me, there's a problem")
- \u274c No impact ("This could be improved")
- \u274c No recommendation ("This is bad")
- \u274c Unbounded ("Refactor the architecture")

**Pro Tip**: Use the **"So what?"** test. After describing a finding, ask: "So what? Why should the reader care?" If you can't answer clearly, the finding isn't ready.

---

### 5. \u2610 **Limitations** \u2014 What Wasn't Verified

**Purpose**: Be honest about what you didn't do, couldn't verify, or couldn't access. This builds trust and helps the reader understand the confidence level of your findings.

**Format**: Structured list of limitations, grouped by category.

**Limitations Template**:
```markdown
## Limitations

This analysis was based on:
- [X] Static analysis of the code/binary
- [ ] Dynamic analysis in a sandbox
- [ ] Dynamic analysis in a full VM
- [ ] Manual code review
- [ ] Automated scanning

This analysis did NOT include:
- Dynamic behavior verification (no execution environment provided)
- Full codebase review (only critical paths analyzed)
- Dependency analysis (external libraries not reviewed)
- Production environment testing (only staging tested)

**Access Limitations**:
- No access to production environment
- No access to database schema
- No access to third-party service configurations
- No access to mobile app source code

**Methodology Limitations**:
- Static analysis only (no dynamic verification)
- Automated scanning only (no manual review)
- Sample analysis only (no full codebase review)
- No threat intelligence lookup (SHA-256 not submitted to VirusTotal)

**Assumptions Made**:
1. The code/binary provided is the production version
2. No additional input validation exists upstream
3. The analysis environment is representative of production
4. No compensating controls exist for identified vulnerabilities

**Impact on Findings**:
- Security findings may miss upstream mitigations
- Performance findings may not reflect production behavior
- Architecture findings may not account for all constraints
- Binary analysis findings are based on static analysis only

**To Strengthen This Analysis**:
1. Provide a dynamic analysis environment
2. Grant access to the full codebase
3. Provide production configuration details
4. Share any available threat intelligence
5. Run dynamic analysis in instrumented sandbox
```

**Why This Matters**:
- **Builds Trust**: Shows you're honest about your limitations
- **Sets Expectations**: Helps the reader understand what to trust
- **Guides Next Steps**: Shows what additional work could strengthen the analysis
- **Protects You**: Provides context if a finding turns out to be wrong

**Anti-Patterns**:
- \u274c Omitting limitations entirely
- \u274c Vague limitations ("Some things weren't checked")
- \u274c Buried limitations (in a footnote or appendix)
- \u274c Overstating limitations (to excuse poor analysis)

**Pro Tip**: The limitations section is your **"get out of jail free"** card. If a finding turns out to be wrong, you can point to the limitations that prevented you from catching it. But this only works if the limitations are **honest and comprehensive**.

---

### 6. \u2610 **Recommended Next Step** \u2014 The Smallest Safe Action

**Purpose**: Tell the reader exactly what to do next, in priority order.

**Format**: Ordered list of actions, each with:
- **Priority**: 1, 2, 3... (ordered by importance)
- **Action**: What to do
- **Scope**: What's involved
- **Effort**: Time estimate
- **Owner**: Who should do it
- **Deadline**: When it should be done
- **Dependencies**: What must be done first

**Recommended Next Step Template**:
```markdown
## Recommended Next Steps

### Immediate (Before Next Release)
1. **Fix P0 SQL injection**
   - **Action**: Parameterize query at user_search.py:23
   - **Scope**: 1 file, 1 line change
   - **Effort**: 30 minutes
   - **Owner**: Backend team
   - **Deadline**: EOD Tuesday
   - **Dependencies**: None
   - **Rollback**: `git revert <commit-hash>`

2. **Deploy hotfix**
   - **Action**: Deploy the SQLi fix to production
   - **Scope**: 1 commit
   - **Effort**: 15 minutes
   - **Owner**: DevOps team
   - **Deadline**: EOD Tuesday
   - **Dependencies**: PR #123 must be merged

### This Sprint (Week 1-2)
1. **Fix P1 circular dependencies**
   - **Action**: Extract interfaces to break cycles
   - **Scope**: 3 files, 2 PRs
   - **Effort**: 4 hours
   - **Owner**: Backend team
   - **Deadline**: EOD Friday Week 1
   - **Dependencies**: None

2. **Add tests for auth flow**
   - **Action**: Add characterization tests
   - **Scope**: 1 module, 1 PR
   - **Effort**: 2 hours
   - **Owner**: QA team
   - **Deadline**: EOD Wednesday Week 2
   - **Dependencies**: None

### Next Sprint (Week 3-4)
1. **Address P2 maintainability issues**
   - **Action**: Consolidate duplicate code
   - **Scope**: 2 files, 1 PR
   - **Effort**: 2 hours
   - **Owner**: Backend team
   - **Deadline**: EOD Friday Week 3
   - **Dependencies**: None

### Backlog
1. **P3 cleanup tasks**
   - Remove dead code
   - Fix style violations
   - Update documentation
   - **Effort**: 4 hours total
   - **Owner**: Backend team
   - **Deadline**: As capacity allows
```

**Next Step Requirements**:
1. **Ordered**: By priority and dependencies
2. **Specific**: Clear what to do
3. **Bounded**: Scoped, estimated
4. **Owned**: Someone is responsible
5. **Timed**: Has a deadline
6. **Actionable**: Reader knows exactly what to do

**Anti-Patterns**:
- \u274c Vague actions ("Improve the code")
- \u274c Unordered list (no priorities)
- \u274c No estimates ("Fix the issues")
- \u274c No owners ("Someone should do this")
- \u274c Unrealistic deadlines

**Pro Tip**: The recommended next step is the **most important section** of the report for driving action. Make it as easy as possible for the reader to understand what to do next.

---

## The Report Writing Process

Follow this process to produce a high-quality report:

### Step 1: Draft the Findings
Write the findings as they come to you, without worrying about structure or polish. Get all your thoughts down.

### Step 2: Organize by Priority
Group findings by priority (P0, P1, P2, P3). Within each priority, order by impact and ease.

### Step 3: Apply the Evidence Checklist
For each finding, verify it meets all 12 points of the evidence checklist:
1. Specific location
2. Verifiable artifact
3. Concrete consequence
4. Reproducible command
5. No decorative citations
6. No hedging
7. Consequence first
8. Before/after where applicable
9. Filter applied (materiality gate)
10. Acceptable alternative considered
11. Bounded recommendation
12. Uncertainty marked

### Step 4: Write the Evidence Section
Extract all evidence from findings and put it in the evidence section. Use tables for scannability.

### Step 5: Write the Findings Section
Write detailed descriptions for each finding. Use the findings table template.

### Step 6: Write the Executive Summary
Summarize the headline findings in 3-5 sentences. Write this last, after you know what the findings are.

### Step 7: Write the Limitations Section
Document what you didn't verify, couldn't access, or didn't do. Be honest and specific.

### Step 8: Write the Recommended Next Steps
Create an ordered list of actions. Make each action specific, bounded, and actionable.

### Step 9: Add the Verdict
Choose the single word or phrase that best describes the overall assessment.

### Step 10: Review and Polish
Review the entire report for:
- Clarity: Is it easy to understand?
- Conciseness: Is it as short as possible?
- Completeness: Does it have all 6 required sections?
- Correctness: Are all facts accurate?
- Actionability: Does it drive action?

---

## Report Types and Their Specific Requirements

### 1. Code Audit Reports

**Purpose**: Assess the quality, security, and maintainability of a codebase.

**Audience**: Developers, engineering managers, security teams

**Specific Requirements**:
- Include code snippets for all findings
- Reference specific files and line numbers
- Include test coverage information
- Document build and dependency information
- Assess code quality metrics (complexity, duplication, etc.)

**Template**:
```markdown
# Code Audit Report \u2014 [Project Name]

**Verdict:** [PASS/CONCERNS/FAIL/BLOCKED]

## Executive Summary
[3-5 sentences]

## Scope
- **Repository**: [repo URL]
- **Branch/Commit**: [branch/commit hash]
- **Files Analyzed**: [number]
- **LOC Analyzed**: [number]
- **Languages**: [list]
- **Analysis Date**: [date]
- **Analyst**: [name]

## Evidence
[Evidence table]

## Findings
[Findings table and details]

## Code Quality Metrics
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Test Coverage | 75% | 80% | \u274c Below target |
| Cyclomatic Complexity | 12 | <10 | \u274c Above target |
| Code Duplication | 5% | <3% | \u274c Above target |
| Security Issues | 2 | 0 | \u274c Above target |

## Limitations
[Limitations]

## Recommended Next Steps
[Ordered list of actions]

## Appendices
- Full file list
- Dependency graph
- Test coverage report
- Complexity report
```

---

### 2. Binary Analysis Reports

**Purpose**: Analyze a binary to understand its behavior, detect malware, or find vulnerabilities.

**Audience**: Security analysts, malware researchers, incident responders

**Specific Requirements**:
- Include binary metadata (type, size, hash, compile timestamp)
- Document all analysis methods used (static, dynamic)
- Include disassembly snippets for key findings
- Document imports, exports, sections
- Include string analysis
- Document entropy analysis

**Template**:
```markdown
# Binary Analysis Report \u2014 [Sample Name]

**Verdict:** [CLEAN/SUSPICIOUS/MALICIOUS/INCONCLUSIVE]

## Executive Summary
[3-5 sentences]

## Binary Metadata
| Property | Value |
|----------|-------|
| File Name | sample.exe |
| File Size | 1.2 MB |
| File Type | PE32+ executable |
| SHA-256 | a1b2c3d4e5f6... |
| MD5 | 1a2b3c4d5e6f... |
| Compile Timestamp | 2024-01-15 10:30:45 UTC |
| Entry Point | 0x401000 |
| Sections | .text, .data, .rdata, .pdata, .reloc |

## Analysis Methods
- [X] Static analysis (strings, imports, entropy)
- [X] Disassembly (IDA Pro, Ghidra, objdump)
- [ ] Dynamic analysis (sandbox, debugger)
- [ ] Memory analysis (Volatility, Rekall)
- [ ] Behavioral analysis (Cuckoo, Joe Sandbox)

## Evidence
[Evidence table with offsets, disassembly, strings]

## Findings
[Findings table and details]

## Indicators of Compromise (IOCs)
| Type | Value | Confidence | Source |
|------|-------|------------|--------|
| SHA-256 | a1b2c3... | CONFIRMED | This analysis |
| IP | 192.0.2.1 | SUSPECTED | C2 communication |
| Domain | evil[.]com | SUSPECTED | C2 communication |
| Mutex | Global\Lumma_v2 | SUSPECTED | Static analysis |

## Limitations
[Limitations]

## Recommended Next Steps
[Ordered list of actions]

## Appendices
- Full import list
- Full string list
- Section details
- Disassembly of key functions
```

---

### 3. Malware Triage Reports

**Purpose**: Quickly assess whether a sample is malicious and what its capabilities are.

**Audience**: SOC analysts, incident responders, threat hunters

**Specific Requirements**:
- Fast turnaround (typically <2 hours)
- Focus on key behaviors (persistence, C2, data exfiltration)
- Include IOCs for detection
- Assess severity and urgency
- Provide containment recommendations

**Template**:
```markdown
# Malware Triage Report \u2014 [Sample Name]

**Verdict:** [CLEAN/SUSPICIOUS/MALICIOUS/INCONCLUSIVE]
**Severity:** [Low/Medium/High/Critical]
**Urgency:** [Low/Medium/High/Critical]

## Executive Summary
[3-5 sentences with key behaviors and recommendations]

## Sample Information
| Property | Value |
|----------|-------|
| Sample Name | malicious.doc |
| Sample Size | 2.3 MB |
| Sample Type | Microsoft Word document |
| SHA-256 | a1b2c3d4e5f6... |
| MD5 | 1a2b3c4d5e6f... |
| Submission Date | 2024-01-15 14:30:00 UTC |
| Submitted By | user@example.com |

## Analysis Methods
- [X] Static analysis (PEiD, file, strings)
- [X] YARA scanning
- [X] Hash lookup (VirusTotal, MalwareBazaar)
- [ ] Dynamic analysis (sandbox)
- [ ] Memory analysis

## Key Findings
| Category | Finding | Confidence | Evidence |
|----------|---------|------------|----------|
| File Type | DOCM (macro-enabled) | CONFIRMED | file command |
| Packing | None detected | VERIFIED | PEiD scan |
| Family | SUSPECTED Emotet | SUSPECTED | Mutex, strings, imports |
| C2 | hxxp://evil[.]com/api/data | CONFIRMED | Static analysis |
| Persistence | Registry Run key | CONFIRMED | Static analysis |
| Capabilities | Data exfiltration | SUSPECTED | String analysis |

## Indicators of Compromise (IOCs)
[IOC table]

## Behavior Summary
- **Initial Access**: Malicious macro in DOCM file
- **Persistence**: Adds Registry Run key for persistence
- **C2 Communication**: HTTP POST to hxxp://evil[.]com/api/data
- **Data Collection**: Enumerates browser data, Outlook contacts
- **Exfiltration**: Sends collected data to C2 server

## Severity Assessment
**Overall Severity**: High

| Factor | Value | Contribution |
|--------|-------|--------------|
| Family | Emotet (known malware) | High |
| Capabilities | Data exfiltration | High |
| Persistence | Registry Run key | Medium |
| C2 | Active | High |
| Prevalence | Widespread | Medium |

## Containment Recommendations
1. **Immediate**: Isolate the system where the sample was found
2. **Short-term**: Block IOCs at firewall and EDR
3. **Long-term**: Hunt for additional infections in the environment

## Limitations
[Limitations]

## Recommended Next Steps
[Ordered list of actions]
```

---

### 4. Architecture Review Reports

**Purpose**: Assess the health of a system's architecture and identify improvement opportunities.

**Audience**: Architects, engineering managers, CTO

**Specific Requirements**:
- Focus on system-level issues
- Include dependency graphs
- Assess coupling and cohesion
- Evaluate scalability and maintainability
- Provide migration paths for big changes

**Template**:
```markdown
# Architecture Review Report \u2014 [System Name]

**Verdict:** [HEALTHY/DEGRADING/CRITICAL/UNKNOWN]

## Executive Summary
[3-5 sentences]

## System Overview
- **System Name**: Order System
- **Purpose**: Process customer orders
- **Scale**: 10K requests/day, 100K users
- **Team Size**: 8 developers
- **Tech Stack**: Python, Django, PostgreSQL, Redis
- **Deployment**: Kubernetes on AWS

## Architecture Diagram
[ASCII or image of architecture]

## Dependency Analysis
### Dependency Graph
[Graph visualization or description]

### Coupling Metrics
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Average Fan-out | 7.3 | <5 | \u274c Above target |
| Max Fan-out | 23 | <10 | \u274c Above target |
| Cycles | 3 | 0 | \u274c Above target |
| Instability | 0.61 | <0.5 | \u274c Above target |

### Layer Violations
[Layer violation table]

## Findings
[Findings table and details]

## Migration Plans
### Migration: Extract Domain Layer
- **Goal**: Separate domain logic from application logic
- **Timeline**: 2 sprints
- **Steps**: [Ordered list of steps]
- **Rollback**: [Rollback plan]

## Limitations
[Limitations]

## Recommended Next Steps
[Ordered list of actions]

## Appendices
- Full dependency graph
- Module inventory
- Coupling metrics by module
```

---

## The "plain English" rule

The report should be readable by someone who isn't a senior engineer in your specific domain. Don't:

**Avoid These**:
| Don't | Why | Instead |
|-------|-----|---------|
| Drop pattern names without explanation | "Singleton anti-pattern" doesn't explain the problem | "Singleton anti-pattern: Creates global state that makes testing difficult and hides dependencies" |
| Use acronyms without first-use | "Use SAST" | "Use Static Application Security Testing (SAST)" |
| Assume the reader knows the codebase | "The user service has issues" | "The user service (src/services/user.py) has issues" |
| Use jargon without explanation | "The code has high cyclomatic complexity" | "The code has high cyclomatic complexity (a measure of code complexity that makes it hard to understand and test)" |
| Use vague language | "This could be a problem" | "This is a SQL injection vulnerability that allows auth bypass" |

**Write for Your Audience**:
- **Engineering team**: Detailed findings, code diffs, time estimates
- **Engineering manager**: Executive summary + verdict + estimated effort
- **Security team**: Full security section with OWASP mapping
- **Compliance / audit**: Scope confirmation + verdict + limitations
- **Executives**: Executive summary only (1 page max)

**Tailor the Report**:
Same findings, different framing. The data is the same; the emphasis changes.

**Example for Different Audiences**:

**Engineering Team**:
```
P0: SQL injection at user_search.py:23

Location: src/services/user_search.py:23
Evidence: cursor.execute(f"SELECT * FROM users WHERE name LIKE '%{q}%'")
Impact: Allows authentication bypass via ' OR '1'='1
Fix: Parameterize the query
Effort: 30 minutes
PR: 1
Tests: Add regression test
```

**Engineering Manager**:
```
P0: Critical security vulnerability in user search

Risk: Authentication bypass affecting all users
Impact: Complete system compromise possible
Fix: 30-minute code change + deployment
Effort: 1 developer-hour
Urgency: Must fix before next release
```

**Security Team**:
```
P0: SQL Injection (CWE-89) in user search endpoint

Vector: User-controlled input concatenated into SQL query
Impact: Authentication bypass (CVSS 9.8)
Evidence: user_search.py:23, q from request.args.get('q')
Fix: Use parameterized queries (OWASP A1:2021)
Compliance: Violates PCI-DSS requirement 6.5.1
```

**Compliance Team**:
```
Finding: SQL Injection vulnerability in user search

Standard: PCI-DSS requirement 6.5.1
Requirement: Inject flaws, particularly SQL injection, must be addressed
Status: Non-compliant
Remediation: Parameterize queries
Deadline: Before next PCI assessment
```

**Pro Tip**: When in doubt, write for the **least technical** member of your audience. If they can understand it, everyone else will too.

---

## The "don't pad" rule

If a section only has 1-2 findings, that's OK. Don't pad it with weak findings to make it look fuller. Quality > quantity.

**Bad**: Adding 10 P3 findings to make the report look comprehensive
**Good**: Reporting 3 strong P0/P1 findings, even if the report is short

**The 80/20 Rule of Reports**:
- 20% of findings will provide 80% of the value
- Focus on making those 20% **bulletproof**
- The other 80% should meet the minimum standard
- Cut the bottom 20% that can't meet the standard

**Report Length Guidelines**:
| Report Type | Ideal Length | Maximum Length |
|-------------|--------------|----------------|
| Brief review (single PR) | 1-2 pages | 3 pages |
| Module audit | 3-5 pages | 7 pages |
| Full codebase audit | 5-10 pages | 15 pages |
| Binary analysis | 3-7 pages | 10 pages |
| Malware triage | 2-5 pages | 7 pages |
| Architecture review | 5-10 pages | 15 pages |

**Pro Tip**: If your report is longer than the maximum, you're either:
1. Including too many low-priority findings
2. Being too verbose in your descriptions
3. Including unnecessary appendices

Cut it down. The reader's time is valuable.

---

## The "let findings speak" rule

Don't editorialize. Let the findings speak for themselves.

**Bad**:
- \u274c "This is a serious issue that the team should address urgently."
- \u274c "This is a critical security vulnerability that could lead to catastrophic data loss."
- \u274c "The code quality is very poor and needs significant improvement."

**Good**:
- \u2705 "P0: SQLi in user_search.py:23 \u2014 directly exploitable, allows auth bypass."
- \u2705 "P0: Memory leak in data_processor.py:101 \u2014 causes OOM under load, affects all users."
- \u2705 "P1: Circular dependency between domain and controllers \u2014 blocks testing, causes build issues."

**Why**: The severity (P0) and the consequence (auth bypass, OOM) tell the reader it's serious. Editorializing adds noise and can sound alarmist.

**Pro Tip**: Use the **"Show, don't tell"** principle. Instead of saying "this is serious", show why it's serious through the impact description.

---

## The "be honest about uncertainty" rule

When you don't know, say so. Be explicit about uncertainty.

**How to Express Uncertainty**:
- Use uncertainty markers: HYPOTHESIS, SUSPECTED, UNVERIFIED, BLOCKED, INCONCLUSIVE
- State what you don't know
- Explain what would resolve the uncertainty
- Provide confidence levels where appropriate

**Examples**:

**Bad**:
- \u274c "This is probably malware."
- \u274c "There might be a vulnerability here."
- \u274c "I think this function has a bug."

**Good**:
- \u2705 "SUSPECTED: Emotet malware variant. Evidence: Mutex matches, 7/9 C2 patterns. To confirm: Submit to MalwareBazaar."
- \u2705 "HYPOTHESIS: Buffer overflow in parse_input.c:47. Evidence: `strcpy(dst, src)` with unbounded `src`. To confirm: Test with input > 15 bytes."
- \u2705 "UNVERIFIED: Function at 0x401234 is AES decryption. To verify: Need dynamic analysis environment."

**Why This Matters**:
- **Builds Trust**: Shows you're honest about your limitations
- **Sets Expectations**: Helps the reader understand confidence levels
- **Guides Action**: Tells the reader what to do to resolve uncertainty
- **Protects You**: Provides context if your assessment turns out to be wrong

**Pro Tip**: The **worst sin** in report writing is **false confidence** \u2014 presenting uncertain findings as fact. This destroys credibility faster than anything else.

---

## The "audience-aware" rule

Tailor the report to your audience. The same findings can be presented differently for different stakeholders.

**Audience Types and Their Needs**:

| Audience | Needs | Focus | Depth |
|----------|-------|-------|-------|
| Developers | Detailed technical information | Code, tests, fixes | Deep |
| Engineering Managers | High-level overview, priorities, effort | Executive summary, priorities, estimates | Medium |
| Security Team | Security-specific details | Vulnerabilities, risks, compliance | Medium |
| Compliance Team | Compliance status, remediation | Standards, requirements, deadlines | Medium |
| Executives | Business impact, risk, recommendations | Verdict, executive summary, recommendations | Shallow |
| Incident Responders | Immediate actions, containment | IOCs, containment, urgency | Medium |
| Threat Hunters | Indicators, patterns, behaviors | IOCs, TTPs, detection | Deep |

**Tailoring Techniques**:

**1. Adjust the Depth**:
- **Executives**: 1-page summary with verdict, executive summary, and recommended actions
- **Managers**: 2-3 page summary with findings table and next steps
- **Technical Staff**: Full report with all details

**2. Adjust the Language**:
- **Executives**: Business language, avoid technical jargon
- **Managers**: Technical but high-level, focus on impact and effort
- **Technical Staff**: Detailed technical language, include code snippets

**3. Adjust the Focus**:
- **Executives**: Business impact, risk, ROI
- **Managers**: Team impact, priorities, resource allocation
- **Developers**: Technical details, code changes, testing
- **Security**: Vulnerabilities, threats, compliance
- **Compliance**: Standards, requirements, deadlines

**4. Adjust the Format**:
- **Executives**: PowerPoint or 1-page PDF
- **Managers**: Short PDF or markdown
- **Technical Staff**: Full markdown or HTML report

**Pro Tip**: When in doubt, provide **multiple versions** of the report:
- 1-page executive summary
- 3-page manager summary
- Full technical report

This ensures everyone gets what they need without overwhelming them.

---

## The "verifiability" rule

Every claim in the report should be checkable by the reader in <5 minutes.

**Verifiability Requirements**:
1. **Specific Location**: Exact file:line or offset
2. **Quoted Evidence**: Exact code, instruction, or string
3. **Reproducible Command**: Command the reader can run to verify
4. **Clear Interpretation**: What the evidence means

**Verification Test**:
For each claim, ask: "Can the reader verify this in 5 minutes or less?"
- If yes \u2192 Good
- If no \u2192 The claim is too vague or needs more detail

**Examples**:

**Bad (Not Verifiable)**:
- \u274c "The auth module has a vulnerability."
- \u274c "There are issues in the user service."
- \u274c "The binary is suspicious."

**Good (Verifiable)**:
- \u2705 "user_search.py:23 has `cursor.execute(f\"SELECT * FROM users WHERE name = '{q}'\")` where `q` is from `request.args.get('q')` at line 12."
- \u2705 ".text:0x401234 contains `call rax ; rax = CreateRemoteThread from IAT`"
- \u2705 "Run `rg \"execute\\(f['\\\"]\" --type py src/` to find all SQL injection patterns."

**Pro Tip**: Always include **reproducible commands** with expected output. This makes verification trivial for the reader.

---

## The "use the templates" rule

Use the templates in `assets/` to ensure consistency and completeness:

| Report Type | Template | When to Use |
|-------------|----------|-------------|
| Code Audit | `assets/report_code_audit.md` | Full codebase audits |
| Binary Analysis | `assets/report_binary_analysis.md` | Binary RE analysis |
| Malware Triage | `assets/report_malware_triage.md` | Quick malware assessment |
| Architecture Review | `assets/report_architecture.md` | System architecture analysis |

**Template Benefits**:
- **Consistency**: All reports have the same structure
- **Completeness**: Won't forget important sections
- **Quality**: Follows best practices
- **Efficiency**: Don't have to start from scratch each time

**Customizing Templates**:
- **Add sections** for specific needs (e.g., "Compliance" section for PCI audits)
- **Remove sections** only if they don't apply (rare)
- **Modify sections** to fit your specific analysis

**Pro Tip**: Keep the templates **up to date** based on feedback and lessons learned from each report.

---

## The "length budget" rule

Set a length budget for your report and stick to it. Long reports don't get read.

**Length Guidelines**:
| Report Type | Ideal Length | Maximum Length | Typical Reading Time |
|-------------|--------------|----------------|---------------------|
| Brief review (single PR) | 1-2 pages | 3 pages | 5-10 minutes |
| Module audit | 3-5 pages | 7 pages | 10-20 minutes |
| Full codebase audit | 5-10 pages | 15 pages | 20-40 minutes |
| Binary analysis | 3-7 pages | 10 pages | 15-30 minutes |
| Malware triage | 2-5 pages | 7 pages | 10-20 minutes |
| Architecture review | 5-10 pages | 15 pages | 20-40 minutes |

**How to Stay Within Budget**:
1. **Prioritize Ruthlessly**: Only include high-value findings
2. **Be Concise**: Say what needs to be said, then stop
3. **Use Tables**: Tables are more information-dense than prose
4. **Use Appendices**: Move detailed data to appendices
5. **Cut Weak Findings**: If a finding doesn't meet the standard, cut it

**Pro Tip**: Use the **"Would I read this if I were the audience?"** test. If you wouldn't read it, they won't either.

---

## The "review your own report" rule

Before submitting, re-read your report as if you were the reader. Ask yourself:

1. **Does the executive summary tell me what to do?**
   - If no \u2192 Rewrite the executive summary
2. **Can I verify each finding in 5 minutes?**
   - If no \u2192 Add more specific evidence
3. **Are the recommendations bounded and reversible?**
   - If no \u2192 Add scope, estimates, rollback plans
4. **Are the limitations honest?**
   - If no \u2192 Be more honest about what you didn't do
5. **Is the next step concrete?**
   - If no \u2192 Make the next steps more specific
6. **Is the report easy to scan?**
   - If no \u2192 Add more headings, tables, bullet points
7. **Is the report free of errors?**
   - If no \u2192 Fix all typos, factual errors, broken links

**The Final Checklist**:
- [ ] Verdict is clear and prominent
- [ ] Executive summary is 3-5 sentences
- [ ] All findings have specific locations
- [ ] All findings have verifiable evidence
- [ ] All findings have concrete impact
- [ ] All findings have actionable recommendations
- [ ] Limitations are documented
- [ ] Next steps are ordered and concrete
- [ ] Report is within length budget
- [ ] Report is free of errors
- [ ] Report uses plain English
- [ ] Report is tailored to audience

**Pro Tip**: Have someone else review your report before submitting. Fresh eyes catch things you miss.

---

## Common Report Writing Mistakes and How to Fix Them

### Mistake 1: Burying the Lead

**Problem**: Starting with methodology or background instead of findings.

**Bad**:
```
This report documents the findings from a code audit of the payment service. The audit was conducted on January 15, 2024, using static analysis and manual code review. The payment service is a critical component of our system...
[3 paragraphs of background]
...finally mentions the SQL injection on page 3
```

**Good**:
```
# Code Audit Report \u2014 Payment Service

**Verdict:** FAIL

## Executive Summary

The payment service has a P0 SQL injection vulnerability at line 42 of process_payment.py that allows arbitrary amount manipulation. This audit was conducted on January 15, 2024...
```

**Fix**: Start with the verdict and headline findings. Background can come later.

---

### Mistake 2: Too Much Background

**Problem**: Including pages of background information that the reader already knows.

**Bad**:
```
## Background

The payment service was created in 2018 to handle credit card processing. It was originally written in Python 2.7 and migrated to Python 3.8 in 2020. The service uses Django 2.2 and PostgreSQL 11. The service handles approximately 10,000 transactions per day...
[2 pages of background]
```

**Good**:
```
## Background

The payment service (Python 3.8, Django 2.2, PostgreSQL 11) handles ~10K transactions/day.
```

**Fix**: Only include background that's **essential** for understanding the findings. Assume the reader knows the basics.

---

### Mistake 3: Vague Findings

**Problem**: Findings that are too vague to act on.

**Bad**:
```
| Priority | Issue | Location | Recommendation |
|----------|-------|----------|----------------|
| P1 | Code quality issues | Various files | Improve code quality |
```

**Good**:
```
| Priority | Issue | Location | Recommendation |
|----------|-------|----------|----------------|
| P1 | SQL injection | user_search.py:23 | Parameterize query |
| P1 | Circular dependency | domain/user.py:1, controllers/auth.py:5 | Extract interface |
```

**Fix**: Be **specific** about what the issue is, where it is, and what to do about it.

---

### Mistake 4: No Evidence

**Problem**: Findings with no supporting evidence.

**Bad**:
```
P0: The auth module has a critical vulnerability.
```

**Good**:
```
P0: SQL injection in auth/login.py:45

Evidence:
- E-001: `cursor.execute(f"SELECT * FROM users WHERE email = '{email}' AND password = '{password}'")`
- E-002: `email` and `password` are from `request.form` at lines 42-43
- E-003: Verified with `' OR '1'='1` -- ' OR '1'='1` payload
```

**Fix**: Include **verifiable evidence** for every finding.

---

### Mistake 5: Too Long

**Problem**: Reports that are so long that no one reads them.

**Bad**: 50-page report with every possible finding, no matter how minor.

**Good**: 8-page report with 10 strong findings, well-prioritized.

**Fix**: 
1. Cut weak findings
2. Be concise
3. Use tables
4. Move details to appendices

---

### Mistake 6: No Priorities

**Problem**: Findings presented in no particular order.

**Bad**:
```
## Findings

1. Unused import in utils.py:5
2. SQL injection in auth.py:23
3. Missing tests in services.py
4. Circular dependency between A and B
```

**Good**:
```
## Findings

### P0 (Critical)
1. SQL injection in auth.py:23

### P1 (High)
1. Circular dependency between A and B
2. Missing tests in services.py

### P3 (Low)
1. Unused import in utils.py:5
```

**Fix**: **Always order findings by priority** (P0, P1, P2, P3).

---

### Mistake 7: No Next Steps

**Problem**: Report ends with findings but no guidance on what to do next.

**Bad**:
```
## Findings

... (list of findings)

## Conclusion

This concludes the report.
```

**Good**:
```
## Findings

... (list of findings)

## Recommended Next Steps

1. Fix P0 SQL injection before next release
2. Address P1 circular dependencies this sprint
3. Clean up P3 issues as time permits
```

**Fix**: Always include **concrete next steps** with owners and deadlines.

---

### Mistake 8: Overusing Jargon

**Problem**: Using technical jargon that the audience doesn't understand.

**Bad**:
```
The system has a high cyclomatic complexity and low cohesion, leading to tight coupling and poor separation of concerns.
```

**Good**:
```
The system has complex functions that are hard to understand and test. The modules are tightly connected, making changes risky and hard to test in isolation.
```

**Fix**: Explain technical terms or use plain English alternatives.

---

### Mistake 9: Editorializing

**Problem**: Adding opinion or emphasis that doesn't add value.

**Bad**:
```
This is a VERY SERIOUS issue that the team MUST address URGENTLY. The consequences could be CATASTROPHIC.
```

**Good**:
```
P0: SQL injection allows authentication bypass. Fix before next release.
```

**Fix**: Let the **facts** speak for themselves. The priority (P0) and impact (auth bypass) convey the seriousness.

---

### Mistake 10: Inconsistent Formatting

**Problem**: Inconsistent headings, tables, or formatting that makes the report hard to read.

**Bad**:
```
# Findings

## P0 Findings

### SQL injection

Location: user_search.py:23

# P1 Findings

Circular dependency
- location: domain/user.py
```

**Good**:
```
# Findings

## P0 (Critical)

### F-001: SQL Injection
**Location**: user_search.py:23
**Impact**: Authentication bypass
**Recommendation**: Parameterize query

## P1 (High)

### F-002: Circular Dependency
**Location**: domain/user.py:1, controllers/auth.py:5
**Impact**: Build and test issues
**Recommendation**: Extract interface
```

**Fix**: Use **consistent formatting** throughout the report.

---

## Output

The report is the deliverable. It should:
- Lead with the verdict
- Have a scannable executive summary
- Use tables for evidence and findings
- Have honest limitations
- End with concrete next steps
- Be verifiable by the reader in 5 minutes per finding

Without these, the report is opinion, not analysis.

**Remember**: The best report is one that **gets read and acted on**. Everything else is secondary.

**Final Checklist Before Publishing**:
1. [ ] Does the report have all 6 required sections?
2. [ ] Is the verdict clear and prominent?
3. [ ] Is the executive summary 3-5 sentences?
4. [ ] Are all findings specific and verifiable?
5. [ ] Are all findings prioritized?
6. [ ] Are all recommendations bounded and actionable?
7. [ ] Are limitations documented?
8. [ ] Are next steps concrete?
9. [ ] Is the report within length budget?
10. [ ] Is the report free of errors?

**When in doubt, cut it out.**

The value of a report is in its **impact**, not its length. A short report with 3 strong, actionable findings is better than a long report with 20 weak, vague findings.
