---
name: diagnostiquer-clone-git-file-uri-msys
description: "Diagnostiquer un git clone local en échec sous Windows/Git Bash quand un wrapper Python exporte MSYS_NO_PATHCONV=1 ou MSYS2_ARG_CONV_EXCL='*' à tous ses appels git et que le clone rend rc=128 avec fatal: '/C:/...' does not appear to be a git repository : reproduire dans une fixture jetable avec un origin nu local, mesurer la matrice quatre conditions (environnement hérité, une variable, l'autre, les deux) croisée avec les formes file:///C:/... et file://C:/..., isoler le facteur, appliquer le correctif minimal en retirant l'export global (les variables restent limitées au sous-processus qui en a besoin) ou en durcissant l'URL, puis accepter par clone propre, remote get-url, status --porcelain vide, absence de configuration locale et reprise du harnais d'origine. 中文触发：Git Bash 克隆失败、rc=128、路径少了盘符 /C:/、does not appear to be a git repository、MSYS_NO_PATHCONV、MSYS2_ARG_CONV_EXCL、file URI、本地裸仓库、Python 包装 git、四条件矩阵、只给需要的工具设置变量。"
---

# Diagnostiquer un clone Git local en échec sous Git Bash

## Objectif

Attribuer un `git clone` local en `rc=128` avec `fatal: '/C:/...' does not appear to be a git repository` à un export global de `MSYS_NO_PATHCONV=1` ou `MSYS2_ARG_CONV_EXCL='*'`, puis appliquer et prouver le correctif minimal.

État mesuré le 2026-10-26 avec Git for Windows 2.52.0 : retirer l'export global des deux variables suffit ; l'URL `file:///C:/...` fonctionne alors à nouveau. Mesure complémentaire du même jour avec le harnais de ce Skill : la forme `file://C:/...` (deux barres) réussit dans les quatre conditions, y compris avec les deux variables présentes ; la source n'avait pas isolé ce facteur. Cette observation vaut pour cet environnement et cette version de Git, pas comme garantie générale.

## État livré

Trois fichiers, tous présents et vérifiés le 2026-10-26 :

| Fichier | État | Preuve |
|---|---|---|
| `SKILL.md` | présent, vérifié | ce contrat ; contrôlé par `skill-file-qa` |
| `scripts/diagnostiquer_clone_file_uri.py` | présent, vérifié | sha256 `cda32146f0e67f10ca33ddceb12e6fcba62076e0fa5460e4f5d291482a4883df`, 353 lignes ; exécutions F–J |
| `references/preuves-msys-file-uri.md` | présent, vérifié | sorties datées, provenance, limites |

Exécutions de la version finale : deux défauts `REPRODUCED` / `EXIT=0`, une passe `--url-forms three` sans ligne `URL two`, un `--keep` puis suppression contrôlée de la fixture, et un contrôle négatif avec `MSYS_NO_PATHCONV=1` dans le parent qui rend `EXIT=2` avant toute fixture. Le harnais d'origine `tester_publication_isolee.py` a rendu deux `RESULT PASS` avec des commits différents. Détail : `references/preuves-msys-file-uri.md`, sections 4b et 6.

## Quand l'utiliser

- `git clone` local en `rc=128`, chemin affiché `/C:/...` sans lettre de lecteur, alors que le dépôt existe.
- Wrapper Python ou Node qui met `MSYS_NO_PATHCONV=1` ou `MSYS2_ARG_CONV_EXCL='*'` dans l'environnement de tous les `git`, y compris `clone`.
- Un outil a réellement besoin de ces variables pour ses propres arguments et on veut les limiter à ce sous-processus.
- Reproduire la matrice « environnement hérité / une variable / l'autre / les deux » avant de changer le code.

Ne pas utiliser pour : un dépôt absent, un refus de permission, un `core.autocrlf` qui salit un clone, une dérive de refs, la publication d'un Skill (`tester-publication-isolee-skill`, `publier-skill-qoder-vers-depot-git`), ni le simple argv d'un CLI (`probe-cli-args-beyond-msys-rewrite`).

## Contrat non négociable

