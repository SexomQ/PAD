from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from datetime import timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from threading import BoundedSemaphore
import os
from dotenv import load_dotenv
from models.model import User
from models.database import db

def create_app(db):
    load_dotenv(os.path.join(os.path.dirname(__file__), '../user-management-db/.env'))

    app = Flask(__name__)

    db_user = os.getenv('POSTGRES_USER')
    db_password = os.getenv('POSTGRES_PASSWORD')
    db_name = os.getenv('POSTGRES_DB')
    db_host = os.getenv('POSTGRES_HOST')
    db_port = os.getenv('POSTGRES_PORT')

    print(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'super secret key'
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

    jwt = JWTManager(app)
    limiter = Limiter(get_remote_address, default_limits=["5 per minute"])
    semaphore = BoundedSemaphore(2) # 2 concurrent requests

    db.init_app(app)
    limiter.init_app(app)

    return app, db, jwt, limiter, semaphore
    

if __name__ == '__main__':
    app, db, jwt, limiter, semaphore = create_app(db)
    import routes.routes
    app.run(host='0.0.0.0', port=5001)