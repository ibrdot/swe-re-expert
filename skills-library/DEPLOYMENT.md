# GitHub Pages deployment

## Existing layout

This project publishes a static site from the `docs/` directory. All local assets
use relative paths so the project URL works under `/ai-agent-skills/`.
`docs/.nojekyll` keeps publication independent of Jekyll processing.

## Admin setup

A repository admin, or a user with the required Pages permissions, should:

1. Open the repository's **Settings > Pages**.
2. Set **Source** to **Deploy from a branch**.
3. Select branch **main**, folder **/docs**, and save.
4. Open **Actions** and inspect the automatically created **pages build and deployment** run.
5. Open https://ibrdot.github.io/ai-agent-skills/ after that run succeeds.

A collaborator can prepare and push site files if permitted, but changing Pages
settings can require additional repository permissions. This update does not add
a competing deploy workflow or silently change the site's publication source.

## Local checks

```sh
python3 tools/build.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000` and `http://localhost:8000/skills.html`. Test search,
filters, reset, copying, keyboard controls, and narrow screens.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Site returns 404 | Correct branch/folder, Pages enabled, public URL, and a successful deploy |
| Old content after deploy | Published commit, deployment completion, then reload without cache |
| Search fails | `docs/data/skills.json` exists and returns JSON over HTTP |
| Missing styles | Relative `assets/style.css` path, correct case, published commit |
| Build or deploy fails | Open the exact failing run and job log; do not assume admin rights are the cause |
| API Pages endpoint returns 404 | Authenticate and check permissions; an unauthenticated 404 alone does not prove Pages is disabled |

At the initial inspection on 2026-10-17, the public homepage returned HTTP 200 and
the two latest public Pages runs were successful. That observation does not certify
any later deployment or prove which error a collaborator previously encountered.

## Automatic generation

`.github/workflows/catalogue.yml` validates every push and pull request. Only main
pushes/manual runs publish generated changes; pull requests never commit or deploy.
The workflow uses the built-in `GITHUB_TOKEN` with contents/pages write permissions,
not a personal token. Organization policy or branch protection may restrict bot
pushes; if so, an admin must allow this workflow or merge generated updates via a PR.
The workflow fails visibly rather than silently claiming publication.

After committing generated files, it requests `POST /repos/{owner}/{repo}/pages/builds`
so branch-based Pages publishes the generated commit. Keep Pages on main + /docs.
There is no competing Actions-based Pages deployment. Third-party imports are still
reviewed manually; this workflow only regenerates content already in the checkout.
