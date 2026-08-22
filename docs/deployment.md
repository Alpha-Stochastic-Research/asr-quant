# Publish the Documentation

The repository includes `.github/workflows/docs.yml` for GitHub Pages.

## GitHub Pages

1. Push the repository to `Alpha-Stochastic-Research/asr-quant`.
2. In **Settings → Pages**, set the source to **GitHub Actions**.
3. Push a change affecting `docs/`, `src/`, `notebooks/` or `mkdocs.yml`, or run the workflow manually.
4. The workflow installs `.[docs]`, builds MkDocs in strict mode and deploys the generated `site/` artifact.

The default `site_url` is configured for the project Pages URL:

```text
https://alpha-stochastic-research.github.io/asr-quant/
```

## ASR domain

For a branded endpoint such as:

```text
https://docs.asr-lab.online/asrquant/
```

route that path from the ASR documentation host/reverse proxy to the built ASRQuant site, then update `site_url` in `mkdocs.yml` to the final public URL.

If ASRQuant is hosted as an independent GitHub Pages custom domain rather than under a shared documentation hub, a dedicated hostname such as `asrquant.asr-lab.online` is operationally simpler because GitHub Pages custom domains map to a site root rather than a nested path.
