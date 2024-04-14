from flask import Flask, render_template, request, jsonify, session, make_response
from openai import OpenAI
import os
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import markdown2
from docx import Document
import io
from flask_migrate import Migrate
import uuid
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, session
from flask_session import Session


app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['https://kokua.fr', 'https://www.kokua.fr'])
# CORS(app, supports_credentials=True, origins='*')

app.secret_key = 'assistant-ai-1a-urrugne-64122'  

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("://", "ql://", 1) # Remplacez pour corriger l'URL pour PostgreSQL
# Exemple de configuration temporaire pour la génération des migrations
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temp.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')

Session(app)

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
    # S'assure que session_id existe dans la session Flask, sinon en crée un nouveau.
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Récupère l'ID de session depuis la session Flask.
    session_id = session['session_id']

    try:
        # Vérifie si une conversation existe pour cet ID de session.
        conversation = Conversation.query.filter_by(session_id=session_id).first()
        if not conversation:
            # Si aucune conversation n'existe, en crée une nouvelle.
            conversation = Conversation(session_id=session_id, derniere_activite=datetime.utcnow())
            db.session.add(conversation)
        else:
            # Si une conversation existe, met à jour la dernière activité.
            conversation.derniere_activite = datetime.utcnow()
        
        db.session.commit()  # Confirmez les modifications ici.
    except Exception as e:
        db.session.rollback()  # En cas d'erreur, annulez les modifications.
        app.logger.error(f"Erreur lors de la gestion de la conversation : {e}")
        return jsonify({"error": "Un problème est survenu lors de la gestion de la conversation"}), 500
    # finally:
    #     db.session.close()  # Fermez la session ici, après toutes les opérations.
    
   # Traitement de la question ou du fichier...
    question = request.form.get('question')
    uploaded_file = request.files.get('file')
   

    # Créez une nouvelle conversation
    # new_conversation = Conversation()
    # db.session.add(new_conversation)
    # db.session.commit() 



    instructions_content = """
    commence ta réponse par "salut Jo"
    """
    instructions_message = Message(conversation_id=conversation.id, role="system", content=instructions_content)
    db.session.add(instructions_message)

    if question:
     question_message = Message(conversation_id=conversation.id, role="user", content=question)
     db.session.add(question_message)

    if uploaded_file and uploaded_file.filename:
        try:
            if uploaded_file.filename.endswith('.docx'):
                document = Document(io.BytesIO(uploaded_file.read()))
                file_content = "\n".join([paragraph.text for paragraph in document.paragraphs])
                uploaded_file_message = Message(conversation_id=conversation.id, role="user", content="Uploaded File: " + uploaded_file.filename)
                db.session.add(uploaded_file_message)
                file_content_message = Message(conversation_id=conversation.id, role="user", content=file_content)
                db.session.add(file_content_message)
            else:
                return jsonify({"error": "Type de fichier non pris en charge."}), 400
        except Exception as e:
            app.logger.error(f"Erreur lors du traitement du fichier : {e}")
            return jsonify({"error": "Le traitement du fichier a échoué.", "details": str(e)}), 400

    db.session.commit()

    db_messages = Message.query.filter_by(conversation_id=conversation.id).all()
    messages_for_openai = [{"role": msg.role, "content": msg.content} for msg in db_messages]

    if question or uploaded_file:
        try:
            chat_completion = client.chat.completions.create(
                messages=messages_for_openai,
                model="gpt-3.5-turbo",
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
