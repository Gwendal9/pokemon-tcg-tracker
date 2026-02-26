# Pokemon TCG Tracker

Suivi automatique des matchs ranked de Pokemon TCG Pocket via capture d'écran MuMu Player.

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

1. **Région MUMU** → Clique "Configurer la région MUMU" et sélectionne la zone de jeu
2. **Deck actif** → Choisis le deck que tu joues
3. **Test de capture** → Vérifie que la capture fonctionne

---

## Fonctionnalités

| Fonctionnalité | Statut |
|---|---|
| Gestion des decks (créer, renommer, supprimer) | ✅ |
| Configuration région MuMu Player | ✅ |
| Dashboard : winrate, stats, graphiques | ✅ |
| Historique des matchs avec filtres | ✅ |
| Édition et suppression de matchs | ✅ |
| Panneau détail adversaires / decks | ✅ |
| Capture automatique des matchs | 🔧 En cours de calibration |

> La capture automatique détecte MuMu Player mais nécessite encore une calibration
> des états de jeu. En attendant, les matchs peuvent être ajoutés manuellement.

---

## Mise à jour

Si tu as installé via Git :

```bat
git pull
launch.bat
```

---

## Logs

Les logs sont dans `data/app.log`. En cas de bug, consulte ce fichier.

Pour lancer en mode debug (logs détaillés) :

```bat
set PTCG_DEBUG=1
launch.bat
```
