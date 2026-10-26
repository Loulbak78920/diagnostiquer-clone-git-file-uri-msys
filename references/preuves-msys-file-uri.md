# Preuves : clone local et file URI sous variables MSYS

Faits datés du **2026-10-26**. Deux origines distinctes, jamais confondues :

- **Observé en session source** (`9bd2ebf7-0527-45b2-9bd3-6bc556a538de`) : l'échec, la sonde quatre conditions et le correctif. La chaîne de références imbriquées de cette session pointe aussi vers `c4fcd88c-4b53-4843-a74c-f4a901244e96` et `b8448766-bcf0-40dc-9ea5-9622f129877e`, qui documentent le même incident.
- **Mesuré avec le harnais de cette Skill** : exécutions réelles du script livré, sorties recopiées telles quelles.

## Environnement mesuré

| Élément | Valeur |
|---|---|
| OS | Windows 10.0.26200, Git Bash |
| Git | `git version 2.52.0.windows.1` |
| Python | `Python 3.14.7` via `py -3` |
| `core.autocrlf` système | `true` |
| `MSYS_NO_PATHCONV` / `MSYS2_ARG_CONV_EXCL` du shell appelant | unset |

## 1. Incident source

Le harnais de publication échoue au premier clone local, avec une URL à trois barres :

```text
Fixture root: C:\Users\Administrateur\.qoder\tmp\isolated-publish-gd_xxp8u
Verifier sha256: d11f8864789d5f8627455c87b8b57554aaa5efa52bef5bf66ad66f9e6f5df1ed
FAIL git clone rc=128: fatal: '/C:/Users/Administrateur/.qoder/tmp/isolated-publish-gd_xxp8u/origin.git' does not appear to be a git repository
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
CLEANUP root and isolated clone absent
RESULT FAIL isolated publication flow
EXIT=1
```

Le chemin affiché a perdu sa lettre de lecteur : `/C:/...` au lieu de `C:/...`. Le dépôt existe pourtant.

## 2. Sonde source : quatre conditions

Le wrapper git exportait `MSYS_NO_PATHCONV=1` et `MSYS2_ARG_CONV_EXCL='*'` pour tous ses appels. La sonde clone un origin nu local avec `file:///C:/...` en variant l'environnement :

```text
URL file:///C:/Users/Administrateur/.qoder/tmp/msysprobe-6p76eubc/o.git
inherit rc 0 ['warning: You appear to have cloned an empty repository.']
no_pathconv rc 128 ['and the repository exists.']
arg_excl rc 128 ['and the repository exists.']
both rc 128 ['and the repository exists.']
cleaned True
```

Lecture : l'environnement hérité réussit ; chacune des deux variables, seule ou avec l'autre, provoque `rc=128`. L'origine était vide, d'où l'avertissement mais pas l'échec de la cellule `inherit`. La sonde n'imprimait que la dernière ligne de `stderr` ; le chemin `/C:/...` complet vient de l'incident ci-dessus.

## 3. Correctif source

Une édition unique retire les deux exports de l'environnement du wrapper git générique, en laissant le commentaire suivant :

```python
env = dict(os.environ)
env["LC_ALL"] = "C"
env["GIT_TERMINAL_PROMPT"] = "0"
# MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL make git resolve file:///C:/ as
# /C:/... and break local clones (rc=128). Only the verifier needs them.
cmd = ["git", "-C", str(repo), *args]
```

Après ce retrait, le harnais de publication rend `RESULT PASS` deux fois avec des hashes différents, puis une fois avec `--keep`, en utilisant encore l'URL à trois barres :

```text
isolated remote: file:///C:/Users/Administrateur/.qoder/tmp/isolated-publish-v8p64r7x/origin.git
RUN2_EXIT=0
RESULT PASS isolated publication flow (clone, SHA-256, guards, ff, push, remote verify, cleanup)
KEEP_EXIT=0
KEEP fixture root: C:\Users\Administrateur\.qoder\tmp\isolated-publish-98fmyylx
RESULT PASS isolated publication flow (clone, SHA-256, guards, ff, push, remote verify, cleanup)
```

