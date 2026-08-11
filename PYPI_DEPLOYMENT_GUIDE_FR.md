# Déploiement PyPI — ASRQuant 1.1.0

`1.1.0` est la release stable qui ajoute Research Discovery / Weekly Research et le stack Interest Rates, tout en conservant le paper-contract 1.0.0.

## Trusted Publisher

Configurer sur PyPI :

- Project: `asrquant`
- Owner: `Alpha-Stochastic-Research`
- Repository: `asrquant`
- Workflow: `release.yml`
- Environment: `pypi`

Aucun token PyPI permanent n'est nécessaire lorsque le Trusted Publisher OIDC est correctement configuré.

## Publication

Après validation du commit final :

```bash
git checkout main
git pull origin main
git tag -a v1.1.0 -m "ASRQuant 1.1.0"
git push origin v1.1.0
```

Créer ensuite une GitHub Release :

- tag : `v1.1.0`
- titre : `ASRQuant 1.1.0`
- **ne pas** cocher `Pre-release`

Le workflow `release.yml` reconstruit les distributions et publie la wheel et le sdist via le Trusted Publisher.

## Vérification

```bash
python3 -m venv asrquant-110-check
source asrquant-110-check/bin/activate
python -m pip install --upgrade pip
python -m pip install asrquant==1.1.0
python -c "import asrquant as asr; print(asr.__version__)"
asrquant --version
```

Résultat attendu : `1.1.0`.
