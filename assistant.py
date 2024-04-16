from rq import Queue
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
from redis import Redis
import json



app = Flask(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Configuration globale de Redis
redis_url = os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)

# Configurer Redis pour les sessions
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis_conn
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

# Configuration de la file d'attente RQ
queue = Queue(connection=redis_conn)


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
def ask_question():

    uploaded_file = request.files.get('file')
    if uploaded_file and uploaded_file.content_length > MAX_FILE_SIZE:
        return jsonify({"error": "File size exceeds the maximum limit"}), 400

    # Chargement des configurations GPT depuis un fichier JSON
    with open('gpt_config.json', 'r') as f:
        gpt_configs = json.load(f)

    # Récupération et validation de la configuration sélectionnée par l'utilisateur
    config_key = request.form.get('config')
    if config_key not in gpt_configs:
        return jsonify({"error": "Configuration non valide."}), 400
    gpt_config = gpt_configs[config_key]

    # Assure l'existence d'un session_id dans la session Flask, sinon en crée un nouveau
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']

    question = request.form.get('question')
    uploaded_file = request.files.get('file')
    file_content = uploaded_file.read() if uploaded_file else None
    file_name = uploaded_file.filename if uploaded_file else None

    data = {
        'session_id': session_id,
        'question': question,
        'config': gpt_config,
        'file_content': file_content,
        'file_name': file_name,
        'instructions': gpt_config['instructions']
    }

    # Mettre en queue la tâche pour traitement asynchrone
    job = queue.enqueue('path.to.your.function.process_question_function', data, result_ttl=5000)

    return jsonify({'job_id': job.get_id()}), 202



def process_question_function(data, db, Message, Conversation):
    import openai  # Assurez-vous que la bibliothèque OpenAI est installée et configurée correctement.

    # Déballage des données
    session_id = data['session_id']
    question = data['question']
    config = data['config']
    file_content = data['file_content']
    file_name = data['file_name']
    instructions = data['instructions']

    # Récupération ou création d'une conversation
    conversation = Conversation.query.filter_by(session_id=session_id).first()
    if not conversation:
        conversation = Conversation(session_id=session_id)
        db.session.add(conversation)
        db.session.commit()

    # Enregistrement des instructions et de la question dans la base de données
    db.session.add(Message(conversation_id=conversation.id, role="system", content=instructions))
    if question:
        db.session.add(Message(conversation_id=conversation.id, role="user", content=question))
    if file_name:
        db.session.add(Message(conversation_id=conversation.id, role="user", content=f"Uploaded File: {file_name}"))
    db.session.commit()

    # Préparation de la requête pour OpenAI
    prompt = f"{instructions}\nQuestion: {question}\n"
    if file_content:
        prompt += f"File Content: {str(file_content)[:1000]}"  # Limitez la taille du contenu du fichier.

    # Appel à l'API OpenAI
    try:
        response = openai.Completion.create(
            engine=config['model'],
            prompt=prompt,
            max_tokens=config['max_tokens'],
            temperature=config['temperature'],
            top_p=config['top_p'],
            frequency_penalty=config['frequency_penalty'],
            presence_penalty=config['presence_penalty']
        )
        response_text = response.choices[0].text.strip()
    except Exception as e:
        response_text = f"Failed to get response from OpenAI: {str(e)}"

    # Enregistrement de la réponse de l'API
    db.session.add(Message(conversation_id=conversation.id, role="assistant", content=response_text))
    db.session.commit()

    return response_text



@app.route('/results/<job_id>', methods=['GET'])
def get_results(job_id):
    job = queue.fetch_job(job_id)
    if job.is_finished:
        return jsonify(job.result), 200
    elif job.is_failed:
        return jsonify({'error': 'Job failed'}), 500
    else:
        return jsonify({'status': 'Still processing'}), 202

if __name__ == '__main__':
    app.run(debug=True)