1. **Fixture jetable uniquement** : tout sous `$HOME/.qoder/tmp/diag-clone-file-uri-*`. Jamais un dépôt de travail ni un remote réseau.
2. **Quatre conditions contrôlées** : `inherit` (environnement du parent, valeurs imprimées), `no_pathconv` (parent nettoyé + `MSYS_NO_PATHCONV=1`), `arg_excl` (parent nettoyé + `MSYS2_ARG_CONV_EXCL='*'`), `both` (les deux). Ne pas empiler d'autres écarts.
3. **URL et environnement séparés** : mesurer `file:///C:/...` et `file://C:/...` pour chaque condition. Ne jamais conclure qu'une forme est équivalente sans sa cellule.
4. **Un seul facteur à la fois** : retirer l'export global et changer la forme d'URL sont deux correctifs distincts. Si les deux sont appliqués, le dire et les tester séparément quand c'est possible.
5. **Portée du correctif** : ne pas supprimer les variables de l'environnement de l'utilisateur. Les retirer du wrapper git générique ; si un outil en a besoin, les laisser à cet outil dans son propre sous-processus (par exemple `verifier_archive_skill.py` les pose lui-même).
6. **Assertions exactes** : `rc`, token `fatal`, présence de `/C:/`, présence du clone, branche, `status --porcelain` vide, `remote get-url` non vide, absence de `core.autocrlf`/`user.name`/`user.email` locaux. « Le script ne plante pas » n'est pas un PASS.
7. **Ne pas forcer la reproduction** : si la matrice ne reproduit pas, rendre `NOT_REPRODUCED` ou `PARTIAL` et le rapporter ; ne pas modifier l'attendu.
8. **Codes réservés** : 0 `REPRODUCED`, 1 `PARTIAL`/`NOT_REPRODUCED`, 2 usage, environnement ou échec de nettoyage. Sortie ASCII, sans traceback brut.
9. **Nettoyage vérifié** : dans `finally`, `chmod` inscriptible avant `rmtree` sous Windows, puis vérifier l'absence. `--keep` conserve et imprime la racine.
10. **Pas de PASS recyclé** : chaque exécution crée un nouveau dépôt, de nouveaux hashes et un nouveau chemin.

## Procédure

Remplacer `<dossier-skill>` par le dossier réel. Les chemins absolus sont passés entre guillemets.

### 0. Préflight

```bash
git --version
py -3 -c "import sys;print(sys.version.split()[0])"
printf 'MSYS_NO_PATHCONV=%s\n' "${MSYS_NO_PATHCONV:-unset}"
printf 'MSYS2_ARG_CONV_EXCL=%s\n' "${MSYS2_ARG_CONV_EXCL:-unset}"
git config --system --get core.autocrlf || echo "core.autocrlf systeme: unset"
```

Les deux variables doivent être unset dans le shell appelant pour que la cellule `inherit` soit un vrai témoin. Si elles sont définies, les retirer pour cette session (`unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL`) et le noter ; ne pas modifier la configuration de façon persistante.

### 1. Reproduire avec une seule cellule

Créer un origin nu local, y pousser un commit, puis cloner avec l'environnement hérité et `Path.as_uri()` (`file:///C:/...`). Attendu : `rc=0`, branche `main`, worktree propre.

Si ce témoin échoue, le diagnostic de ce Skill ne s'applique pas : chercher d'abord un dépôt absent, un droit ou un chemin invalide.

### 2. Matrice quatre conditions

```bash
py -3 "<dossier-skill>/scripts/diagnostiquer_clone_file_uri.py" --url-forms three
```

Attendu mesuré à la source : `inherit rc=0` ; les trois cellules MSYS `rc=128` avec `'/C:/...' does not appear to be a git repository`. Le script rend `RESULT REPRODUCED` seulement si les quatre cellules correspondent ; sinon `PARTIAL` ou `NOT_REPRODUCED`.

### 3. Croisement des formes d'URL

```bash
py -3 "<dossier-skill>/scripts/diagnostiquer_clone_file_uri.py"
```

Lire les lignes `OBSERVE form=two` : elles ne participent pas au verdict. Elles indiquent si `file://C:/...` réussit lorsque les variables sont présentes. Mesure du 2026-10-26 : les quatre cellules deux barres ont rendu `rc=0` et un clone propre, y compris sous les deux variables. Ne pas généraliser à une autre version de Git ni à un remote réseau ; si une cellule échoue sur une autre machine, le déclarer et ne pas présenter cette forme comme correctif.

