from flask import Flask, render_template, request, session, jsonify
from openai import OpenAI
import os
from flask_cors import CORS
import markdown2
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['https://kokua.fr', 'https://www.kokua.fr'])
app.secret_key = 'assistant-ai-1a-urrugne-64122'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def home():
    session['message_history'] = []  # Réinitialise l'historique pour chaque nouvelle session
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    # Le reste de votre fonction ask_question reste inchangé
    ...

@app.route('/ask_file', methods=['POST'])
def ask_file():
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('temp_directory', filename)  # Assurez-vous que ce répertoire existe
        file.save(file_path)
        
        # Lire le contenu du fichier
        with open(file_path, 'r', encoding='utf-8') as file_content:
            file_text = file_content.read()
        
        # Envoyer le contenu du fichier à GPT pour analyse
        instructions = """
        # Analyse et Traitement d’Entretiens 
        ## Contexte: Expertise CHSCT et CSE
        ...
        ## Analyse et traitement: Transformer les notes brutes en un compte-rendu structuré et clair, sans ajouter d'interprétations ou de créativité.
        """
        response = client.chat.completions.create(
            prompt=instructions + "\n\n" + file_text,  # Ajoutez le contenu du fichier après les instructions
            model="text-davinci-003",  # Assurez-vous de sélectionner le bon modèle
            temperature=0.5,
            max_tokens=1024,  # Ajustez en fonction de la taille de sortie désirée
        )
        
        response_text = response.choices[0].text.strip()
        response_html = markdown2.markdown(response_text)
        
        # Supprime le fichier après traitement
        os.remove(file_path)
        
        return jsonify({"response": response_html})
        
    return jsonify({"error": "Aucun fichier reçu"}), 400

if __name__ == '__main__':
    app.run(debug=True)
