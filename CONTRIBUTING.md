# Contributing

Small, evidence-backed improvements are welcome: a broken workflow, a misleading
claim, a parser regression, a better report, or a reproducible counterexample.

## Submit a useful change

1. Open an issue explaining expected versus observed behavior.
2. Include the command, Python version, platform, and minimal fixture where possible.
3. Keep patches focused and preserve existing interfaces unless the change is explicit.
4. Add a regression test; label heuristics and platform limits honestly.
5. Run `python3 -m unittest discover -s tests -v` and `python3 -m py_compile scripts/*.py`.

Do not include credentials, private customer data, or executable samples in issue
attachments. Prefer a tiny source reproducer or descriptive metadata.

## Reports and playbooks

Cite evidence. Avoid fabricated results, unsupported compatibility claims, and
severity inflation. New references must resolve locally or link to a relevant source.

Contact: [ibrdot@outlook.com](mailto:ibrdot@outlook.com).