### 4. Correctif minimal

Ordre de préférence :

1. Retirer `MSYS_NO_PATHCONV` et `MSYS2_ARG_CONV_EXCL` de l'environnement du wrapper git générique.
2. Si un outil a besoin de ces variables, les poser dans son appel à lui (sous-processus), jamais dans l'environnement global.
3. Durcir l'URL en `file://C:/...` seulement si la matrice le justifie, ou comme défense en profondeur en le déclarant comme tel.

Ne pas modifier la configuration Git globale ou système. Ne pas changer `core.autocrlf` pour masquer un autre échec.

### 5. Accepter le correctif

Pour chaque clone réussi :

```bash
git -C "<clone>" rev-parse --abbrev-ref HEAD          # main
git -C "<clone>" status --porcelain=v1                # vide
git -C "<clone>" remote get-url origin                # URL attendue
git -C "<clone>" config --local --get core.autocrlf   # rc=1, absent
git -C "<clone>" config --local --get user.name       # rc=1, absent
git -C "<clone>" config --local --get user.email      # rc=1, absent
```

Puis relancer le harnais d'origine deux fois (par exemple `tester_publication_isolee.py`) : deux `RESULT PASS` avec des hashes différents. Un seul PASS peut être recyclé ou dater d'avant le correctif.

### 6. Nettoyer et rapporter

Vérifier l'absence de `diag-clone-file-uri-*` sous `$HOME/.qoder/tmp`, puis produire le rapport ci-dessous.

## Sorties observées

### Source (2026-10-26)

Matrice quatre conditions avec `file:///C:/...` (`9bd2ebf7`, 2026-10-26) :

```text
URL file:///C:/Users/Administrateur/.qoder/tmp/msysprobe-6p76eubc/o.git
inherit rc 0 ['warning: You appear to have cloned an empty repository.']
no_pathconv rc 128 ['and the repository exists.']
arg_excl rc 128 ['and the repository exists.']
both rc 128 ['and the repository exists.']
cleaned True
```

Le chemin fautif vient du clone échoué, pas de cette sonde qui n'imprimait que la dernière ligne de stderr :

```text
FAIL git clone rc=128: fatal: '/C:/Users/Administrateur/.qoder/tmp/isolated-publish-gd_xxp8u/origin.git' does not appear to be a git repository
fatal: Could not read from remote repository.
```

Après retrait de l'export global, l'URL était encore `file:///C:/...` et le harnais a rendu `RESULT PASS` deux fois, puis une fois avec `--keep`. La forme `file://C:/...` est apparue ensuite dans le script final, également en PASS, sans mesure isolée de son effet dans la source.

### Mesure complémentaire (2026-10-26)

Avec le harnais livré (version `cda32146…`), les quatre cellules deux barres (`inherit`, `no_pathconv`, `arg_excl`, `both`) rendent `rc=0`, branche `main`, statut propre, remote présent et aucune configuration locale. C'est une observation locale à Git 2.52.0.windows.1, pas une équivalence générale. Détail daté : `references/preuves-msys-file-uri.md`.

## Erreurs et pièges

| Symptôme | Cause | Action |
|---|---|---|
| `rc=128`, `fatal: '/C:/...' does not appear...` | variables MSYS exportées + URL `file:///C:/...` | retirer l'export global, puis remesurer |
| `fatal: 'C:/...' does not appear...` sans `/` initial | dépôt absent, chemin faux ou droit refusé | ne pas attribuer à MSYS ; vérifier le dépôt |
| `can't open file 'C:\c\Users\...'` | variables MSYS ayant aussi réécrit le chemin du script Python | lancer avec un chemin natif ou sans les variables |
| `warning: You appear to have cloned an empty repository.` + `rc=0` | origin vide, pas un échec | semer un commit avant la matrice |
| `M base.txt` après clone | différence `core.autocrlf`, pas MSYS | traiter séparément, ne pas mélanger les causes |
| `STOP_BRANCH` / `STOP_DIRTY` / `STOP_ORIGIN` | garde de dérive, pas ce diagnostic | voir `tester-garde-derive-git` |
| `could not create work tree dir` | droit ou chemin de destination | ne pas attribuer à MSYS |
| `remote get-url` normalise la forme d'URL | normalisation Git | enregistrer la valeur ; ne pas échouer sur ce seul point |
| `RESULT NOT_REPRODUCED` alors que l'incident est réel | environnement différent (version Git, shell, variables déjà absentes) | rapporter la matrice réelle ; ne pas forcer l'attendu |
| `ERROR parent exports MSYS variables...`, `EXIT=2`, aucune fixture créée | le shell appelant exporte déjà `MSYS_NO_PATHCONV` ou `MSYS2_ARG_CONV_EXCL` | les retirer de la session (`unset ...`) puis relancer ; ne pas modifier la configuration persistante |

