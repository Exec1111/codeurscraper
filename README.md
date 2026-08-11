# codeurscraper

Recherche automatisée de missions freelance sur plusieurs sites
([codeur.com](https://www.codeur.com), [freelancer.com](https://www.freelancer.com)),
avec des critères exprimés en langage naturel plutôt que les filtres par
défaut de chaque site. Chaque matin, un workflow GitHub Actions scrape les
nouvelles missions, les fait noter par un LLM par rapport à tes critères, et
publie les 5 à 20 meilleures sur une page GitHub Pages.

## Fonctionnement

1. Chaque source vit dans `scripts/sources/<nom>.py` (`codeur.py`,
   `freelancer.py`) et expose la même interface : `crawl_new_listings(seen_ids,
   max_pages, delay)` qui parcourt les pages de listing par ordre de
   récence et s'arrête dès qu'une page ne contient plus rien de nouveau par
   rapport à la veille (`docs/data/seen_ids.json`), et `fetch` /
   `parse_detail_description` pour aller chercher la description complète
   d'une mission. Les ids sont préfixés par source (`codeur:488057`,
   `freelancer:/projects/...`) pour rester uniques une fois agrégés.
2. `scripts/score.py` note les nouvelles missions (toutes sources
   confondues) en deux passes :
   - une passe rapide sur titre + extrait + tags (bon marché, élimine le
     bruit) ;
   - une passe précise sur la description complète, pour les ~25 meilleures
     candidates de la première passe.
3. `scripts/main.py` orchestre le tout et écrit :
   - `docs/data/latest.json` : le résultat du jour ;
   - `docs/data/history/YYYY-MM-DD.json` : l'archive ;
   - `docs/data/seen_ids.json` : mémoire des missions déjà vues.
4. `docs/index.html` affiche `latest.json`, à consulter quand tu veux (avec
   le site d'origine de chaque mission).

## Ajouter un nouveau site

Créer `scripts/sources/<nom>.py` avec :
- `SOURCE_ID` (str, unique)
- `crawl_new_listings(seen_ids: set[str], max_pages: int, delay: float) -> tuple[list[dict], set[str]]`
  — renvoie les nouvelles missions pertinentes à noter, et l'ensemble des ids
  vus pendant le run (peut être plus large que les missions renvoyées, par
  exemple si le site mélange projets à prix fixe et à l'heure sur le même
  flux : voir `freelancer.py`, qui ne garde que les prix fixes)
- `fetch(url)` et `parse_detail_description(html)` pour la description
  complète

Chaque item retourné doit avoir au minimum : `id` (préfixé `SOURCE_ID:`),
`source`, `url`, `title`, `snippet`, `tags`, `budget`, `offers`, `views`
(mettre `None` pour les champs sans équivalent sur le site). Puis ajouter le
module à la liste `SOURCES` dans `scripts/main.py`.

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
