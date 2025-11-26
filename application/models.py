from .database import db #context of application is root directory, no dot> looks in root directory, with dot> looks in current directory
class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(), unique=True, nullable=False)
  email=db.Column(db.String(), unique=True, nullable=False)
  password=db.Column(db.String(), nullable=False)
  type=db.Column(db.String(), nullable=False, default="user")
  requests=db.relationship("Request", backref="user") 

class doctor(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(), nullable=False)
  specialisation = db.Column(db.String(), nullable=False)
  experience = db.Column(db.Integer(), nullable=False)
  details = db.Column(db.string(), nullable=False)
  status = db.Column(db.String(), nullable=False, default="available")
  requests=db.relationship("Request", backref="product")


class department(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(), nullable=False)
  detail = db.Column(db.string(), nullable=False)
  status = db.Column(db.String(), nullable=False, default="available")

class Request(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer(), db.ForeignKey("user.id"),nullable=False)
  product_id = db.Column(db.Integer(), db.ForeignKey("product.id"),nullable=False)
  units_requested = db.Column(db.Integer(), nullable=False)
  status = db.Column(db.String(), nullable=False, default="requested")

class Product(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(), nullable=False)
  specialisation = db.Column(db.String(), nullable=False)
  experience = db.Column(db.Integer(), nullable=False)
  details = db.Column(db.string(), nullable=False)
  status = db.Column(db.String(), nullable=False, default="available")
  requests=db.relationship("Request", backref="product")
  




  
# 1. from database import db > models.py will look for this file in root directory
# 2. from .database import db > models.py will look for this file in current directory(application folder)
# 3. from application.database import db > models.py will think that there is one more application folder in the root directory(application folder) with respect to models.py
