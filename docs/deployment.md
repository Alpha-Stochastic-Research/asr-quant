# Publish the Documentation

ASRQuant uses GitHub Pages with a custom GitHub Actions workflow. The public documentation endpoint is:

```text
https://docs.asr-lab.online/asrquant/
```

The generated Pages artifact has a small root page at `docs.asr-lab.online/` that redirects to `/asrquant/`.

## Repository configuration

The documentation source stays inside the official repository:

```text
Alpha-Stochastic-Research/asr-quant
```

No separate ASRQuant documentation repository is required.

In **GitHub → asr-quant → Settings → Pages**:

1. Set **Source** to **GitHub Actions**.
2. Under **Custom domain**, enter:

```text
docs.asr-lab.online
```

3. Save the custom domain.
4. After DNS is valid and the certificate is issued, enable **Enforce HTTPS**.

GitHub Pages custom domains used with a custom Actions workflow are configured in repository settings; a repository `CNAME` file is not required.

## DNS configuration

At the DNS provider for `asr-lab.online`, create this record:

```text
Type:   CNAME
Name:   docs
Target: alpha-stochastic-research.github.io
```

Do not put `/asrquant/` in the DNS target. DNS resolves only the hostname. The GitHub Actions artifact provides the `/asrquant/` path.

## Deployment workflow

`.github/workflows/docs.yml` performs the following steps whenever documentation-related files change on `main`:

1. checks out the repository;
2. validates the official notebook's Markdown mathematics;
3. installs the documentation dependencies;
4. runs MkDocs in strict mode;
5. builds the MkDocs site into `site-root/asrquant/`;
6. creates a root redirect from `/` to `/asrquant/`;
7. uploads the full `site-root/` artifact to GitHub Pages.

The MkDocs canonical site URL is:

```text
https://docs.asr-lab.online/asrquant/
```

## Local preview

For the normal MkDocs development server:

```bash
python -m pip install -e ".[docs]"
mkdocs serve
```

To reproduce the Pages directory structure locally:

```bash
rm -rf site-root
mkdir -p site-root/asrquant
mkdocs build --strict --site-dir site-root/asrquant
```

## Notebook mathematics policy

The official notebook is validated before each documentation build. Displayed equations must use:

```markdown
$$
P(0,T)=e^{-z(T)T}
$$
```

The validator rejects `\\(...\\)`, `\\[...\\]`, unbalanced `$$` delimiters and single-dollar math in the official quickstart notebook.
