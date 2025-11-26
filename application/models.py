from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# USER MODEL

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / doctor / patient

    doctor_profile = db.relationship("Doctor", backref="user", uselist=False)
    patient_profile = db.relationship("Patient", backref="user", uselist=False)


# DEPARTMENT MODEL

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    doctors = db.relationship("Doctor", backref="department", lazy=True)


# DOCTOR MODEL

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    dept_id = db.Column(db.Integer, db.ForeignKey("department.id"))
    specialization = db.Column(db.String(120))
    bio = db.Column(db.String(300))

    availability = db.relationship(
        "Availability", backref="doctor", cascade="all, delete"
    )
    appointments = db.relationship("Appointment", backref="doctor")


# PATIENT MODEL

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    appointments = db.relationship("Appointment", backref="patient")


# DOCTOR AVAILABILITY MODEL

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"))
    date = db.Column(db.Date, nullable=False)
    slot = db.Column(db.String(50), nullable=False)   # "10:00 AM - 11:00 AM"

    is_booked = db.Column(db.Boolean, default=False)


# APPOINTMENTS MODEL

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"))
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"))
    availability_id = db.Column(db.Integer, db.ForeignKey("availability.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    availability = db.relationship("Availability")

    history = db.relationship(
        "History",
        backref="appointment",
        cascade="all, delete",
        uselist=False
    )


# MEDICAL HISTORY MODEL

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
