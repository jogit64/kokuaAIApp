
from flask import Flask, render_template, request, session, jsonify  

from openai import OpenAI
import os
from flask_cors import CORS

import markdown2 

app = Flask(__name__)

CORS(app, supports_credentials=True, origins=['https://kokua.fr', 'https://www.kokua.fr'])


app.secret_key = 'assistant-ai-1a-urrugne-64122'  # Définissez une clé secrète pour les sessions




app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

# Initialisez l'extension Flask-Session ou une autre gestion de session ici...
# Session(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# Consignes détaillées pour guider les réponses de ChatGPT
chatgpt_guidelines = """
## Analyse et Traitement d’Entretiens
### Contexte: Expertise CHSCT et CSE
### Connaissances requises: Rapports d’expertise CHSCT et CSE, normes de l'INRS et de l'ANACT
### Objectif: Mise au propre de notes sur les conditions de travail et la prévention des risques professionnels, avec exhaustivité sans ajout d'interprétations ou de créativité.
### Instructions: Transformer les notes brutes en compte-rendu structuré, clair et exhaustif. Récapitulatif sous forme de bullet points des vigilances pour la prévention des risques professionnels. Identifier les personnes pour s'entretenir et les points à aborder.
""".strip()


@app.route('/')
def home():
    session['message_history'] = []
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.form['question']
    message_history = session.get('message_history', [])
    message_history.append({"role": "user", "content": question})
    
    # Intégration des consignes dans la requête
    prompt_text = f"{chatgpt_guidelines}\n\nQuestion: {question}\n\nRéponse:"
    
    chat_completion = client.chat.completions.create(
        messages=message_history,
        model="gpt-3.5-turbo",
        temperature=0.0,  # Réduit la créativité
        max_tokens=1024,  # Limite la longueur de la réponse
        prompt=prompt_text  # Inclut les consignes et la question dans le prompt
    )
    
    response_chatgpt = chat_completion.choices[0].message.content
    response_html = markdown2.markdown(response_chatgpt)
    
    message_history.append({"role": "assistant", "content": response_chatgpt})
    session['message_history'] = message_history
    session.modified = True
    
    return jsonify({"response": response_html})

if __name__ == '__main__':
    app.run(debug=True)
