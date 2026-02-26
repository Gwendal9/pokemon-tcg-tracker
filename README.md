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
2. **Deck actif** → Choisis le deck que tu joues actuellement
3. **Test de capture** → Vérifie que la capture fonctionne
4. **Calibration** → Pour chaque état (pré-queue, combat, fin de match), lance le jeu dans cet état et clique "Calibrer"

---

## Fonctionnalités

### Dashboard
| Fonctionnalité | Statut |
|---|---|
| 4 KPI cards : winrate global, matchs joués, victoires/défaites, série en cours | ✅ |
| Filtre par saison (persisté entre sessions) | ✅ |
| Graphique winrate par deck (barres) | ✅ |
| Courbe de tendance winrate cumulatif | ✅ |
| Graphique top 10 adversaires (barres horizontales W/L) | ✅ |
| Thème clair / sombre | ✅ |

### Historique
| Fonctionnalité | Statut |
|---|---|
| Table des matchs avec filtres (résultat, deck, adversaire) | ✅ |
| Recherche textuelle par nom d'adversaire | ✅ |
| Édition inline (résultat, adversaire, premier joueur) | ✅ |
| Suppression de match avec confirmation | ✅ |
| Export CSV (ouvre le fichier automatiquement) | ✅ |

### Saisie & gestion
| Fonctionnalité | Statut |
|---|---|
| Saisie manuelle de match (+ bouton dans la navbar) | ✅ |
| Gestion des decks : créer, renommer, supprimer (avec confirmation) | ✅ |
| Panneau détail slide-in : stats adversaires, stats decks | ✅ |
| Toast notification à chaque match enregistré | ✅ |

### Capture automatique
| Fonctionnalité | Statut |
|---|---|
| Détection MuMu Player | ✅ |
| Calibration des états de jeu (pré-queue / combat / fin de match) | ✅ |
| Enregistrement automatique du résultat W/L en fin de match | ✅ (nécessite calibration) |
| Détection automatique du deck adverse | ❌ Pas encore implémenté |

### Système
| Fonctionnalité | Statut |
|---|---|
| Icône tray (hide on close, double-clic pour rouvrir) | ✅ |
| Vérification de mise à jour au démarrage (bannière GitHub) | ✅ |

---

## Saisie manuelle de match

Clique sur **+ Match** dans la barre de navigation pour enregistrer un match sans capture automatique.
Champs disponibles : résultat, deck joué, adversaire, premier à jouer, saison.

---

## Mise à jour

Si tu as installé via Git :

```bat
git pull
launch.bat
```

L'application vérifie aussi automatiquement les mises à jour au démarrage et affiche une bannière si une nouvelle version est disponible sur GitHub.

---

## Logs

Les logs sont dans `data/app.log`. En cas de bug, consulte ce fichier.

Pour lancer en mode debug (logs détaillés) :

```bat
set PTCG_DEBUG=1
launch.bat
```
