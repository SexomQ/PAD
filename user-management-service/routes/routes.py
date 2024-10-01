from flask import Flask, request, session
from __main__ import app

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