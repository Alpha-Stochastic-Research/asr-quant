# ASRQuant branded documentation route

The public ASRQuant documentation URL is:

`https://docs.asr-lab.online/asrquant/`

The generated MkDocs HTML keeps this branded route as its canonical page identity and navigation base. Static MkDocs assets are served from the GitHub Pages origin:

`https://alpha-stochastic-research.github.io/asr-quant/`

This split is intentional. The branded route may be served through a proxy/CDN path that does not mirror every nested static asset path. Absolute asset URLs prevent CSS, JavaScript, logos, and search resources from resolving against the wrong `/asrquant/...` path.

The documentation workflow performs a live post-deploy smoke test against the branded route so a future deployment fails visibly if the route starts returning raw, unstyled MkDocs HTML again.
