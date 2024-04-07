from flask import Flask, render_template, request, session, jsonify
from openai import OpenAI
import os
from flask_cors import CORS
import markdown2
from docx import Document
import io

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
    question = request.form.get('question')
    uploaded_file = request.files.get('file')
    message_history = session.get('message_history', [])

    # Préparation des instructions et ajout à l'historique des messages
    instructions = """
    # Analyse et Traitement d’Entretiens 
    ## Contexte: Expertise CHSCT et CSE
    ## Connaissances: Les rapports d’expertise CHSCT et CSE réalisés au profit des élus représentants du personnel. Les normes de l'INRS et de l'ANACT.
    ## Objectif: Mise au propre de notes, objectif exhaustivité.
    ## Analyse et traitement: Transformer les notes brutes en un compte-rendu structuré et clair, sans ajouter d'interprétations ou de créativité.
    """
    message_history.append({"role": "system", "content": instructions})

    if question:
        message_history.append({"role": "user", "content": question})

    file_content = ""
    if uploaded_file and uploaded_file.filename:  # Vérifie si un fichier a été téléchargé
        try:
            if uploaded_file.filename.endswith('.docx'):
                document = Document(io.BytesIO(uploaded_file.read()))
                file_content = "\n".join([paragraph.text for paragraph in document.paragraphs])
                message_history.append({"role": "user", "content": "Uploaded File: " + uploaded_file.filename})
                message_history.append({"role": "user", "content": file_content})
            else:
                # Gérer d'autres types de fichiers si nécessaire
                return jsonify({"error": "Type de fichier non pris en charge."}), 400
        except Exception as e:
            app.logger.error(f"Erreur lors du traitement du fichier : {e}")
            return jsonify({"error": "Le traitement du fichier a échoué.", "details": str(e)}), 400

    if not question and not uploaded_file:
        return jsonify({"error": "Aucune question ou fichier fourni."}), 400

    # Génération de la réponse basée sur l'historique des messages
    try:
        chat_completion = client.chat.completions.create(
            messages=message_history,
            model="gpt-3.5-turbo",
        )
        response_chatgpt = chat_completion.choices[0].message.content
        response_html = markdown2.markdown(response_chatgpt)
        message_history.append({"role": "assistant", "content": response_chatgpt})
        session['message_history'] = message_history
        session.modified = True

        return jsonify({"response": response_html})
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération de la réponse : {e}")
        return jsonify({"error": "Erreur lors de la génération de la réponse.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
