# ASRQuant v1.1.0 release checklist

## Source and scientific validation

- [x] package/runtime version set to `1.1.0`;
- [x] 197 tests collected;
- [x] new Discovery/Rates/ECB tests pass;
- [x] legacy paper-contract and production groups pass;
- [x] Python source compilation passes;
- [x] new examples execute;
- [x] wheel and sdist build locally;
- [x] isolated-target wheel import and CLI smoke tests pass;
- [ ] Ruff/static-analysis job passes on the exact hosted release commit;
- [ ] clean environment resolves declared dependencies, including `pypdf>=6.14.2,<7`;
- [ ] GitHub-hosted CI/security/distribution workflows are green.

## Research/interest-rate review

- [x] automated novelty claims remain disabled (`NOT_ESTABLISHED` by default);
- [x] Friday-to-Friday plan includes independent review before publication;
- [x] no-arbitrage/curve-risk diagnostics are exposed;
- [x] Black and normal rate-option conventions are explicit;
- [x] model/research implementation limitations are documented;
- [ ] independent rates-domain reviewer signs off before public release.

## Release

- [ ] push reviewed changes to the protected repository branch;
- [ ] open/approve PR according to ASR governance;
- [ ] tag the reviewed commit `v1.1.0`;
- [ ] build distributions in hosted release CI;
- [ ] approve the protected PyPI environment;
- [ ] install `asrquant==1.1.0` from PyPI in a clean environment;
- [ ] verify `import asrquant as asr` and `asrquant --version`.
