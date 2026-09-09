# Garde-fou de publication

`pre-commit` refuse d'indexer le coeur ferme (IP-BOUNDARY) dans ce depot :
`.gitignore` est consultatif, `git add -f` ou un stash passent a cote, alors
que ce hook inspecte ce qui est REELLEMENT indexe.

Il ne vivait que dans `.git/hooks/`, donc perdu a chaque clone et absent de
toute sauvegarde. Cette copie versionnee corrige cela.

## Installation

    cp tools/hooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Ou, une fois pour toutes :

    git config core.hooksPath tools/hooks

## Contournement

Delibere, a taper en entier :

    EIDOLON_ALLOW_CLOSED_CORE=i-have-read-IP-BOUNDARY git commit ...

## Ou va le coeur ferme

Depot prive `C:/Logos/eidolon-core.git`, sauvegarde sur la branche `core`
de `Oykdo/Eidolon` (prive). Voir IP-BOUNDARY.md.
