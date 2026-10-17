# Initialize planning files for a new session
# Usage: .\init-session.ps1 [project-name]

param(
    [string]$ProjectName = "project"
)

$DATE = Get-Date -Format "yyyy-MM-dd"
$PlanningDir = if ($env:PLANNING_DIR) { $env:PLANNING_DIR } else { ".claude/planning" }
$PlanFile = Join-Path $PlanningDir "task_plan.md"
$FindingsFile = Join-Path $PlanningDir "findings.md"
$ProgressFile = Join-Path $PlanningDir "progress.md"

Write-Host "Initializing planning files for: $ProjectName"
New-Item -ItemType Directory -Force -Path $PlanningDir | Out-Null

# Create task_plan.md if it doesn't exist
if (-not (Test-Path $PlanFile)) {
    @"
# Task Plan: [Brief Description]

## Goal
[One sentence describing the end state]

## Current Phase
Phase 1

## Phases

### Phase 1: Requirements & Discovery
- [ ] Understand user intent
- [ ] Identify constraints
- [ ] Document in findings.md
- **Status:** in_progress

### Phase 2: Planning & Structure
- [ ] Define approach
- [ ] Create project structure
- **Status:** pending

### Phase 3: Implementation
- [ ] Execute the plan
- [ ] Write to files before executing
- **Status:** pending

### Phase 4: Testing & Verification
- [ ] Verify requirements met
- [ ] Document test results
- **Status:** pending

### Phase 5: Delivery
- [ ] Review outputs
- [ ] Deliver to user
- **Status:** pending

## Decisions Made
| Decision | Rationale |
|----------|-----------|

## Errors Encountered
| Error | Resolution |
|-------|------------|
"@ | Out-File -FilePath $PlanFile -Encoding UTF8
    Write-Host "Created $PlanFile"
} else {
    Write-Host "$PlanFile already exists, skipping"
}

# Create findings.md if it doesn't exist
if (-not (Test-Path $FindingsFile)) {
    @"
# Findings & Decisions

## Requirements
-

## Research Findings
-

## Technical Decisions
| Decision | Rationale |
|----------|-----------|

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
"@ | Out-File -FilePath $FindingsFile -Encoding UTF8
    Write-Host "Created $FindingsFile"
} else {
    Write-Host "$FindingsFile already exists, skipping"
}

# Create progress.md if it doesn't exist
if (-not (Test-Path $ProgressFile)) {
    @"
# Progress Log

## Session: $DATE

### Current Status
- **Phase:** 1 - Requirements & Discovery
- **Started:** $DATE

### Actions Taken
-

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|

### Errors
| Error | Resolution |
|-------|------------|
"@ | Out-File -FilePath $ProgressFile -Encoding UTF8
    Write-Host "Created $ProgressFile"
} else {
    Write-Host "$ProgressFile already exists, skipping"
}

Write-Host ""
Write-Host "Planning files initialized!"
Write-Host "Files: $PlanFile, $FindingsFile, $ProgressFile"
