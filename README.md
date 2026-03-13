# Pokemon TCG Tracker

Suivi automatique des matchs **Pokemon TCG Pocket** via capture d'écran.
Compatible avec tous les émulateurs Android (MuMu, BlueStacks, LDPlayer…).

---

## Aperçu

![Dashboard](docs/screenshots/dashboard.png)

*Dashboard principal — KPI, graphiques winrate et top adversaires*

---

## Prérequis

| | |
|---|---|
| **OS** | Windows 10 ou 11 |
| **Python** | 3.10 ou plus — [télécharger](https://www.python.org/downloads/) · cocher **"Add Python to PATH"** |
| **Git** | Optionnel, pour les mises à jour — [télécharger](https://git-scm.com) |

---

## Installation

### Téléchargement ZIP (simple)

1. Clique **Code → Download ZIP** sur cette page
2. Extrais le dossier (ex. `C:\Pokemon TCG Tracker`)
3. Double-clique **`launch.bat`** — installe automatiquement les dépendances
   *(première fois : 2 à 5 minutes)*
4. L'icône du tracker apparaît dans la **barre des tâches** (à côté de l'horloge)

### Via Git (recommandé pour les mises à jour)

```bat
git clone https://github.com/Gwendal9/pokemon-tcg-tracker.git
cd pokemon-tcg-tracker
launch.bat
```

> **Raccourci Bureau** — double-clique `create_shortcut.bat` après le premier lancement.

---

## Configuration initiale

![Config](docs/screenshots/config.png)

*Onglet Config — sélection de la fenêtre émulateur et gestion des decks*

Ouvre l'onglet **Config** au premier lancement :

1. **Fenêtre à capturer** → clique **"Choisir une fenêtre"** → sélectionne ton émulateur dans la liste.
   Un cadre rouge confirme la sélection. Si l'émulateur n'apparaît pas, utilise **"Sélection manuelle"** pour dessiner la zone.
2. **Decks** → crée tes decks dans l'onglet **Decks** (bouton **+**)
3. **Deck actif** → sélectionne le deck en cours

Le modèle de détection (`models/state_classifier.pkl`) est **inclus dans le téléchargement** — aucune installation supplémentaire.

---

## Capture automatique

Le tracker détecte en temps réel l'état du jeu et enregistre chaque match automatiquement :

- **File d'attente** → lit le nom du deck et le type d'énergie
- **Fin de match** → lit le résultat, l'adversaire, le premier joueur, le score, les tours et les dégâts
- **Abandon adverse** → détecté automatiquement

### Associer un deck détecté

![Détection deck](docs/screenshots/deck_detection.png)

*Liaison automatique entre le nom détecté OCR et ton deck*

1. Lance une partie — le tracker lit le nom et le type d'énergie de ton deck depuis l'écran de file d'attente
2. Dans **Config → Détection de deck**, le deck détecté apparaît dans la liste
3. Clique **"Lier"** et sélectionne le deck correspondant
4. À partir de là, le deck s'active automatiquement à chaque match

---

## Fonctionnalités

### Dashboard

![Dashboard graphiques](docs/screenshots/dashboard_charts.png)

*Graphiques — winrate par deck, tendance sur les derniers matchs, top adversaires*

- KPI : winrate, matchs joués, série en cours
- Graphiques : winrate par deck, tendance, top adversaires, répartition énergie
- Filtre par saison · thème clair/sombre

### Historique

![Historique](docs/screenshots/history.png)

*Tableau historique — toutes les colonnes et filtres*

- Filtres : résultat, deck, adversaire, date, tags
- Recherche globale (adversaire, deck, notes)
- Édition inline des matchs
- Colonnes : date · résultat · deck · adversaire · premier · score · tours · dégâts · énergie
- Indicateurs d'abandon (adversaire ou soi-même)
- Export CSV

### Saisie manuelle

Bouton **+ Match** dans la navbar — résultat, deck, adversaire, premier joueur, saison, notes.

---

## Utilisation

| Action | Comment |
|---|---|
| Ouvrir le dashboard | Double-clique sur l'icône dans le tray |
| Réduire | Ferme la fenêtre (l'appli continue en arrière-plan) |
| Quitter | Clic droit sur l'icône → **Quitter** |

---

## Mise à jour

**Via Git :**
```bat
git pull
launch.bat
```

**Via ZIP :** retélécharge le ZIP et remplace les fichiers.
Tes données sont dans `%LOCALAPPDATA%\pokemon-tcg-tracker\data\` — ne supprime pas ce dossier.

> Le tracker vérifie automatiquement les mises à jour au démarrage.

---

## Logs & debug

Fichier de log : `%LOCALAPPDATA%\pokemon-tcg-tracker\data\app.log`

Mode debug (logs détaillés) :
```bat
set PTCG_DEBUG=1
launch.bat
```
