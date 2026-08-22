# ASRQuant Documentation Domain Setup

Target URL:

```text
https://docs.asr-lab.online/asrquant/
```

## One-time GitHub setting

Go to:

**Alpha-Stochastic-Research/asr-quant → Settings → Pages**

Set:

```text
Source: GitHub Actions
Custom domain: docs.asr-lab.online
```

Save the domain. When GitHub makes the HTTPS option available, enable **Enforce HTTPS**.

## One-time DNS record

At the DNS provider for `asr-lab.online`:

```text
Type: CNAME
Name/Host: docs
Target/Value: alpha-stochastic-research.github.io
TTL: Auto (or provider default)
```

Do not add `/asrquant/` to the CNAME value.

## Deploy

Push this repository state to `main` through the normal protected-branch/PR process. The `Documentation` Actions workflow builds the site beneath `site-root/asrquant/` and GitHub Pages publishes it at the target URL.
