from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from datetime import timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from threading import BoundedSemaphore
import os
from dotenv import load_dotenv
from models.model import Calendar, Event, UserCalendar
from models.database import db

def create_app(db):
    load_dotenv(os.path.join(os.path.dirname(__file__), '../calendar-db/.env'))

    db_user = os.getenv('POSTGRES_USER')
    db_password = os.getenv('POSTGRES_PASSWORD')
    db_name = os.getenv('POSTGRES_DB')
    db_host = os.getenv('POSTGRES_HOST')
    db_port = os.getenv('POSTGRES_PORT')
    
    app = Flask(__name__)

    print(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'super secret key'
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

    socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
    jwt = JWTManager(app)
    limiter = Limiter(get_remote_address)
    semaphore = BoundedSemaphore(2)

    db.init_app(app)
    limiter.init_app(app)

    return app, db, jwt, limiter, semaphore , socketio 

if __name__ == '__main__':
    app, db, jwt, limiter, semaphore, socketio  = create_app(db)
    import routes.routes
    socketio.run(app=app, host='0.0.0.0', port=5002, allow_unsafe_werkzeug=True)