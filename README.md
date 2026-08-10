# codeurscraper

Recherche automatisée de missions sur [codeur.com](https://www.codeur.com), avec
des critères exprimés en langage naturel plutôt que les filtres par défaut du
site. Chaque matin, un workflow GitHub Actions scrape les nouvelles missions,
les fait noter par un LLM par rapport à tes critères, et publie les 5 à 20
meilleures sur une page GitHub Pages.

## Fonctionnement

1. `scripts/scrape.py` parcourt `codeur.com/projects` (pagination `?page=N`,
   le seul paramètre autorisé par `robots.txt`) et s'arrête dès qu'une page ne
   contient plus aucune mission nouvelle par rapport à la veille
   (`docs/data/seen_ids.json`).
2. `scripts/score.py` note les nouvelles missions en deux passes :
   - une passe rapide sur titre + extrait + tags (bon marché, élimine le
     bruit) ;
   - une passe précise sur la description complète, pour les ~25 meilleures
     candidates de la première passe.
3. `scripts/main.py` orchestre le tout et écrit :
   - `docs/data/latest.json` : le résultat du jour ;
   - `docs/data/history/YYYY-MM-DD.json` : l'archive ;
   - `docs/data/seen_ids.json` : mémoire des missions déjà vues.
4. `docs/index.html` affiche `latest.json`, à consulter quand tu veux.

## Mise en route

1. **Clé API OpenAI** : Settings → Secrets and variables → Actions → New
   repository secret → `OPENAI_API_KEY`.
2. **GitHub Pages** : Settings → Pages → Source = `Deploy from a branch`,
   branche = celle qui contient ce code (ou la branche par défaut après
   fusion), dossier = `/docs`.
3. **Critères** : édite `criteria.txt` à la racine du repo, en langage
   naturel. Relu à chaque exécution.
4. **Test manuel** : onglet Actions → "Daily mission search" → Run workflow.

## Limites connues

- Les workflows planifiés (`schedule`) ne se déclenchent que sur la branche
  par défaut du repo. Tant que ce code reste sur une branche non-default, le
  cron ne tournera pas automatiquement — utilise "Run workflow" pour tester,
  et fusionne sur la branche par défaut pour activer la planification.
- L'heure du cron (`0 5 * * *` UTC, soit 7h à Paris en été) ne s'ajuste pas
  automatiquement au changement d'heure hiver/été ; décale-la de ±1h dans
  `.github/workflows/daily.yml` si besoin.
- Modèle utilisé par défaut : `gpt-5.6-luna` (variable d'environnement
  `OPENAI_MODEL` dans le workflow pour en changer).
