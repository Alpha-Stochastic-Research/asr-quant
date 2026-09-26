# GitHub Pages deployment

ASRQuant documentation is built with MkDocs Material and deployed through `.github/workflows/docs.yml`.

## Automatic behaviour

- A pull request that changes documentation, source code, `README.md`, `pyproject.toml`, `mkdocs.yml`, or the docs workflow runs a strict documentation build.
- A push to `main` affecting the same files runs the strict build and then deploys the generated site to GitHub Pages.
- The Python API reference is regenerated directly from the source tree by `scripts/generate_docs.py` during every build.
- The workflow can also be triggered manually with **Actions → Documentation → Run workflow**.

## One-time repository setting

For the first deployment, GitHub Pages must use **GitHub Actions** as its publishing source:

`Settings → Pages → Build and deployment → Source → GitHub Actions`

After that one-time repository setting, documentation updates are automatic. A custom domain, if desired, is configured separately in the repository's Pages settings or via the GitHub Pages API.
