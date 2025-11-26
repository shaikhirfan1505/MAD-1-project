from flask import Flask
from application.models import db, User   # updated import
from werkzeug.security import generate_password_hash

app = None

def create_app():
    app = Flask(__name__)
    app.debug = True

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    app.app_context().push()
    return app


app = create_app()

# Import routes AFTER app creation
from application.controllers import *  


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Ensure default admin exists
        admin = User.query.filter_by(role="admin").first()
        if admin is None:
            admin = User(
                username="admin",
                email="admin@example.com",
                password=generate_password_hash("admin123"),
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()

    app.run()
