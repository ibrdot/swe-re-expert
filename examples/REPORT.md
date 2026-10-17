# Demo: a reviewable source-audit lead

## Target and method

Target: [demo-project/review_me.py](demo-project/review_me.py), a deliberately small
fixture. Run `python3 scripts/swe_audit.py --root examples/demo-project --all` from
the repository root. [demo-audit.json](demo-audit.json) is actual generated output.

## What the tool observes

- One Python source file in the demo directory.
- `route_order` contains nested conditionals, a loop, and a boolean expression;
  the AST-based score ranks it above trivial helpers.
- `unused_candidate` appears only at its definition in this fixture.
- `called_helper` is invoked three times and should not be reported as low-reference.

## What this does not establish

A low reference count is not proof that a function is dead: reflection, public
APIs, framework callbacks, external consumers, and dynamic imports can all matter.
Complexity is not a security finding. This fixture demonstrates a ranking workflow,
not a vulnerability benchmark or a claim about a production project.

## Useful next step

Ask your agent to inspect the highest-ranked function, cite its source lines,
check behavior with tests, and recommend a small change only if it improves clarity.
Keep this distinction between machine-collected signals and analyst conclusions
in the final report.
