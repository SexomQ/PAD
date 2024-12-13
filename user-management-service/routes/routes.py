from flask import Flask, request, session, jsonify, Blueprint
from flask_limiter.util import get_remote_address
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from main import app, db, jwt, limiter, semaphore
from models.model import User
from time import sleep
import logging
import logstash
from redis.sentinel import Sentinel
from redis import StrictRedis

from consistent_hashing.consistent_hashing import ConsistentHashRing

# Consistent Hash Ring Initialization
hash_ring = ConsistentHashRing(replicas=3)
hash_ring.add_node("redis_node_a")
hash_ring.add_node("redis_node_b")
hash_ring.add_node("redis_node_c")

# Configure Redis Sentinel for each node
sentinels = {
    "redis_node_a": Sentinel([("sentinel_node_a", 26379)], socket_timeout=1),
    "redis_node_b": Sentinel([("sentinel_node_b", 26379)], socket_timeout=1),
    "redis_node_c": Sentinel([("sentinel_node_c", 26379)], socket_timeout=1),
}

# Initialize Redis connections dynamically based on the master node for each Redis node
def get_redis_clients():
    redis_clients = {}
    for node in ["redis_node_a", "redis_node_b", "redis_node_c"]:
        master = sentinels[node].master_for("mymaster", decode_responses=True)
        redis_clients[node] = master
    return redis_clients

redis_clients = get_redis_clients()

# Set up logging
logger = logging.getLogger('python-logstash-logger')
logger.setLevel(logging.INFO)
logger.addHandler(logstash.TCPLogstashHandler('logstash', 5044, version=1))

user = Blueprint('user', __name__)

# Get the status of Redis nodes (master and replicas)
def get_redis_nodes():
    redis_nodes = {}
    for node_name in sentinels:
        # Get master node information
        master = sentinels[node_name].master_for("mymaster", decode_responses=True)
        
        # Extract connection details from the master Redis client
        master_host = master.connection_pool.get_connection('ping')._sock.getpeername()[0]
        master_port = master.connection_pool.get_connection('ping')._sock.getpeername()[1]
        
        redis_nodes[node_name] = {
            'master': {
                'host': master_host,
                'port': master_port,
                'role': 'master'
            },
            'replicas': []
        }
        
        # Get replica nodes information
        replicas = sentinels[node_name].discover_slaves("mymaster")
        for replica in replicas:
            replica_connection = StrictRedis(host=replica['ip'], port=replica['port'], decode_responses=True)
            redis_nodes[node_name]['replicas'].append({
                'host': replica['ip'],
                'port': replica['port'],
                'role': 'replica'
            })
    
    return redis_nodes

@user.route('/api/user/status', methods=['GET'])
def status():
    try:
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
        credentials = request.get_json()

        if not credentials or 'username' not in credentials or 'password' not in credentials:
            logger.error('microservice: Missing username or password', extra={'service': 'user-management-service' ,'status': 'error'})
            return "Missing username or password", 400

        username = credentials['username']
        password = credentials['password']

        check_user = db.session.query(User).filter_by(username=username).first()
        if check_user:
            logger.error('microservice: User already exists', extra={'service': 'user-management-service' ,'status': 'error'})
            return "User already exists", 409
        
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        logger.info('microservice: User registered successfully', extra={'service': 'user-management-service' ,'status': 'success'})
        return jsonify({"message": "User registered successfully!"}), 201
    finally:
        semaphore.release()
    
@user.route('/api/user/login', methods=['POST'])
def login():
    # sleep(30)
    try:
        semaphore.acquire()
        credentials = request.get_json()
        username = credentials['username']
        password = credentials['password']

        # Check user in the database
        user = db.session.query(User).filter_by(username=username, password=password).first()
        if not user:
            logger.error('Invalid credentials', extra={'service': 'user-management-service', 'status': 'error'})
            return "Invalid credentials", 401

        # Determine which Redis node to use using consistent hashing
        redis_node = hash_ring.get_node(username)
        redis_client = redis_clients[redis_node]

        # Check if username is in cache
        cached_token = redis_client.get(username)
        if cached_token:
            logger.info('User found in cache', extra={'service': 'user-management-service', 'status': 'success'})
            return jsonify({"message": "Logged in successfully (cached)!", "token": cached_token, "username": username}), 200

        # Generate a new token and save to Redis
        jwt_token = create_access_token(identity=username)
        redis_client.set(username, jwt_token, ex=3600)  # Cache for 1 hour

        logger.info('Logged in successfully', extra={'service': 'user-management-service', 'status': 'success'})
        return jsonify({"message": "Logged in successfully!", "token": jwt_token, "username": username}), 200

    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}", extra={'service': 'user-management-service', 'status': 'error'})
        return str(e), 500
    finally:
        semaphore.release()

@user.route('/api/user/redis', methods=['GET'])
def redis_status():
    try:
        semaphore.acquire()
        redis_nodes = get_redis_nodes()
        return jsonify(redis_nodes), 200
    finally:
        semaphore.release()

@user.route('/api/user/redis_content', methods=['GET'])
def redis_content():
    try:
        semaphore.acquire()
        
        # Initialize a dictionary to store the content from all Redis nodes
        redis_content = {}

        # Iterate over all Redis nodes
        for node_name, redis_client in redis_clients.items():
            # Get all keys from the Redis node
            keys = redis_client.keys('*')  # Fetch all keys
            node_data = {}

            # For each key, fetch its corresponding value from Redis
            for key in keys:
                value = redis_client.get(key)
                node_data[key] = value

            # Add the node's data to the main dictionary
            redis_content[node_name] = node_data
        
        # Return the collected data
        logger.info('Redis content fetched successfully', extra={'service': 'user-management-service', 'status': 'success'})
        return jsonify(redis_content), 200

    except Exception as e:
        logger.error(f"Exception occurred while fetching Redis content: {str(e)}", extra={'service': 'user-management-service', 'status': 'error'})
        return str(e), 500
    finally:
        semaphore.release()
