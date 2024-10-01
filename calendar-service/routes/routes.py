from flask import request, jsonify
from flask_socketio import SocketIO, emit
# from models.database import db
# from models.electro_scooter import ElectroScooter
from __main__ import app, socketio

@app.route('/')
def index():
    return "Calendar Service is running."

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('event')
def handle_event(data):
    print(f"Received event: {data}")
    emit('response', {'message': 'Event received!'})