La forme à deux barres est apparue plus tard dans le script final (`file://C:/...`) et a aussi rendu `RESULT PASS`, mais la source n'a pas mesuré ce facteur isolément : les variables MSYS étaient déjà retirées. Cette lacune est comblée ci-dessous.

## 4. Mesure fraîche : matrice 2 formes × 4 conditions

Exécution **historique** `--keep` du 2026-10-26 à 13:11:35, empreinte du script `228bf2e2521126d2e0cf9b4dc797fb586886a4da91670787b3693d4698bff8de` (11 133 octets, 348 lignes). Cette empreinte n'est plus celle du script livré ; la version finale est re-vérifiée en 4b.

```text
Skill: diagnostiquer-clone-git-file-uri-msys
Timestamp: 2026-10-26 13:11:35
Parent: MSYS_NO_PATHCONV=unset | MSYS2_ARG_CONV_EXCL=unset
Fixture root: C:\Users\Administrateur\.qoder\tmp\diag-clone-file-uri-4lrkmsut
Git: git version 2.52.0.windows.1
Origin: C:\Users\Administrateur\.qoder\tmp\diag-clone-file-uri-4lrkmsut\origin.git
URL three: file:///C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git
URL two:   file://C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git
CELL form=three env=inherit rc=0 clone=yes branch=main status=clean remote=file:///C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git local_config=absent
CELL form=three env=no_pathconv rc=128 clone=no fatal=fatal: '/C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git' does not appear to be a git repository
CELL form=three env=arg_excl rc=128 clone=no fatal=fatal: '/C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git' does not appear to be a git repository
CELL form=three env=both rc=128 clone=no fatal=fatal: '/C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git' does not appear to be a git repository
OBSERVE form=two env=inherit rc=0 clone=yes branch=main status=clean remote=file://C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git local_config=absent
OBSERVE form=two env=no_pathconv rc=0 clone=yes branch=main status=clean remote=file://C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git local_config=absent
OBSERVE form=two env=arg_excl rc=0 clone=yes branch=main status=clean remote=file://C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git local_config=absent
OBSERVE form=two env=both rc=0 clone=yes branch=main status=clean remote=file://C:/Users/Administrateur/.qoder/tmp/diag-clone-file-uri-4lrkmsut/origin.git local_config=absent
RESULT REPRODUCED msys_file_uri_clone
KEEP fixture root: C:\Users\Administrateur\.qoder\tmp\diag-clone-file-uri-4lrkmsut
EXIT=0
```

Synthèse :

| Forme | `inherit` | `no_pathconv` | `arg_excl` | `both` |
|---|---|---|---|---|
| `file:///C:/...` | rc=0, clone propre | rc=128, `/C:/...` | rc=128, `/C:/...` | rc=128, `/C:/...` |
| `file://C:/...` | rc=0, clone propre | rc=0, clone propre | rc=0, clone propre | rc=0, clone propre |

Trois autres exécutions historiques du même jour, sans `--keep`, ont rendu le même verdict et `EXIT=0` :

| Exécution | Option | Fixture | Verdict | Nettoyage |
|---|---|---|---|---|
| 1 | défaut | `diag-clone-file-uri-_r1rav2d` | `REPRODUCED` | racine absente |
| 2 | défaut | `diag-clone-file-uri-8lbc_zo5` | `REPRODUCED` | racine absente |
| 3 | `--url-forms three` | `diag-clone-file-uri-8yor1aya` | `REPRODUCED` | racine absente |

### 4b. Re-vérification de la version finale

Empreinte du script livré : `cda32146f0e67f10ca33ddceb12e6fcba62076e0fa5460e4f5d291482a4883df` (11 273 octets, 353 lignes). Cinq exécutions sur cette version, shell appelant nettoyé sauf mention :

