import pytest
import os
from dotenv import load_dotenv
from main import app, db
from models.model import User

load_dotenv(os.path.join(os.path.dirname(__file__), '../user-management-db/.env'))

db_user = os.getenv('POSTGRES_USER')
db_password = os.getenv('POSTGRES_PASSWORD')
db_name = os.getenv('POSTGRES_DB')
db_host = os.getenv('POSTGRES_HOST')
db_port = os.getenv('POSTGRES_PORT')


from routes.routes import user
app.register_blueprint(user)

@pytest.fixture
def client():
    global db
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    with app.test_client() as client:
        # with app.app_context():
        #     db.create_all()
        yield client
        # with app.app_context():
        #     db.drop_all()

def test_register(client):
    with client.application.app_context():
        db.create_all()

        response = client.post('/api/user/register', json={"username":"unittest", "password":"unittest"})
        assert response.status_code == 201
        assert response.json == {"message": "User registered successfully!"}

        # Cleanup
        new_user = User.query.filter_by(username='unittest').first()
        db.session.delete(new_user)
        db.session.commit()

        # db.drop_all()

def test_register_existing_user(client):
    with client.application.app_context():
        db.create_all()

        new_user = User(username='unittest', password='unittest')
        db.session.add(new_user)
        db.session.commit()

        response = client.post('/api/user/register', json={"username":"unittest", "password":"unittest"})
        assert response.status_code == 409
        assert response.data == b'User already exists'

        # Cleanup
        db.session.query(User).filter_by(username='unittest').delete()
        db.session.commit()

        # db.drop_all()

def test_login(client):
    with client.application.app_context():
        db.create_all()

        new_user = User(username='unittest', password='unittest')
        db.session.add(new_user)
        db.session.commit()

        response = client.post('/api/user/login', json={"username":"unittest", "password":"unittest"})
        assert response.status_code == 200
        assert response.json['message'] == 'Logged in successfully!'

        # Cleanup
        db.session.query(User).filter_by(username='unittest').delete()
        db.session.commit()

        # db.drop_all()

def test_login_invalid_credentials(client):
    with client.application.app_context():
        db.create_all()

        new_user = User(username='unittest', password='unittest')
        db.session.add(new_user)
        db.session.commit()

        response = client.post('/api/user/login', json={"username":"unittest", "password":"wrongpassword"})
        assert response.status_code == 401
        assert response.data == b'Invalid credentials'

        # Cleanup
        db.session.query(User).filter_by(username='unittest').delete()
        db.session.commit()

        # db.drop_all()