# Assistant AI Flask Application

Cette application Flask sert d'interface pour interagir avec l'API OpenAI, permettant aux utilisateurs de poser des questions via une interface web ou API et de recevoir des réponses générées par GPT-3.5 Turbo. L'application est conçue pour être utilisée conjointement avec le [plugin WordPress MonAssistantAIPlugin](https://github.com/jogit64/MonAssistantAIPlugin-V1), permettant une intégration transparente dans un site WordPress.

## Fonctionnalités

- Interface API pour poser des questions et recevoir des réponses de GPT-3.5 Turbo.
- Support des sessions pour garder un historique des interactions par utilisateur.
- Sécurisation des cookies de session et configuration pour les requêtes cross-origin (CORS).

## Prérequis

- Python 3.6+.
- Flask.
- Une clé API valide pour OpenAI.

## Installation

1. Clonez ce dépôt sur votre machine locale :

   ```bash
   git clone https://votre-repo.git
   cd chemin-vers-votre-application
   ```

2. Créez un environnement virtuel et activez-le :

   ```bash
   python -m venv venv
   . venv/bin/activate  # Sur Windows : venv\Scripts\activate
   ```

3. Installez les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

4. Définissez votre clé API OpenAI comme variable d'environnement :

   ```bash
   export OPENAI_API_KEY="votre_clé_api"
   ```

   Sur Windows, utilisez `set` au lieu de `export`.

5. Lancez l'application :

   ```bash
   flask run
   ```

## Utilisation avec le Plugin WordPress

Pour intégrer cette application Flask dans votre site WordPress, utilisez le plugin [MonAssistantAIPlugin](https://github.com/jogit64/MonAssistantAIPlugin-V1). Ce plugin permet d'afficher le widget de l'application Flask directement sur votre site WordPress.

## Configuration CORS

Les requêtes cross-origin sont configurées pour être acceptées seulement depuis `https://www.goodyesterday.com`. Modifiez cette configuration dans le code selon vos besoins.

## Sécurité

L'application utilise des configurations de sécurité pour les cookies de session. Assurez-vous de comprendre ces paramètres et de les adapter à votre environnement de déploiement.

## Licence

Incluez ici les informations de licence de votre projet.

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
