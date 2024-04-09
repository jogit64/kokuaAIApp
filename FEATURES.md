# ACTU

- **API Flask avec CORS activé** : Configuration pour accepter les requêtes cross-origin depuis des domaines spécifiques.
- **Sessions Flask** : Suivi des utilisateurs avec des sessions uniques via `session['session_id']`.
- **Base de données PostgreSQL avec SQLAlchemy** : Stockage et gestion des conversations et messages.
- **Support des Fichiers .docx** : Traitement et analyse des fichiers .docx soumis par les utilisateurs.
- **Intégration OpenAI** : Utilisation de l'API OpenAI pour générer des réponses basées sur l'historique des conversations.

# LIMITES

- Accumulation des données dans PostgreSQL sans procédure de vidage.
- Absence d'authentification pour un suivi personnalisé de l'historique utilisateur.

# EVOLUTIONS POSSIBLES

# A FAIRE

- Modularité : Séparer le code en modules communs et spécifiques pour faciliter la duplication et la personnalisation de l'application.
- Examiner l'impact des politiques des navigateurs sur les cookies tiers.

# FAIT

- [x] Configuration initiale de Flask et SQLAlchemy.
- [x] Mise en place de la reconnaissance et du traitement des fichiers .docx.
- [x] Intégration initiale avec l'API OpenAI pour la génération de réponses.
- [x] Documentation pour REPLICATION.

# A FAIRE

- [ ] Améliorer l'historique des conversations pour augmenter la pertinence des réponses générées.
- [ ] Renforcer la sécurité et le nettoyage des sessions utilisateurs.
- [ ] Optimiser le traitement des fichiers pour supporter d'autres formats.
- [ ] Design UX.

# Tags Associés

- `v1.0` : Première version stable avec gestion des sessions, support de fichiers .docx, et intégration OpenAI.
