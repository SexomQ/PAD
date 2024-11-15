from flask import request, jsonify, session
from flask_socketio import emit, join_room, leave_room
from models.model import Calendar, Event, UserCalendar
from flask_limiter.util import get_remote_address
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from __main__ import app, db, jwt, limiter, semaphore, socketio
import logging
import logstash

# Set up logging
logger = logging.getLogger('python-logstash-logger')
logger.setLevel(logging.INFO)
logger.addHandler(logstash.TCPLogstashHandler('logstash', 5044, version=1))

@socketio.on('connect')
@jwt_required()
def connect():
    print('Connected')
    emit('message', f"{request.sid} has connected")

@socketio.on('disconnect')
@jwt_required()
def disconnect():
    print('Disconnected')
    emit('message', f"{request.sid} has disconnected")

@socketio.on('message')
@jwt_required()
def message(data):
    print(f"Message: {data}")
    emit('message', data, broadcast=True)

# @socketio.on("created_event")
# def created_event(data):
#     print(f"Event created: {data}")
#     emit("event_created", data)

@socketio.on("join_calendar")
@jwt_required()
def join_calendar(data):
    username = get_jwt_identity()
    calendar_name = data['calendar_name']
    calendar = Calendar.query.filter_by(calendar_name=calendar_name).first()
    if not calendar:
        emit("message", "Calendar does not exist", broadcast=True)
    user_calendar = UserCalendar.query.filter_by(username=username, calendar_id=calendar.id).first()
    if user_calendar:
        emit("message", "User in calendar", room=calendar_name)
    user_calendar = UserCalendar(username=username, calendar_id=calendar.id)
    db.session.add(user_calendar)
    db.session.commit()

    join_room(calendar_name)
    emit("message", f"Joined calendar {calendar_name}", room=calendar_name, broadcast=True)

@socketio.on("leave_calendar")
@jwt_required()
def leave_calendar(data):
    username = get_jwt_identity()
    calendar_name = data['calendar_name']
    calendar = Calendar.query.filter_by(calendar_name=calendar_name).first()
    if not calendar:
        emit("message", "Calendar does not exist")
    user_calendar = UserCalendar.query.filter_by(username=username, calendar_id=calendar.id).first()
    if not user_calendar:
        emit("message", "User not in calendar")
    db.session.delete(user_calendar)
    db.session.commit()

    leave_room(calendar_name)
    emit("message", f"Left calendar {calendar_name}")

# Event for checking the status of the service and the database
@app.route('/api/calendar/status', methods=['GET'])
def status():
    try:
        semaphore.acquire()
        calendars = Calendar.query.all()
        events = Event.query.all()
        user_calendars = UserCalendar.query.all()
        if calendars and events and user_calendars:
            logger.info('microservice: Service and database are up and running', extra={'service': 'calendar-service' ,'status': 'success'})
            return jsonify({'message': 'Service and database are up and running'}), 200
    finally:
        semaphore.release()

