Préparation de l'Environnement Local
Créer un Environnement Virtuel Python (si pas déjà fait) :

bash
Copy code
python -m venv venv
Activer l'Environnement Virtuel :

Sur Windows :
bash
Copy code
venv\Scripts\activate
Sur macOS et Linux :
bash
Copy code
source venv/bin/activate
Installer les Dépendances :

Assurez-vous d'avoir un fichier requirements.txt à jour dans votre projet.
Installez les dépendances dans votre environnement virtuel :
bash
Copy code
pip install -r requirements.txt
Initialisation du Projet Git
Initialiser un Dépôt Git (si pas déjà fait) :

bash
Copy code
git init
Ajouter et Commiter les Fichiers au Dépôt :

bash
Copy code
git add .
git commit -m "Initial commit"
Configuration sur Heroku
Créer une Nouvelle Application sur Heroku :

bash
Copy code
heroku create nom_de_votre_application
Définir des Variables d'Environnement sur Heroku :

Pour OpenAI et toute autre configuration nécessaire :
bash
Copy code
heroku config:set OPENAI_API_KEY=votre_clé_api
heroku config:set NOM_VARIABLE=ma_valeur
Ajouter l'Addon PostgreSQL à Votre Application Heroku :

bash
Copy code
heroku addons:create heroku-postgresql:hobby-dev
Cela configurera automatiquement une variable d'environnement DATABASE_URL dans votre application Heroku avec la chaîne de connexion à votre base de données PostgreSQL.
Déploiement sur Heroku
Pousser Votre Application sur Heroku :

bash
Copy code
git push heroku main
Effectuer les Migrations de Base de Données avec Flask-Migrate :

Après le déploiement, exécutez les migrations pour configurer votre base de données PostgreSQL sur Heroku :
bash
Copy code
heroku run flask db upgrade
Chaîne de Connexion PostgreSQL
La chaîne de connexion est une URL qui contient toutes les informations nécessaires pour se connecter à votre base de données PostgreSQL. Sur Heroku, elle est automatiquement définie comme variable d'environnement DATABASE_URL lors de l'ajout de l'addon PostgreSQL. Vous l'utilisez dans votre application pour configurer SQLAlchemy ou tout autre ORM que vous utilisez pour interagir avec PostgreSQL.
Commandes Utiles Additionnelles
Générer un Fichier requirements.txt :

bash
Copy code
pip freeze > requirements.txt
Voir les Logs de votre Application Heroku :

bash
Copy code
heroku logs --tail
Utiliser Flask-Migrate pour Générer et Appliquer des Migrations :

Initialiser les migrations (une fois) :
bash
Copy code
flask db init
Générer une migration après modification des modèles :
bash
Copy code
flask db migrate -m "Description de la migration"
Appliquer les migrations à la base de données :
bash
Copy code
flask db upgrade
Redémarrer Votre Application sur Heroku :

bash
Copy code
heroku restart
Ouvrir votre Application dans le Navigateur :

bash
Copy code
heroku open
En suivant ces étapes, vous devriez être en mesure de répliquer et de configurer de nouvelles instances de votre projet widget + application Flask sur Heroku, y compris la gestion des bases de données PostgreSQL et des variables d'environnement pour la configuration.

---

Commandes PostgreSQL Utiles pour la Gestion de la Base de Données
Si vous avez besoin d'interagir directement avec votre base de données PostgreSQL sur Heroku pour voir l'état des tables, manipuler des données, ou effectuer des ajustements comme ajouter ou supprimer des colonnes, voici quelques commandes et étapes utiles :

Se Connecter à Votre Base de Données PostgreSQL sur Heroku
Obtenir l'URL de Connexion PostgreSQL :

Heroku stocke l'URL de connexion à votre base de données dans une variable d'environnement appelée DATABASE_URL. Vous pouvez la récupérer directement depuis le tableau de bord Heroku ou en utilisant la commande CLI :
bash
Copy code
heroku config:get DATABASE_URL -a nom_de_votre_application
Utiliser heroku pg:psql pour se Connecter :

Heroku fournit une commande pratique pour se connecter directement à votre base de données PostgreSQL depuis votre terminal :
bash
Copy code
heroku pg:psql -a nom_de_votre_application
Cette commande ouvre une session psql avec votre base de données, vous permettant d'exécuter des commandes SQL directement.
Commandes SQL Utiles
Lister toutes les Tables :

sql
Copy code
\dt
Afficher la Structure d'une Table (remplacez nom_de_la_table par le nom réel de votre table) :

sql
Copy code
\d nom_de_la_table
Ajouter une Colonne à une Table :

sql
Copy code
ALTER TABLE nom_de_la_table ADD COLUMN nom_de_la_colonne type_de_donnée;
Supprimer des Données d'une Table :

sql
Copy code
DELETE FROM nom_de_la_table WHERE condition;
Soyez prudent avec cette commande pour éviter de supprimer des données importantes.
Modifier la Structure d'une Table (par exemple, ajouter une contrainte NOT NULL à une colonne) :

sql
Copy code
ALTER TABLE nom_de_la_table ALTER COLUMN nom_de_la_colonne SET NOT NULL;
