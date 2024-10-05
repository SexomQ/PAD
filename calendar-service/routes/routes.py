from flask import request, jsonify, session
from models.model import Calendar, Event, UserCalendar
from flask_limiter.util import get_remote_address
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from __main__ import app, db, jwt, limiter, semaphore

# Event for checking the status of the service and the database
@app.route('/api/calendar/status', methods=['GET'])
def status():
    try:
        semaphore.acquire()
        calendars = Calendar.query.all()
        events = Event.query.all()
        user_calendars = UserCalendar.query.all()
        if calendars and events and user_calendars:
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
            return jsonify({'message': 'Calendar already exists'}), 409

        new_calendar = Calendar(calendar_name=calendar_name, calendar_password=calendar_password)
        db.session.add(new_calendar)
        db.session.commit()
        return jsonify({'message': 'New calendar created'}), 201
    finally:
        semaphore.release()

# Event for joining a calendar
@app.route('/api/calendar/join_calendar', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def join_calendar():
    try:
        semaphore.acquire()
        data = request.get_json()
        username = get_jwt_identity()
        print(username)
        calendar_name = data['calendar_name']
        calendar_password = data['calendar_password']
        calendar = Calendar.query.filter_by(calendar_name=calendar_name).first()
        if not calendar:
            return jsonify({'message': 'Calendar does not exist'}), 404
        if calendar.calendar_password != calendar_password:
            return jsonify({'message': 'Incorrect password'}), 401
        user_calendar = UserCalendar(username=username, calendar_id=calendar.id)
        db.session.add(user_calendar)
        db.session.commit()
        return jsonify({'message': 'Joined calendar'}), 200
    finally:
        semaphore.release()

# Event for leaving a calendar
@app.route('/api/calendar/leave_calendar', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def leave_calendar():
    try:
        semaphore.acquire()
        data = request.get_json()
        username = get_jwt_identity()
        calendar_name = data['calendar_name']
        calendar = Calendar.query.filter_by(calendar_name=calendar_name).first()
        if not calendar:
            return jsonify({'message': 'Calendar not found'}), 404
        user_calendar = UserCalendar.query.filter_by(username=username, calendar_id=calendar.id).first()
        if not user_calendar:
            return jsonify({'message': 'User not in calendar'}), 404
        db.session.delete(user_calendar)
        db.session.commit()
        return jsonify({'message': 'Left calendar'}), 200
    finally:
        semaphore.release()

# Event for creating a new event
@app.route('/api/calendar/create_event', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def create_event():
    try:
        semaphore.acquire()
        data = request.get_json()
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
        return jsonify({'message': 'New event created'}), 201
    finally:
        semaphore.release()

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
            return jsonify({'message': 'User not in calendar'}), 404
        events = Event.query.filter_by(calendar_id=user_calendar.calendar_id).all()
        if not events:
            return jsonify({'message': 'No events found'}), 404
        event_list = []
        for event in events:
            event_list.append({'event_name': event.event_name, 'event_start': event.event_start, 'event_end': event.event_end, 'created_by': event.created_by})
        return jsonify({'events': event_list}), 200
    finally:
        semaphore.release()