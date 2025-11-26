# application/controllers.py
from flask import render_template, redirect, request, session, url_for, flash
from flask import current_app as app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from .models import db, User, Doctor, Patient, Department, Availability, Appointment, History

# ------------------------
# AUTH / SESSION
# ------------------------
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        pwd = request.form.get("password")  # form field name: password
        user = User.query.filter_by(username=username).first()
        if not user:
            return render_template("login.html", error="User not found")
        # Password may be hashed or plain depending on your registration flow.
        # We try check_password_hash first; if it fails, fall back to plaintext compare (backwards compat).
        try:
            ok = check_password_hash(user.password, pwd)
        except Exception:
            ok = (user.password == pwd)
        if not ok:
            return render_template("login.html", error="Incorrect password")

        # Set session
        session["user_id"] = user.id
        session["role"] = user.role

        # Redirect by role
        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif user.role == "doctor":
            return redirect(url_for("doctor_dashboard", user_id=user.id))
        else:
            return redirect(url_for("patient_dashboard", user_id=user.id))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Expect form fields: username, email, password, role (admin/doctor/patient)
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        raw_pwd = request.form.get("password")
        role = request.form.get("role", "patient")

        if User.query.filter((User.username == username) | (User.email == email)).first():
            return render_template("register.html", error="Username or email already taken")

        hashed = generate_password_hash(raw_pwd)
        user = User(username=username, email=email, password=hashed, role=role)
        db.session.add(user)
        db.session.commit()

        # create role-specific profile rows
        if role == "doctor":
            doc = Doctor(user_id=user.id)
            db.session.add(doc)
        elif role == "patient":
            pat = Patient(user_id=user.id)
            db.session.add(pat)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------
# ADMIN ROUTES
# ------------------------
@app.route("/admin")
def admin_dashboard():
    # a simple admin landing — you may want admin_dash.html
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    departments = Department.query.all()
    doctors = Doctor.query.all()
    patients = Patient.query.all()
    return render_template("admin_dash.html", departments=departments, doctors=doctors, patients=patients)


@app.route("/admin/add-department", methods=["GET", "POST"])
def admin_add_department():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("name")
        if not name:
            return render_template("create_dept.html", error="Name required")
        if Department.query.filter_by(name=name).first():
            return render_template("create_dept.html", error="Department exists")
        dept = Department(name=name)
        db.session.add(dept)
        db.session.commit()
        return redirect(url_for("admin_dashboard"))
    return render_template("create_dept.html")


@app.route("/admin/add-doctor", methods=["GET", "POST"])
def admin_add_doctor():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    departments = Department.query.all()
    if request.method == "POST":
        # Expect either existing user_id (if doctor user already created) or create a new user
        username = request.form.get("username")
        email = request.form.get("email")
        raw_pwd = request.form.get("password") or "doctorpass"
        dept_id = request.form.get("department_id")
        specialization = request.form.get("specialization") or ""
        bio = request.form.get("bio") or ""

        # Create User account for doctor
        if User.query.filter((User.username == username) | (User.email == email)).first():
            return render_template("add_doctor.html", departments=departments, error="Username/email exists")

        hashed = generate_password_hash(raw_pwd)
        user = User(username=username, email=email, password=hashed, role="doctor")
        db.session.add(user)
        db.session.commit()

        doc = Doctor(user_id=user.id, dept_id=int(dept_id) if dept_id else None,
                     specialization=specialization, bio=bio)
        db.session.add(doc)
        db.session.commit()
        return redirect(url_for("admin_dashboard"))

    return render_template("add_doctor.html", departments=departments)


@app.route("/admin/doctors")
def admin_view_doctors():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    doctors = Doctor.query.all()
    return render_template("view_doctors.html", doctors=doctors)


@app.route("/admin/patients")
def admin_view_patients():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    patients = Patient.query.all()
    return render_template("view_patients.html", patients=patients)


# ------------------------
# DOCTOR ROUTES
# ------------------------
@app.route("/doctor/<int:user_id>/dashboard")
def doctor_dashboard(user_id):
    # doctor sees appointments assigned to them
    user = User.query.filter_by(id=user_id, role="doctor").first_or_404()
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    if not doctor:
        return "No doctor profile found", 404
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
    return render_template("doctor_dash.html", doctor=doctor, appointments=appointments)