## Rapport

```text
Skill : diagnostiquer-clone-git-file-uri-msys | matrice du <date>
Environnement : Windows <version>, Git <version>, Python <version>, core.autocrlf=<valeur>
Parent : MSYS_NO_PATHCONV=<valeur|unset> | MSYS2_ARG_CONV_EXCL=<valeur|unset>
Matrice trois barres : inherit rc=<n> | no_pathconv rc=<n> | arg_excl rc=<n> | both rc=<n>
Verdict : REPRODUCED | PARTIAL | NOT_REPRODUCED
Croisement deux barres : <cellules observées, y compris les échecs>
Correctif : export global retiré ? oui/non | variables limitées à <outil> ? oui/non | URL deux barres ? mesurée oui/non
Acceptation : clone rc=0, branche, statut, remote, config locale absente | harnais d'origine PASS x2
Nettoyage : racine absente | --keep non utilisé
Limites : réseau, autres versions Git, push/fetch sous variables non testés
```

## Définition de terminé

- [ ] Préflight exécuté : versions Git/Python, variables MSYS du parent imprimées, `core.autocrlf` relevé.
- [ ] Cellule témoin `inherit` + `file:///C:/...` réussie ; sinon, diagnostic déclaré hors périmètre.
- [ ] Matrice trois barres exécutée et verdict lu (`REPRODUCED`, `PARTIAL` ou `NOT_REPRODUCED`).
- [ ] Croisement deux barres exécuté ou explicitement non mesuré ; aucune généralisation hors environnement.
- [ ] Correctif appliqué selon l'ordre de préférence, sans toucher à la configuration Git globale ni à l'environnement de l'utilisateur.
- [ ] Pour chaque clone accepté : branche `main`, `status --porcelain` vide, `remote get-url` non vide, aucune config locale `core.autocrlf`/`user.name`/`user.email`.
- [ ] Harnais d'origine relancé deux fois, deux `RESULT PASS` avec des hashes différents.
- [ ] Fixtures absentes après nettoyage, ou racine `--keep` imprimée et supprimée après contrôle du préfixe.
- [ ] Rapport produit avec les valeurs réelles ; aucun `PASS` ou `REPRODUCED` revendiqué sans sortie correspondante.

## Fichiers et ressources

| Fichier | Rôle | État |
|---|---|---|
| `SKILL.md` | Contrat, procédure, erreurs et rapport | présent, vérifié |
| `scripts/diagnostiquer_clone_file_uri.py` | Matrice 2 formes × 4 conditions, verdict et nettoyage | présent, vérifié |
| `references/preuves-msys-file-uri.md` | Preuves datées, provenance et limites | présent, vérifié |

Les chemins ci-dessus sont relatifs au dossier du Skill. Sur cette machine, le dossier est `C:\Users\Administrateur\.qoder\skills\diagnostiquer-clone-git-file-uri-msys\` ; après un déplacement ou une copie, remplacer ce préfixe.

- `probe-cli-args-beyond-msys-rewrite` : argv et paramètres CLI réécrits par MSYS ; ne couvre pas le clone ni le file URI.
- `tester-publication-isolee-skill` : harnais d'intégration à relancer après le correctif ; contient déjà un correctif analogue.
- `skill-file-qa` : validation statique de ce Skill après écriture.

```bash
py -3 "<dossier-skill>/scripts/diagnostiquer_clone_file_uri.py"
py -3 "<dossier-skill>/scripts/diagnostiquer_clone_file_uri.py" --url-forms three
py -3 "<dossier-skill>/scripts/diagnostiquer_clone_file_uri.py" --keep
```

Un `RESULT REPRODUCED` ne prouve que la matrice observée dans la fixture locale. Il ne prouve ni un remote réseau, ni une autre version de Git, ni la sûreté d'un push.
