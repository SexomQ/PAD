from main import app, db, User

def init_db(db):
    with app.app_context():
        db.create_all()
        if db.session.query(User).filter_by(username='admin').first():
            print("Database already initialized")
            return
        db.session.add(User(username='admin', password='admin'))
        db.session.commit()
        print("Database initialized")

if __name__ == '__main__':
    init_db(db)