# Pokemon TCG Tracker

Suivi automatique des matchs de Pokemon TCG Pocket via capture d'écran.
Compatible avec n'importe quel émulateur Android (MuMu, BlueStacks, LDPlayer…).

---

## Prérequis

- **Windows 10/11**
- **Python 3.10 ou plus** → [python.org/downloads](https://www.python.org/downloads/)
  - ⚠️ Coche **"Add Python to PATH"** lors de l'installation
- **Git** (optionnel, pour les mises à jour) → [git-scm.com](https://git-scm.com)

---

## Installation & premier lancement

### Option A — Télécharger le ZIP (sans Git)

1. Sur cette page GitHub, clique **Code → Download ZIP**
2. Extrais le dossier où tu veux (ex: `C:\Pokemon TCG Tracker`)
3. Double-clique sur **`launch.bat`**
   - Il crée automatiquement l'environnement Python et installe les dépendances
   - ⏳ La première fois prend 2 à 5 minutes
4. L'icône du tracker apparaît dans la **barre des tâches système** (à côté de l'horloge)
5. Double-clique sur l'icône pour ouvrir le dashboard

### Option B — Via Git (recommandé pour les mises à jour)

```bat
git clone https://github.com/Gwendal9/pokemon-tcg-tracker.git
cd pokemon-tcg-tracker
launch.bat
```

---

## Créer un raccourci Bureau

Après le premier lancement réussi :

1. Double-clique sur **`create_shortcut.bat`**
2. Un raccourci **"Pokemon TCG Tracker"** apparaît sur ton Bureau

---

## Lancer l'application

- **Double-clique sur `launch.bat`** ou sur le raccourci Bureau
- L'icône apparaît dans la barre des tâches système
- Double-clique dessus → ouvre le dashboard
- **Fermer la fenêtre** = réduit dans le tray (l'appli continue de tourner)
- **Quitter** = clic droit sur l'icône → Quitter

---

## Configuration initiale

Au premier lancement, va dans l'onglet **Config** :

1. **Fenêtre à capturer** → clique **"Choisir une fenêtre"** → une liste de toutes les fenêtres ouvertes s'affiche → clique sur ton émulateur. Un cadre rouge confirme la zone sélectionnée.
   - Si ton émulateur n'apparaît pas, utilise **"Sélection manuelle"** pour dessiner la zone à la souris.
2. **Crée tes decks** dans l'onglet **Decks** (bouton + en haut à droite)
3. **Deck actif** → sélectionne le deck que tu joues actuellement
4. **Test de capture** → vérifie que l'image de l'émulateur s'affiche correctement

### Modèle de détection automatique

Le modèle ML (`models/state_classifier.pkl`) est inclus dans le téléchargement — aucune étape supplémentaire n'est nécessaire.

**Sans le modèle** : tu peux toujours utiliser la saisie manuelle (bouton **+ Match**) et toutes les fonctionnalités de stats.

---

## Détection automatique du deck

Le tracker détecte automatiquement quel deck tu joues depuis l'écran "C'est parti !" :

1. Lance une partie — le tracker lit le nom et la couleur d'énergie de ton deck
2. Va dans **Config → Détection de deck** : le deck détecté apparaît dans la liste
3. Clique sur **"Lier"** et sélectionne le deck correspondant dans tes decks
4. À partir de là, le deck s'active automatiquement au début de chaque match

Tu peux aussi cliquer **"Tester maintenant"** si tu es sur l'écran "C'est parti !" pour voir ce que le tracker détecte.

---

## Fonctionnalités

### Dashboard
| Fonctionnalité | Description |
|---|---|
| KPI cards | Winrate global, matchs joués, victoires/défaites, série en cours |
| Filtre par saison | Persisté entre sessions |
| Graphiques | Winrate par deck, tendance cumulée, top 10 adversaires |
| Thème | Clair / sombre |

### Historique
| Fonctionnalité | Description |
|---|---|
| Table des matchs | Filtres résultat, deck, adversaire, date, tags |
| Recherche | Par adversaire, deck ou notes |
| Édition inline | Résultat, adversaire, premier joueur, notes |
| Colonnes | Date, résultat, deck, adversaire, premier, score, tours, dégâts, énergie |
| Indicateurs | Badge "Abandon adv." si l'adversaire a abandonné, "Abandon" si tu as abandonné |
| Export CSV | Ouvre le fichier automatiquement |

### Saisie & gestion
| Fonctionnalité | Description |
|---|---|
| Saisie manuelle | Bouton **+ Match** dans la navbar |
| Gestion des decks | Créer, renommer, supprimer |
| Stats matchup | Clic sur un adversaire → stats détaillées |
| Notifications | Toast à chaque match enregistré automatiquement |

### Capture automatique (nécessite le modèle ML)
| Fonctionnalité | Description |
|---|---|
| Détection d'émulateur | Fonctionne avec n'importe quel émulateur Android |
| Détection des états | Pré-queue / en combat / fin de match |
| Enregistrement automatique | Résultat W/L, adversaire, premier joueur, score, tours, dégâts |
| Détection du deck | Lit le nom et le type d'énergie depuis l'écran "C'est parti !" |
| Détection abandon | Détecte automatiquement "Votre adversaire a abandonné" |

### Système
| Fonctionnalité | Description |
|---|---|
| Icône tray | Hide on close, double-clic pour rouvrir |
| Backup automatique | Sauvegarde de la base de données au démarrage |
| Mises à jour | Vérifie automatiquement au démarrage, affiche une bannière |

---

## Saisie manuelle de match

Clique sur **+ Match** dans la barre de navigation pour enregistrer un match sans capture automatique.
Champs disponibles : résultat, deck joué, adversaire, premier à jouer, saison, notes.

---

## Mise à jour

Si tu as installé via Git :

```bat
git pull
launch.bat
```

Si tu as installé via ZIP : retélécharge le ZIP et remplace les fichiers.
Le dossier `data/` dans `AppData\Local\pokemon-tcg-tracker\` contient ta base de données — ne le supprime pas.

L'application vérifie aussi automatiquement les mises à jour au démarrage et affiche une bannière si une nouvelle version est disponible.

---

## Logs & debug

Les logs sont dans `%LOCALAPPDATA%\pokemon-tcg-tracker\data\app.log`.

Pour lancer en mode debug (logs détaillés) :

```bat
set PTCG_DEBUG=1
launch.bat
```
