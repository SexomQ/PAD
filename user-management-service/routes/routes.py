from flask import Flask, request, session, jsonify
from __main__ import app, db
from models.model import User

@app.route('/register', methods=['POST'])
def register():
    # Get credentials from json 
    credentials = request.get_json()

    if not credentials or 'username' not in credentials or 'password' not in credentials:
        return "Missing username or password", 400

    username = credentials['username']
    password = credentials['password']

    check_user = db.session.query(User).filter_by(username=username).first()
    if check_user:
        return "User already exists", 400
    
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    print(f"Registered new user {username}")
    return jsonify(credentials), 201

    
@app.route('/login', methods=['POST'])
def login():
    # Get credentials from json 
    credentials = request.get_json()
    username = credentials['username']
    password = credentials['password']

    print(f"Received login request for user {username}")

    return "Cool, you're logged in!", 200

@app.route('/logout')
def logout():
    session.pop('user', None)
    return "Logged out!", 200