| Exécution | Option | Fixture | Attendu | Constaté |
|---|---|---|---|---|
| F | défaut | `diag-clone-file-uri-hydwsq27` | 8 cellules, `REPRODUCED`, `EXIT=0` | conforme, `CLEANUP root and clones absent` |
| G | défaut | `diag-clone-file-uri-cqx5fq7i` | idem | conforme, nettoyage confirmé |
| H | `--url-forms three` | `diag-clone-file-uri-yjlteqz7` | 4 `CELL`, 0 `OBSERVE`, 0 ligne `URL two`, `EXIT=0` | conforme |
| I | `--keep` | `diag-clone-file-uri-pvm62wh1` | `REPRODUCED`, `KEEP` affiché | conforme ; fixture supprimée ensuite |
| J | défaut, `MSYS_NO_PATHCONV=1` dans le parent | aucune créée | `ERROR`, `EXIT=2` avant fixture | conforme, comptage avant/après identique |

Sorties F et J recopiées :

```text
Skill: diagnostiquer-clone-git-file-uri-msys
Timestamp: 2026-10-26 13:19:56
Parent: MSYS_NO_PATHCONV=unset | MSYS2_ARG_CONV_EXCL=unset
Fixture root: C:\Users\Administrateur\.qoder\tmp\diag-clone-file-uri-hydwsq27
Git: git version 2.52.0.windows.1
Origin: C:\Users\Administrateur\.qoder\tmp\diag-clone-file-uri-hydwsq27\origin.git
RESULT REPRODUCED msys_file_uri_clone
CLEANUP root and clones absent
EXIT=0
```

```text
Skill: diagnostiquer-clone-git-file-uri-msys
Timestamp: 2026-10-26 13:20:38
Parent: MSYS_NO_PATHCONV=1 | MSYS2_ARG_CONV_EXCL=unset
ERROR parent exports MSYS variables; unset MSYS_NO_PATHCONV and MSYS2_ARG_CONV_EXCL for this session, then rerun.
EXIT=2
```

La garde J compte : un `inherit` mesuré dans un shell qui exporte déjà les variables ne serait pas un témoin valide. Le script refuse désormais de produire une matrice ambiguë et sort avant de créer la fixture.

## 5. Constat nouveau : deux barres sous variables MSYS

Dans cet environnement précis (Git 2.52.0.windows.1), `file://C:/...` réussit dans les quatre conditions, y compris quand `MSYS_NO_PATHCONV=1` et `MSYS2_ARG_CONV_EXCL='*'` sont présents. La source n'avait pas mesuré cette combinaison : elle avait retiré les variables avant de passer à deux barres. Le constat a été refait sur la version finale du harnais (exécutions F–I ci-dessus).

Ce constat est une observation locale, pas un contrat :

