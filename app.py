from flask import Flask
from application.database import db
from application.models import User
from application.controllers import init_routes

def create_app():
    app = Flask(__name__)
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'  # For session

    db.init_app(app)

    # Create tables and default admin
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@hospital.com',
                password='admin123',
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()

    init_routes(app)  
    return app

app = create_app()

if __name__ == "__main__":
    app.run()