@app.route("/doctor/<int:user_id>/availability", methods=["GET", "POST"])
def doctor_availability(user_id):
    # doctors set their own availability (flow chosen)
    # ensure logged-in doctor matches user_id or admin
    if session.get("role") not in ("doctor", "admin"):
        return redirect(url_for("login"))

    doctor = Doctor.query.filter_by(user_id=user_id).first_or_404()

    if request.method == "POST":
        date_str = request.form.get("date")
        slot = request.form.get("slot")
        if not date_str or not slot:
            return render_template("doctor_avail.html", doctor=doctor, availability=doctor.availability,
                                   error="date and slot required")
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return render_template("doctor_avail.html", doctor=doctor, availability=doctor.availability,
                                   error="date must be YYYY-MM-DD")
        a = Availability(doctor_id=doctor.id, date=d, slot=slot, is_booked=False)
        db.session.add(a)
        db.session.commit()
        return redirect(url_for("doctor_availability", user_id=user_id))

    availability = Availability.query.filter_by(doctor_id=doctor.id).all()
    return render_template("doctor_avail.html", doctor=doctor, availability=availability)


@app.route("/doctor/<int:user_id>/appointments/<int:appointment_id>/update_history", methods=["GET", "POST"])
def doctor_update_history(user_id, appointment_id):
    if session.get("role") not in ("doctor", "admin"):
        return redirect(url_for("login"))
    # ensure doctor owns appointment
    doctor = Doctor.query.filter_by(user_id=user_id).first_or_404()
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != doctor.id and session.get("role") != "admin":
        return "Not allowed", 403

    if request.method == "POST":
        notes = request.form.get("notes", "")
        hist = History(appointment_id=appt.id, notes=notes)
        db.session.add(hist)
        # optional: mark appointment completed
        db.session.commit()
        return redirect(url_for("doctor_dashboard", user_id=user_id))

    return render_template("update_history.html", appointment=appt)


# ------------------------
# PATIENT ROUTES
# ------------------------
@app.route("/patient/<int:user_id>/dashboard")
def patient_dashboard(user_id):
    user = User.query.filter_by(id=user_id, role="patient").first_or_404()
    patient = Patient.query.filter_by(user_id=user.id).first()
    if not patient:
        return "No patient profile found", 404
    appointments = Appointment.query.filter_by(patient_id=patient.id).all()
    return render_template("patient_dash.html", patient=patient, appointments=appointments)


@app.route("/patient/<int:user_id>/departments")
def patient_departments(user_id):
    departments = Department.query.all()
    return render_template("department.html", departments=departments, user_id=user_id)


@app.route("/patient/department/<int:dept_id>")
def patient_doctor_list(dept_id):
    # lists doctors in a department
    doctors = Doctor.query.filter_by(dept_id=dept_id).all()
    return render_template("doctor_detail.html", doctors=doctors, dept_id=dept_id)


@app.route("/patient/book/<int:user_id>/<int:doctor_id>", methods=["GET", "POST"])
def patient_book_appointment(user_id, doctor_id):
    # user_id is the patient user's id (User.id). Need to find Patient record.
    user = User.query.filter_by(id=user_id, role="patient").first_or_404()
    patient = Patient.query.filter_by(user_id=user.id).first_or_404()
    doctor = Doctor.query.get_or_404(doctor_id)
    # available slots where is_booked=False
    slots = Availability.query.filter_by(doctor_id=doctor.id, is_booked=False).all()

    if request.method == "POST":
        avail_id = request.form.get("availability_id")
        if not avail_id:
            return render_template("book_appointment.html", doctor=doctor, slots=slots, error="Choose a slot")
        slot = Availability.query.get_or_404(int(avail_id))
        if slot.is_booked:
            return render_template("book_appointment.html", doctor=doctor, slots=slots, error="Slot already booked")
        slot.is_booked = True
        appt = Appointment(patient_id=patient.id, doctor_id=doctor.id, availability_id=slot.id)
        db.session.add(appt)
        db.session.commit()
        return redirect(url_for("patient_dashboard", user_id=user_id))

    return render_template("book_appointment.html", doctor=doctor, slots=slots, user_id=user_id)


@app.route("/patient/cancel/<int:user_id>/<int:appointment_id>", methods=["POST"])
def patient_cancel_appointment(user_id, appointment_id):
    user = User.query.filter_by(id=user_id, role="patient").first_or_404()
    patient = Patient.query.filter_by(user_id=user.id).first_or_404()
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != patient.id:
        return "Not allowed", 403
    # free slot if linked
    if appt.availability_id:
        slot = Availability.query.get(appt.availability_id)
        if slot:
            slot.is_booked = False
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for("patient_dashboard", user_id=user_id))


@app.route("/patient/<int:user_id>/history")
def patient_history(user_id):
    user = User.query.filter_by(id=user_id, role="patient").first_or_404()
    patient = Patient.query.filter_by(user_id=user.id).first_or_404()
    appointments = Appointment.query.filter_by(patient_id=patient.id).all()
    # template you have: patient_history.html
    return render_template("patient_history.html", appointments=appointments, patient=patient)
