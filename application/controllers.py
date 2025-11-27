from flask import render_template, request, redirect, url_for, flash, session
from application.database import db
from application.models import User, Patient, Doctor, Appointment, Department, TreatmentHistory


def init_routes(app):
    # Default route -> Login page
    @app.route('/', methods=['GET', 'POST'])
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            user = User.query.filter((User.username == username) | (User.email == username)).first()
            if user and user.password == password:  # In real app, use hashed passwords
                session['user_id'] = user.id
                session['role'] = user.role

                if user.role == 'admin':
                    return redirect('/admin/dashboard')
                elif user.role == 'doctor':
                    return redirect('/doctor/dashboard')
                else:  # patient
                    return redirect('/patient/dashboard')
            else:
                flash('Invalid credentials', 'danger')

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            phone = request.form['phone']
            password = request.form['password']

            # Check if username/email exists
            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash("Username or Email already exists", "warning")
                return redirect(url_for('register'))

            # Only patients can register
            new_user = User(username=username, email=email, phone=phone, password=password, role='patient')
            db.session.add(new_user)
            db.session.commit()

            # Create linked Patient record
            new_patient = Patient(name=username, email=email, phone=phone, user_id=new_user.id)
            db.session.add(new_patient)
            db.session.commit()

            flash("Registration successful. Please login.", "success")
            return redirect(url_for('login'))

        return render_template('register.html')
    
    #logout for admin
    @app.route('/logout')
    def logout():
        session.clear()  # removes all session data
        flash("You have been logged out.", "success")
        return redirect(url_for('login'))


    # Admin dashboard route
    @app.route('/admin/dashboard')
    def admin_dashboard():
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        # Fetch data from database
        doctors = Doctor.query.all()
        patients = Patient.query.all()
        total_doctors = len(doctors)
        total_patients = len(patients)
        total_appointments = Appointment.query.count()
        departments = Department.query.all()
        upcoming_appointments = Appointment.query.all()  # or filter by future date

        return render_template('admin_dash.html',
                            doctors=doctors,
                            patients=patients,
                            total_doctors=total_doctors,
                            departments=departments,
                            total_patients=total_patients,
                            total_appointments=total_appointments,
                            upcoming_appointments=upcoming_appointments)

    
    # Patient dashboard route
    @app.route('/patient/dashboard')
    def patient_dashboard():
        if 'role' not in session or session['role'] != 'patient':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        user_id = session.get('user_id')
        patient = Patient.query.filter_by(user_id=user_id).first()
        if not patient:
            flash("Patient record not found!", "danger")
            return redirect(url_for('login'))

        return render_template('patient_dash.html', patient=patient)
    

        # Add doctor route (only admin)
    @app.route('/admin/doctor/add', methods=['GET', 'POST'])
    def add_doctor():
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        # Fetch all departments to show in the dropdown
        Departments = Department.query.all()

        if request.method == 'POST':
            name = request.form['name']
            phone = request.form['phone']
            experience = request.form['experience']
            details = request.form['details']
            department_id = request.form['department_id']  # get selected department

            # Create User record for doctor
            username = name.lower().replace(" ", "")
            email = f"{username}@hospital.com"
            password = request.form['password']
            new_user = User(username=username, email=email, password=password, role='doctor')
            db.session.add(new_user)
            db.session.commit()

            # Create Doctor record with department_id
            new_doctor = Doctor(
                name=name,
                email=email,
                phone=phone,
                experience=experience,
                details=details,
                department_id=department_id
            )
            db.session.add(new_doctor)
            db.session.commit()

            flash(f"Doctor {name} added.", "success")
            return redirect('/admin/dashboard')

        return render_template('add_doctor.html', Departments=Departments)



    # Doctor dashboard route
    @app.route('/doctor/dashboard')
    def doctor_dashboard():
        if 'role' not in session or session['role'] != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        user_id = session.get('user_id')
        doctor_user = User.query.get(user_id)
        doctor = Doctor.query.filter_by(email=doctor_user.email).first()

        return render_template('doctor_dash.html', doctor=doctor)
    

        # View doctor details (Admin)
    @app.route('/admin/doctor/<int:doctor_id>')
    def admin_doctor_details(doctor_id):
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.get_or_404(doctor_id)
        return render_template('doctor_detail.html', doctor=doctor)


    # View doctor details (Patient)
    @app.route('/patient/doctor/<int:doctor_id>')
    def patient_doctor_details(doctor_id):
        if 'role' not in session or session['role'] != 'patient':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.get_or_404(doctor_id)
        return render_template('doctor_detail.html', doctor=doctor)
    
    @app.route('/admin/doctor/edit/<int:doctor_id>', methods=['GET', 'POST'])
    def edit_doctor(doctor_id):
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.get_or_404(doctor_id)

        if request.method == 'POST':
            doctor.name = request.form['name']
            doctor.phone = request.form['phone']
            doctor.experience = request.form['experience']
            doctor.details = request.form['details']
            doctor.department_id = request.form['department_id']

            db.session.commit()
            flash("Doctor details updated successfully.", "success")
            return redirect(url_for('admin_dashboard'))

        Departments = Department.query.all()
        return render_template('edit_doctor.html', doctor=doctor, Departments=Departments)

    
    # Delete doctor route
    @app.route('/admin/doctor/delete/<int:doctor_id>', methods=['GET', 'POST'])
    def delete_doctor(doctor_id):
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.get_or_404(doctor_id)

        if request.method == 'POST':
            db.session.delete(doctor)
            db.session.commit()
            flash(f"Doctor {doctor.name} deleted successfully!", "success")
            return redirect(url_for('admin_dashboard'))

        return render_template('delete_doctor.html', doctor=doctor)
    
    # Create Department
    @app.route('/admin/department/create', methods=['POST'])
    def create_department():
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        name = request.form.get('name')
        details = request.form.get('details')

        if not name:
            flash("Department name is required", "warning")
            return redirect(url_for('admin_dashboard'))

        # Optional: check if department already exists
        existing = Department.query.filter_by(name=name).first()
        if existing:
            flash("Department already exists", "warning")
            return redirect(url_for('admin_dashboard'))

        new_dept = Department(name=name, details=details)
        db.session.add(new_dept)
        db.session.commit()

        flash(f"Department '{name}' created successfully", "success")
        return redirect(url_for('admin_dashboard'))
    


        # View patient history (Admin)
    @app.route('/admin/patient/<int:patient_id>/history')
    def admin_patient_history(patient_id):
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        patient = Patient.query.get_or_404(patient_id)
        treatment_history = TreatmentHistory.query.filter_by(patient_id=patient.id).order_by(TreatmentHistory.created_at.desc()).all()

        history_data = []
        for visit in treatment_history:
            doctor = Doctor.query.get(visit.doctor_id)
            department = Department.query.get(visit.department_id)
            history_data.append({
                "visit": visit,
                "doctor": doctor,
                "department": department
            })

        user_role = session.get('role')  # pass role instead of current_user
        return render_template(
            'patient_history.html',
            patient=patient,
            history_data=history_data,
            back_url=url_for('admin_dashboard'),
            user_role=user_role
        )
    


    # View Department Details (Admin)
    @app.route('/admin/department/<int:department_id>')
    def admin_department_details(department_id):
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        # Get department record
        department = Department.query.get_or_404(department_id)

        # Get all doctors in this department
        doctors = Doctor.query.filter_by(department_id=department.id).all()

        return render_template('department_detail.html', department=department, doctors=doctors)
    

    #edit department redirecting 
    @app.route('/admin/departments/edit/<int:id>')
    def edit_department(id):
        dept = Department.query.get_or_404(id)
        return render_template('edit_department.html', dept=dept)
    
    #edit department updating
    @app.route('/admin/departments/update/<int:id>', methods=['POST'])
    def update_department(id):
        dept = Department.query.get_or_404(id)

        dept.name = request.form['name']
        dept.details = request.form['details']

        db.session.commit()

        return redirect('/admin/dashboard')  # admin dashboard departments section





    