# Event for creating a new calendar
@app.route('/api/calendar/create_calendar', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def create_calendar():
    try:
        semaphore.acquire()
        data = request.get_json()
        calendar_name = data['calendar_name']
        calendar_password = data['calendar_password']
        if Calendar.query.filter_by(calendar_name=calendar_name).first():
            logger.error('microservice: Calendar already exists', extra={'service': 'calendar-service' ,'status': 'error'})
            return jsonify({'message': 'Calendar already exists'}), 409

        new_calendar = Calendar(calendar_name=calendar_name, calendar_password=calendar_password)
        db.session.add(new_calendar)
        db.session.commit()
        logger.info('microservice: New calendar created', extra={'service': 'calendar-service' ,'status': 'success'})
        return jsonify({'message': 'New calendar created'}), 201
    finally:
        semaphore.release()

# Event for joining a calendar
# @app.route('/api/calendar/join_calendar', methods=['POST'])
# @jwt_required()
# @limiter.limit("5 per minute")
# def join_calendar():
#     try:
#         semaphore.acquire()
#         data = request.get_json()
#         username = get_jwt_identity()
#         print(username)
#         calendar_name = data['calendar_name']
#         calendar_password = data['calendar_password']
#         calendar = Calendar.query.filter_by(calendar_name=calendar_name).first()
#         if not calendar:
#             return jsonify({'message': 'Calendar does not exist'}), 404
#         if calendar.calendar_password != calendar_password:
#             return jsonify({'message': 'Incorrect password'}), 401
#         user_calendar = UserCalendar(username=username, calendar_id=calendar.id)
#         db.session.add(user_calendar)
#         db.session.commit()

#         # Join the room for the calendar
#         socketio.join_room(calendar_name)

#         # Emit event to all users in the calendar
#         socketio.emit("joined_calendar", {f"username {username} joined calendar {calendar_name}"})
#         return jsonify({'message': 'Joined calendar'}), 200
#     finally:
#         semaphore.release()

# Event for leaving a calendar
# @app.route('/api/calendar/leave_calendar', methods=['POST'])
# @jwt_required()
# @limiter.limit("5 per minute")
# def leave_calendar():
#     try:
#         semaphore.acquire()
#         data = request.get_json()
#         username = get_jwt_identity()
#         calendar_name = data['calendar_name']
#         calendar = Calendar.query.filter_by(calendar_name=calendar_name).first()
#         if not calendar:
#             return jsonify({'message': 'Calendar not found'}), 404
#         user_calendar = UserCalendar.query.filter_by(username=username, calendar_id=calendar.id).first()
#         if not user_calendar:
#             return jsonify({'message': 'User not in calendar'}), 404
#         db.session.delete(user_calendar)
#         db.session.commit()

#         # Leave the room for the calendar
#         socketio.leave_room(calendar_name)

#         # Emit event to all users in the calendar
#         socketio.emit("left_calendar", {'username': username, 'calendar_name': calendar_name})

#         return jsonify({'message': 'Left calendar'}), 200
#     finally:
#         semaphore.release()

# Event for creating a new event
@socketio.on('create_event')
@jwt_required()
def create_event(data):
    username = get_jwt_identity()
    event_name = data['event_name']
    event_start = data['event_start']
    event_end = data['event_end']
    calendar_name = data['calendar_name']
    calendar = Calendar.query.filter_by(calendar_name=calendar_name).first()
    if not calendar:
        return jsonify({'message': 'Calendar does not exist'}), 404
    user_calendar = UserCalendar.query.filter_by(username=username, calendar_id=calendar.id).first()
    if not user_calendar:
        return jsonify({'message': 'User not in calendar'}), 404
    new_event = Event(event_name=event_name, event_start=event_start, event_end=event_end, created_by=username, calendar_id=calendar.id)
    db.session.add(new_event)
    db.session.commit()

    # Emit event to all users in the calendar
    emit("created_event", f"New event {event_name} created by {username}", room=calendar_name)
    print(f"New event {event_name} created by {username}")


# Event for getting all events in a calendar
@app.route('/api/calendar/get_events', methods=['GET'])
@jwt_required()
@limiter.limit("5 per minute")
def get_events():
    try:
        semaphore.acquire()
        username = get_jwt_identity()
        user_calendar = UserCalendar.query.filter_by(username=username).first()
        if not user_calendar:
            logger.error('microservice: User not in calendar', extra={'service': 'calendar-service' ,'status': 'error'})
            return jsonify({'message': 'User not in calendar'}), 404
        events = Event.query.filter_by(calendar_id=user_calendar.calendar_id).all()
        if not events:
            logger.error('microservice: No events found', extra={'service': 'calendar-service' ,'status': 'error'})
            return jsonify({'message': 'No events found'}), 404
        event_list = []
        for event in events:
            event_list.append({'event_name': event.event_name, 'event_start': event.event_start, 'event_end': event.event_end, 'created_by': event.created_by})
        logger.info('microservice: Events found', extra={'service': 'calendar-service' ,'status': 'success'})
        return jsonify({'events': event_list}), 200
    finally:
        semaphore.release()