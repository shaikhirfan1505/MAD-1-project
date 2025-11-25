from flask  import Flask
from application.database import db #step 3
app = None

def create_app():
  app = Flask(__name__) 
  app.debug=True 
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.sqlite3'
  db.init_app(app)
  app.app_context().push()
  return app

app = create_app()
from application.controllers import * 

if __name__ == '__main__': 
  with app.app_context():
    db.create_all()
    admin=User.query.filter_by(type="admin").first()
    if admin is None:
      admin=User(username="@admin1234",email="admin@1234.com",password="@1234",type="admin")
      db.session.add(admin)
      db.session.commit()
  app.run()
