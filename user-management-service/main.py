from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from models.model import User
from models.database import db

def create_app(db):
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

    app = Flask(__name__)

    db_user = os.getenv('POSTGRES_USER')
    db_password = os.getenv('POSTGRES_PASSWORD')
    db_name = os.getenv('POSTGRES_DB')
    db_host = os.getenv('POSTGRES_HOST')
    db_port = os.getenv('POSTGRES_PORT')

    print(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    return app
    

if __name__ == '__main__':
    app = create_app(db)
    import routes.routes
    app.run(host='0.0.0.0', port=5001)