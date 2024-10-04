from main import create_app, db, Calendar, Event, UserCalendar

def init_db(db):
    app, db, jwt, limiter, semaphore = create_app(db)
    with app.app_context():
        db.create_all()
        if db.session.query(Calendar).filter_by(calendar_name='test').first():
            print("Database already initialized")
            return
        db.session.add(Calendar(calendar_name='test', calendar_password='test1234'))
        db.session.add(Event(event_name='Cristina Birthday )', event_start='2024-10-21 00:00:00', event_end='2024-10-21 23:59:00', created_by='admin', calendar_id=1))
        db.session.add(UserCalendar(username='admin', calendar_id=1))
        db.session.commit()
        print("Database initialized")

if __name__ == '__main__':
    init_db(db)