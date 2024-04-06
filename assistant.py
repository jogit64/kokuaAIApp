from flask import Flask, render_template, request, session, jsonify
from openai import OpenAI
import os
from flask_cors import CORS
import markdown2

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
    question = request.form['question']
    message_history = session.get('message_history', [])

    # Instructions spécifiques pour l'analyse et le traitement
    instructions = """
    # Analyse et Traitement d’Entretiens 
    ## Contexte: Expertise CHSCT et CSE
    ## Connaissances: Les rapports d’expertise CHSCT et CSE réalisés au profit des élus représentants du personnel. Les normes de l'INRS et de l'ANACT.
    ## Objectif: Mise au propre de notes, objectif exhaustivité.
    ## Analyse et traitement: Transformer les notes brutes en un compte-rendu structuré et clair, sans ajouter d'interprétations ou de créativité.
    """
    # Ajoute les instructions et la nouvelle question à l'historique des messages
    message_history.append({"role": "system", "content": instructions})
    message_history.append({"role": "user", "content": question})

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
