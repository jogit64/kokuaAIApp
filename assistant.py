from flask import Flask, render_template, request, jsonify, session, make_response, current_app
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
from flask_session import Session
from redis import Redis
from rq import Queue
import json

app = Flask(__name__)
app.secret_key = 'assistant-ai-1a-urrugne-64122'  # Assurez-vous de garder votre secret key sécurisée et unique
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

# Utiliser Redis pour les sessions et les tâches en file d'attente
redis_url = os.getenv('REDISCLOUD_URL')
if not redis_url:
    raise RuntimeError("REDIS_URL not set in the environment variables.")

redis_instance = Redis.from_url(redis_url)

# Tester la connexion à Redis test
try:
    redis_instance.ping()
    print("Connected to Redis successfully!")
except Exception as e:
    print(f"Failed to connect to Redis: {str(e)}")

app.config['SESSION_REDIS'] = redis_instance
Session(app)

q = Queue(connection=redis_instance)

CORS(app, supports_credentials=True, origins=['https://kokua.fr', 'https://www.kokua.fr'])

 

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("://", "ql://", 1) # Remplacez pour corriger l'URL pour PostgreSQL
# Exemple de configuration temporaire pour la génération des migrations
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temp.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)






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






# ! mise en place de rq test
@app.route('/ask', methods=['POST'])
def ask_question():
    data = {
        "config_key": request.form.get('config', 'default_config'),
        "question": request.form.get('question'),
        "session_id": session.get('session_id', str(uuid.uuid4())),
        "file_content": read_file_content(request.files.get('file')) if request.files.get('file') else None
    }
    app.logger.info(f"Requête reçue à /ask avec données : {data}")
    job = q.enqueue(process_ask_question, data)
    return jsonify({"job_id": job.get_id()}), 202

def process_ask_question(data):
    # Obtention de l'instance de l'application Flask
    app = current_app._get_current_object()

    with app.app_context():
        app.logger.info("Début du traitement de la requête avec data: {}".format(data))
        try:
            # Chargement de la configuration GPT depuis un fichier JSON
            with open('gpt_config.json', 'r') as f:
                gpt_configs = json.load(f)
            
            gpt_config = gpt_configs.get(data.get('config_key'), {
                "model": "gpt-3.5-turbo",
                "temperature": 0.2,
                "max_tokens": 500,
                "instructions": "Votre première réponse doit commencer par 'STAN :'",
                "top_p": 1,
                "frequency_penalty": 0.5,
                "presence_penalty": 0.5
            })

            session_id = data['session_id']
            conversation = Conversation.query.filter_by(session_id=session_id).first()
            if not conversation:
                conversation = Conversation(session_id=session_id, last_activity=datetime.utcnow())
                db.session.add(conversation)
            else:
                conversation.last_activity = datetime.utcnow()
            db.session.commit()

            # Traitement des messages et des fichiers téléchargés
            process_messages(data, conversation)

            # Préparation et envoi des données à OpenAI
            db_messages = Message.query.filter_by(conversation_id=conversation.id).all()
            messages_for_openai = [{"role": msg.role, "content": msg.content} for msg in db_messages]
            response_html = handle_openai_request(gpt_config, messages_for_openai, conversation)
            db.session.close()
            return {"response": response_html}
        except Exception as e:
            app.logger.error(f"Erreur lors du traitement de la requête : {e}")
            return {"error": "Erreur lors de la génération de la réponse.", "details": str(e)}

def process_messages(data, conversation):
    if data['question']:
        question_message = Message(conversation_id=conversation.id, role="user", content=data['question'])
        db.session.add(question_message)
    if data.get('file_content'):
        file_messages = [
            Message(conversation_id=conversation.id, role="user", content="Uploaded File: Provided"),
            Message(conversation_id=conversation.id, role="user", content=data['file_content'])
        ]
        db.session.extend(file_messages)
    db.session.commit()

def handle_openai_request(gpt_config, messages_for_openai, conversation):
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

    # Enregistrement de la réponse de l'assistant
    response_message = Message(conversation_id=conversation.id, role="assistant", content=response_chatgpt)
    db.session.add(response_message)
    db.session.commit()

    return markdown2.markdown(response_chatgpt)

@app.route('/results/<job_id>', methods=['GET'])
def get_results(job_id):
    job = q.fetch_job(job_id)
    if job.is_finished:
        return jsonify(job.result), 200
    elif job.is_failed:
        return jsonify({"error": "La tâche a échoué", "details": str(job.exc_info)}), 500
    else:
        return jsonify({"status": "En cours..."}), 202

if __name__ == '__main__':
    db.init_app(app)
    app.run(debug=True)
