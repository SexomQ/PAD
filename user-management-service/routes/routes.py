from flask import Flask, request, session, jsonify, Blueprint
from flask_limiter.util import get_remote_address
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from main import app, db, jwt, limiter, semaphore
import time
from models.model import User
import asyncio
import logging
import logstash
from services.saga import OrchestrationBuilder

# Set up logging
logger = logging.getLogger('python-logstash-logger')
logger.setLevel(logging.INFO)
logger.addHandler(logstash.TCPLogstashHandler('logstash', 5044, version=1))

user = Blueprint('user', __name__)

# Create steps for the saga orchestration 
async def get_credentials(request):
    credentials = request.get_json()
    if not credentials or 'username' not in credentials or 'password' not in credentials:
        logger.error('microservice: Missing username or password', extra={'service': 'user-management-service' ,'status': 'error'})
        raise Exception("Missing username or password")
    print(f"From get_credentials: {credentials['username']}, {credentials['password']}")
    return credentials['username'], credentials['password']

async def register_user(username, password):
    check_user = db.session.query(User).filter_by(username=username).first()
    if check_user:
        logger.error('microservice: User already exists', extra={'service': 'user-management-service' ,'status': 'error'})
        raise Exception("User already exists")
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    logger.info('microservice: User registered successfully', extra={'service': 'user-management-service' ,'status': 'success'})
    return jsonify({"message": "User registered successfully!"}), 201

async def login_user(username, password):
    user = db.session.query(User).filter_by(username=username, password=password).first()
    if not user:
        logger.error('microservice: Invalid credentials', extra={'service': 'user-management-service' ,'status': 'error'})
        raise Exception("Invalid credentials")
    jwt_token = create_access_token(identity=username)
    logger.info('microservice: Logged in successfully', extra={'service': 'user-management-service' ,'status': 'success'})
    return jsonify({"message": "Logged in successfully!", "token" : jwt_token, "username" : user.username}), 200

# Compensations
async def register_user_compensation(username, password):
    # Delete user from database
    user = db.session.query(User).filter_by(username=username).first()
    db.session.delete(user)
    db.session.commit()
    logger.error('microservice: User registration failed ---- Compensating', extra={'service': 'user-management-service' ,'status': 'error'})
    return jsonify({"message": "User registration failed ---- Compensating"}), 500

async def login_user_compensation(username, password):
    logger.error('microservice: Login failed ---- Compensating', extra={'service': 'user-management-service' ,'status': 'error'})
    return jsonify({"message": "Login failed ---- Compensating"}), 500


@user.route('/api/user/status', methods=['GET'])
def status():
    try:
        # time.sleep(10)
        semaphore.acquire()
        users = db.session.query(User).all()
        if users:
            logger.info('microservice: Service and database are up and running', extra={'service': 'user-management-service' ,'status': 'success'})
            return jsonify({'message': 'Service and database are up and running'}), 200
    finally:
        semaphore.release()

@user.route('/api/user/register', methods=['POST'])
# @limiter.limit("5 per minute")
def register():
    try:
        semaphore.acquire()
        # time.sleep(30)
        # # Get credentials from json 
        # credentials = request.get_json()

        # if not credentials or 'username' not in credentials or 'password' not in credentials:
        #     logger.error('microservice: Missing username or password', extra={'service': 'user-management-service' ,'status': 'error'})
        #     return "Missing username or password", 400

        # username = credentials['username']
        # password = credentials['password']

        # check_user = db.session.query(User).filter_by(username=username).first()
        # if check_user:
        #     logger.error('microservice: User already exists', extra={'service': 'user-management-service' ,'status': 'error'})
        #     return "User already exists", 409
        
        # new_user = User(username=username, password=password)
        # db.session.add(new_user)
        # db.session.commit()

        # logger.info('microservice: User registered successfully', extra={'service': 'user-management-service' ,'status': 'success'})
        # return jsonify({"message": "User registered successfully!"}), 201

        credentials = request.get_json()
        username = credentials['username']
        password = credentials['password']

        saga_builder = (
            OrchestrationBuilder()
            .add_step(lambda : get_credentials(request), lambda : None)
            .add_step(lambda : register_user(username, password), lambda : register_user_compensation(username, password))
            .add_step(lambda : login_user(username, password), lambda : login_user_compensation(username, password))
        )

        asyncio.run(saga_builder.execute())

        return jsonify({"message": "User registered successfully!"}), 201
    finally:
        semaphore.release()
    
@user.route('/api/user/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    try:
        semaphore.acquire()
        # Get credentials from json 
        credentials = request.get_json()
        username = credentials['username']
        password = credentials['password']

        user = db.session.query(User).filter_by(username=username, password=password).first()
        if not user:
            logger.error('microservice: Invalid credentials', extra={'service': 'user-management-service' ,'status': 'error'})
            return "Invalid credentials", 401

        jwt_token = create_access_token(identity=username)
        
        logger.info('microservice: Logged in successfully', extra={'service': 'user-management-service' ,'status': 'success'})
        return jsonify({"message": "Logged in successfully!", "token" : jwt_token, "username" : user.username}), 200
    except Exception as e:
        return str(e), 500
    finally:
        semaphore.release()