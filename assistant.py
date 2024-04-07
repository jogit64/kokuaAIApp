from flask import Flask, render_template, request, session, jsonify
from openai import OpenAI
import os
from flask_cors import CORS
import markdown2
from docx import Document

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

    # Instructions spécifiques pour l'analyse et le traitement
    instructions = """
    # Analyse et Traitement d’Entretiens 
    ## Contexte: Expertise CHSCT et CSE
    ## Connaissances: Les rapports d’expertise CHSCT et CSE réalisés au profit des élus représentants du personnel. Les normes de l'INRS et de l'ANACT.
    ## Objectif: Mise au propre de notes, objectif exhaustivité.
    ## Analyse et traitement: Transformer les notes brutes en un compte-rendu structuré et clair, sans ajouter d'interprétations ou de créativité.
    """

    message_history = session.get('message_history', [])
    message_history.append({"role": "system", "content": instructions})
    if question:
        message_history.append({"role": "user", "content": question})

    if uploaded_file:
    file_content = ""
    try:
        # Déterminer le type de fichier et le lire en conséquence
        if uploaded_file.filename.endswith('.docx'):
            # Tente de lire le fichier .docx
            document = Document(io.BytesIO(uploaded_file.read()))
            file_content = "\n".join([paragraph.text for paragraph in document.paragraphs])
        else:
            # Traitement simplifié pour les autres types de fichiers
            file_content = uploaded_file.read().decode('utf-8')
    except Exception as e:
        # Log l'erreur ou renvoie une réponse appropriée
        app.logger.error(f"Erreur lors du traitement du fichier : {e}")
        return jsonify({"error": "Le traitement du fichier a échoué.", "details": str(e)}), 400

    message_history.append({"role": "user", "content": "Uploaded File"})
    message_history.append({"role": "user", "content": file_content})

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

if __name__ == '__main__':
    app.run(debug=True)

