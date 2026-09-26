# Déploiement PyPI — ASRQuant 1.3.0

`1.3.0` est la release stable d’ASRQuant. Elle préserve les contrats publics 1.0–1.2 et ajoute l’infrastructure de conventions de marché, courbes/instruments, risque en espace de cotations, crédit, validation avancée, snapshots point-in-time, lineage de recherche, scénarios, modèles de coûts, calibration/sensibilités et contrôles renforcés de compatibilité API.

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
git tag -a v1.3.0 -m "ASRQuant 1.3.0"
git push origin v1.3.0
```

Créer ensuite une GitHub Release :

- tag : `v1.3.0`
- titre : `ASRQuant 1.3.0`
- **ne pas** cocher `Pre-release`

Le workflow `release.yml` reconstruit les distributions et publie la wheel et le sdist via le Trusted Publisher.

## Vérification

```bash
python3 -m venv asrquant-130-check
source asrquant-130-check/bin/activate
python -m pip install --upgrade pip
python -m pip install asrquant==1.3.0
python -c "import asrquant as asr; print(asr.__version__)"
asrquant --version
```

Résultat attendu : `1.3.0`.