- il n'a pas été expliqué par lecture du code de Git ;
- il n'a pas été reproduit sur une autre version de Git, un autre shell ou un remote réseau ;
- il ne rend pas inutile le correctif principal (retirer l'export global), qui traite la cause et pas seulement la forme de l'URL.

## 6. Intégration : harnais de publication

Après le correctif, le harnais `tester-publication-isolee-skill` a été relancé une première fois dans cette session :

```text
Fixture root: C:\Users\Administrateur\.qoder\tmp\isolated-publish-u_n30mkw
Verifier sha256: d11f8864789d5f8627455c87b8b57554aaa5efa52bef5bf66ad66f9e6f5df1ed
STEP 5 commit 548270a41039723fe604276d0caeb40e83a04f5c
STEP 5b recovery commit 724b035af0a600e38df17849f2242fc3635a7af3
ok remote main after push: '724b035af0a600e38df17849f2242fc3635a7af3'
ok original branch: 'skill/occupied'
ok original status: 'M base.txt\n?? untracked.txt'
CLEANUP root and isolated clone absent
RESULT PASS isolated publication flow (clone, SHA-256, guards, ff, push, remote verify, cleanup)
EXIT=0
```

Le clone isolé utilise `file://C:/...` et le wrapper git ne pose plus les variables MSYS. Le clone source est resté sur sa branche, avec son statut sale et ses hashes inchangés ; le commit publié n'y apparaît pas.

Après la mise à jour finale de cette Skill, le même harnais a été relancé deux fois : deux `RESULT PASS`, `EXIT=0`, avec des commits différents.

```text
Fixture root: C:\Users\Administrateur\.qoder\tmp\isolated-publish-6j89yo6_
STEP 5 commit 0bfe1092336356036a3791c47dd74c5aa4dab91a
STEP 5b recovery commit 53f121073d260d8ed4892e71b50c17d7a985f805
RESULT PASS isolated publication flow (clone, SHA-256, guards, ff, push, remote verify, cleanup)
EXIT=0
```

```text
Fixture root: C:\Users\Administrateur\.qoder\tmp\isolated-publish-eou_iu_i
STEP 5 commit cfa7502a70278d6400ac0ad4c6b5580447bc7f63
STEP 5b recovery commit 30b090589d7ecad7ab1adc97bbc8cbe0480e3c4e
RESULT PASS isolated publication flow (clone, SHA-256, guards, ff, push, remote verify, cleanup)
EXIT=0
```

## 7. Nettoyage

- Les fixtures `--keep` `diag-clone-file-uri-ayfc8m0o` et `diag-clone-file-uri-pvm62wh1` ont été vérifiées présentes, contrôlées sur le préfixe `diag-clone-file-uri-` sous `$HOME/.qoder/tmp`, puis supprimées ; absence confirmée.
- Après quatorze exécutions du script de diagnostic (dont une sortie volontaire en `EXIT=2`) et trois exécutions du harnais de publication, aucune entrée `diag-clone-file-uri-*`, `isolated-publish-*` ou `publish-fake-skill.*` ne restait sous `$HOME/.qoder/tmp`.
- Aucun fichier des Skills voisins n'a été modifié par ces mesures.

## 8. Provenance et limites

- **Observé en session source** : échec `rc=128` avec `/C:/...`, sonde quatre conditions, retrait des exports, deux `RESULT PASS` puis un `--keep` avec URL à trois barres.
- **Mesuré avec le harnais livré** : matrice complète 2 × 4, verdict `REPRODUCED`, nettoyage, `--keep`, le constat deux barres sous variables MSYS, puis re-vérification de la version `cda32146…` par cinq exécutions (F–J), dont la garde parent `EXIT=2` sans création de fixture.
- **Non prouvé** : un dépôt réel, un remote réseau, une autre version de Git, un autre shell, la sûreté d'un `push`/`fetch` sous ces variables, ou la correction d'un wrapper de production. Le harnais exige Windows, Git dans le `PATH` et `py -3`.

## 9. Reproduire

```bash
py -3 "C:/Users/Administrateur/.qoder/skills/diagnostiquer-clone-git-file-uri-msys/scripts/diagnostiquer_clone_file_uri.py"
py -3 "C:/Users/Administrateur/.qoder/skills/diagnostiquer-clone-git-file-uri-msys/scripts/diagnostiquer_clone_file_uri.py" --url-forms three
py -3 "C:/Users/Administrateur/.qoder/skills/diagnostiquer-clone-git-file-uri-msys/scripts/diagnostiquer_clone_file_uri.py" --keep
```

Sur une autre machine, remplacer le préfixe `C:/Users/Administrateur/.qoder/skills/` par le dossier d'installation réel. Un `RESULT REPRODUCED` ne vaut que pour la matrice exécutée dans la fixture locale. Si le shell appelant exporte déjà `MSYS_NO_PATHCONV` ou `MSYS2_ARG_CONV_EXCL`, le script sort `ERROR` avec le code 2 avant toute mesure : les retirer d'abord.
