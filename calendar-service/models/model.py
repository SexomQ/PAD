from models.database import db

class Calendar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    calendar_name = db.Column(db.String(100), nullable=False)
    calendar_password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Calendar {self.calendar_name}>'
    
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False)
    event_start = db.Column(db.DateTime, nullable=False)
    event_end = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.String(100), nullable=False)
    calendar_id = db.Column(db.Integer, db.ForeignKey('calendar.id'), nullable=False)
    calendar = db.relationship('Calendar', backref=db.backref('event', lazy=True))

    def __repr__(self):
        return f'<Event {self.event_name}>'
    
class UserCalendar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    calendar_id = db.Column(db.Integer, db.ForeignKey('calendar.id'), nullable=False)
    calendar = db.relationship('Calendar', backref=db.backref('user_calendar', lazy=True))

    def __repr__(self):
        return f'<UserCalendar {self.user_id}>'