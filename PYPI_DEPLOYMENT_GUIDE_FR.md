# Déploiement PyPI — ASRQuant 1.2.0

`1.2.0` est la release stable qui conserve Research Discovery / Interest Rates et ajoute les APIs structurées, la découverte d’hypothèses data-driven, alpha, factors, risk et microstructure.

## Trusted Publisher

Configurer sur PyPI :

- Project: `asrquant`
- Owner: `Alpha-Stochastic-Research`
- Repository: `asr-quant`
- Workflow: `release.yml`
- Environment: `pypi`

Aucun token PyPI permanent n'est nécessaire lorsque le Trusted Publisher OIDC est correctement configuré.

## Publication

Après validation du commit final :

```bash
git checkout main
git pull origin main
git tag -a v1.2.0 -m "ASRQuant 1.2.0"
git push origin v1.2.0
```

Créer ensuite une GitHub Release :

- tag : `v1.2.0`
- titre : `ASRQuant 1.2.0`
- **ne pas** cocher `Pre-release`

Le workflow `release.yml` reconstruit les distributions et publie la wheel et le sdist via le Trusted Publisher.

## Vérification

```bash
python3 -m venv asrquant-120-check
source asrquant-120-check/bin/activate
python -m pip install --upgrade pip
python -m pip install asrquant==1.2.0
python -c "import asrquant as asr; print(asr.__version__)"
asrquant --version
```

Résultat attendu : `1.2.0`.
