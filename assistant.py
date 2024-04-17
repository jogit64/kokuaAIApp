from flask import Flask, render_template, request, jsonify, session, make_response
from openai import OpenAI
import os
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import markdown2
from docx import Document
import fitz  # PyMuPDF
import openpyxl
from pptx import Presentation
import io
from flask_migrate import Migrate
import uuid
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, session
from flask_session import Session
import redis
import json

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

redis_url = os.environ.get('REDISCLOUD_URL')
if redis_url:
    app.config['SESSION_REDIS'] = redis.from_url(redis_url)
else:
    raise ValueError("REDISCLOUD_URL is not set in the environment variables.")

Session(app)

CORS(app, supports_credentials=True, origins=['https://kokua.fr', 'https://www.kokua.fr'])
# CORS(app, supports_credentials=True, origins='*')

app.secret_key = 'assistant-ai-1a-urrugne-64122'  

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("://", "ql://", 1) # Remplacez pour corriger l'URL pour PostgreSQL
# Exemple de configuration temporaire pour la génération des migrations
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temp.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)




app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Text, unique=True, nullable=False)
    derniere_activite = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True)



class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # "system", "user", ou "assistant"
    content = db.Column(db.Text, nullable=False)


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def nettoyer_conversations_inactives():
    limite_inactivite = datetime.now() - timedelta(days=30)  # Exemple: 30 jours d'inactivité
    conversations_inactives = Conversation.query.filter(Conversation.derniere_activite < limite_inactivite).all()
    for conversation in conversations_inactives:
        db.session.delete(conversation)
    db.session.commit() 

scheduler = BackgroundScheduler()
scheduler.add_job(func=nettoyer_conversations_inactives, trigger="interval", days=1)  # Exécute tous les jours
scheduler.start()



def read_file_content(uploaded_file):
    file_type = uploaded_file.filename.split('.')[-1]
    if file_type == 'docx':
        document = Document(io.BytesIO(uploaded_file.read()))
        return "\n".join([paragraph.text for paragraph in document.paragraphs])
    elif file_type == 'pdf':
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    elif file_type == 'txt':
        return uploaded_file.read().decode('utf-8')
    elif file_type == 'xlsx':
        workbook = openpyxl.load_workbook(io.BytesIO(uploaded_file.read()))
        sheet = workbook.active
        data = []
        for row in sheet.iter_rows(values_only=True):
            data.append(' '.join([str(cell) for cell in row if cell is not None]))
        return "\n".join(data)
    elif file_type == 'pptx':
        ppt = Presentation(io.BytesIO(uploaded_file.read()))
        text = []
        for slide in ppt.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)
    else:
        raise ValueError("Unsupported file type")
    


@app.route('/')
def home(): 
    # session['message_history'] = []  # Réinitialise l'historique pour chaque nouvelle session
    return render_template('index.html')


# @app.route('/set-test-cookie') 
# def set_test_cookie():
#     response = make_response("Cookie Set")
#     response.set_cookie('test', 'chez jouni', secure=True, samesite='None', domain='.kokua.fr')
#     return response



@app.route('/reset-session', methods=['POST'])
def reset_session():
    session.pop('session_id', None)  # Supprime l'ID de session actuel
    return jsonify({"message": "Session réinitialisée"}), 200



@app.route('/ask', methods=['POST'])
@app.route('/ask', methods=['POST'])
def ask_question():
    # Charges les modèles et instructions GPT.
    with open('gpt_config.json', 'r') as f:
        gpt_configs = json.load(f)

    
    # Récupération de la valeur de config sélectionnée par l'utilisateur
    config_key = request.form.get('config')
    
    # # Sélection de la configuration GPT basée sur la valeur de config
    # if config_key not in gpt_configs:
    #     return jsonify({"error": "Configuration non valide."}), 400
    # gpt_config = gpt_configs[config_key]
    
    
    # Sélection de la configuration GPT basée sur la valeur de config
    if config_key not in gpt_configs:
        gpt_config = {
        "model": "gpt-3.5-turbo",
        "temperature": 0.2,
        "max_tokens": 500,
        "instructions": "Votre première réponse doit commencer par 'STAN :'",
        "top_p": 1,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.5
    }

    else:
        gpt_config = gpt_configs[config_key]

    
    # S'assure que session_id existe dans la session Flask, sinon en crée un nouveau.
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    session_id = session['session_id']

    try:
        conversation = Conversation.query.filter_by(session_id=session_id).first()
        if not conversation:
            conversation = Conversation(session_id=session_id, derniere_activite=datetime.utcnow())
            db.session.add(conversation)
        else:
            conversation.derniere_activite = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erreur lors de la gestion de la conversation : {e}")
        return jsonify({"error": "Un problème est survenu lors de la gestion de la conversation"}), 500
    
    question = request.form.get('question')
    uploaded_file = request.files.get('file')
    
    # Ajout de l'instruction initiale spécifique au GPT
    instructions_content = gpt_config['instructions']
    instructions_message = Message(conversation_id=conversation.id, role="system", content=instructions_content)
    db.session.add(instructions_message)
    
    # Traitement de la question de l'utilisateur
    if question:
        question_message = Message(conversation_id=conversation.id, role="user", content=question)
        db.session.add(question_message)

    # Traitement du fichier téléchargé
    if uploaded_file and uploaded_file.filename:
      if uploaded_file and uploaded_file.filename:
        try:
            file_content = read_file_content(uploaded_file)
            uploaded_file_message = Message(conversation_id=conversation.id, role="user", content="Uploaded File: " + uploaded_file.filename)
            db.session.add(uploaded_file_message)
            file_content_message = Message(conversation_id=conversation.id, role="user", content=file_content)
            db.session.add(file_content_message)
            db.session.commit()
            # Continue processing and send to OpenAI
        except ValueError as e:  # Catch the ValueError raised by read_file_content
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": "Error processing file: " + str(e)}), 500

    db.session.commit()

    # Préparation des messages pour OpenAI
    db_messages = Message.query.filter_by(conversation_id=conversation.id).all()
    messages_for_openai = [{"role": msg.role, "content": msg.content} for msg in db_messages]

    # Envoi à OpenAI et génération de la réponse
    if question or uploaded_file:
        try:
            chat_completion = client.chat.completions.create(
                model=gpt_config['model'],
                messages=messages_for_openai,
                temperature=gpt_config['temperature'],
                max_tokens=gpt_config['max_tokens'],
                top_p=gpt_config['top_p'],
                frequency_penalty=gpt_config['frequency_penalty'],
                presence_penalty=gpt_config['presence_penalty']
            )
            response_chatgpt = chat_completion.choices[0].message.content

            response_message = Message(conversation_id=conversation.id, role="assistant", content=response_chatgpt)
            db.session.add(response_message)
            db.session.commit()

            response_html = markdown2.markdown(response_chatgpt)
            db.session.close()
            return jsonify({"response": response_html})
        except Exception as e:
            app.logger.error(f"Erreur lors de la génération de la réponse : {e}")
            return jsonify({"error": "Erreur lors de la génération de la réponse.", "details": str(e)}), 500
    else:
        return jsonify({"error": "Aucune question ou fichier fourni."}), 400

if __name__ == '__main__':
    app.run(debug=True)
