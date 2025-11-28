from flask import render_template, request, redirect, url_for, flash, session
from application.database import db
from application.models import User, Patient, Doctor, Appointment, Department, TreatmentHistory
from datetime import date, timedelta
import json 





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

        # Fetch all available departments
        departments = Department.query.all()

        # Fetch upcoming appointments for this patient
        upcoming_appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date.asc()).all()

        return render_template(
            'patient_dash.html',
            patient=patient,
            departments=departments,
            upcoming_appointments=upcoming_appointments
        )

    # Patient logout route
    @app.route('/patient/logout')
    def patient_logout():
        session.clear()
        flash("Logged out successfully.", "success")
        return redirect(url_for('login'))

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

        # Get logged-in doctor
        user_id = session.get('user_id')
        doctor_user = User.query.get(user_id)
        doctor = Doctor.query.filter_by(email=doctor_user.email).first()

        if not doctor:
            flash("Doctor record not found!", "danger")
            return redirect(url_for('login'))

        # Upcoming appointments (status = 'Scheduled')
        upcoming_appointments = Appointment.query.filter_by(
            doctor_id=doctor.id, status='Scheduled'
        ).order_by(Appointment.date.asc()).all()

        # Assigned patients: all patients who have any appointment with this doctor
        assigned_patients = Patient.query.join(
            Appointment, Appointment.patient_id == Patient.id
        ).filter(
            Appointment.doctor_id == doctor.id
        ).distinct().all()

        # Counts for dashboard cards
        total_patients = len(assigned_patients)
        upcoming_appointments_count = len(upcoming_appointments)
        completed_appointments_count = Appointment.query.filter_by(
            doctor_id=doctor.id, status='Completed'
        ).count()

        return render_template(
            'doctor_dash.html',
            doctor=doctor,
            upcoming_appointments=upcoming_appointments,
            assigned_patients=assigned_patients,
            total_patients=total_patients,
            upcoming_appointments_count=upcoming_appointments_count,
            completed_appointments_count=completed_appointments_count
        )

    

        # View doctor details (Admin)
    @app.route('/admin/doctor/<int:doctor_id>')
    def admin_doctor_details(doctor_id):
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.get_or_404(doctor_id)

        # Optional: pass empty slots so template doesn’t break
        slots = {}
        if doctor.available_slots:
            try:
                slots = json.loads(doctor.available_slots)
            except:
                slots = {}

        return render_template('doctor_detail.html', doctor=doctor, slots=slots)



    @app.route('/patient/doctor/<int:doctor_id>')
    def patient_doctor_details(doctor_id):
        if session.get('role') != 'patient':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.get_or_404(doctor_id)

        # Parse JSON availability
        slots = {}
        if doctor.available_slots:
            try:
                slots = json.loads(doctor.available_slots)
            except:
                slots = {}

        return render_template(
            'doctor_detail.html',
            doctor=doctor,
            slots=slots   # <-- REQUIRED
        )

    
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


    #patient viewing there own history
    @app.route('/patient/history')
    def patient_history():
        if 'role' not in session or session['role'] != 'patient':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        user_id = session.get('user_id')
        patient = Patient.query.filter_by(user_id=user_id).first()
        if not patient:
            flash("Patient record not found!", "danger")
            return redirect(url_for('login'))

        treatment_history = TreatmentHistory.query.filter_by(patient_id=patient.id)\
                                                .order_by(TreatmentHistory.created_at.desc()).all()

        history_data = []
        for visit in treatment_history:
            doctor = Doctor.query.get(visit.doctor_id)
            department = Department.query.get(visit.department_id)
            history_data.append({
                "visit": visit,
                "doctor": doctor,
                "department": department
            })

        return render_template('patient_history.html',
                            patient=patient,
                            history_data=history_data,
                            back_url=url_for('patient_dashboard'),
                            user_role='patient')

    #patient viewing departments
    @app.route('/department/<int:department_id>')
    def view_department(department_id):
        if 'role' not in session or session['role'] != 'patient':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        department = Department.query.get_or_404(department_id)
        doctors = Doctor.query.filter_by(department_id=department.id).all()
        return render_template('department_detail.html', department=department, doctors=doctors)
    

    # GET route to display doctor's availability
    @app.route('/doctor/availability')
    def doctor_availability():
        if session.get('role') != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor_user = User.query.get(session.get('user_id'))
        if not doctor_user:
            flash("User not found!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.filter_by(email=doctor_user.email).first()
        if not doctor:
            flash("Doctor record not found!", "danger")
            return redirect(url_for('login'))

        # Parse availability JSON
        slots_data = json.loads(doctor.available_slots) if doctor.available_slots else {}

        # Generate next 7 days
        next_7_days = [date.today() + timedelta(days=i) for i in range(7)]

        return render_template(
            'doctor_avail.html',
            next_7_days=next_7_days,
            slots_data=slots_data,
            doctor=doctor
        )


    # POST route to save doctor's availability
    @app.route('/doctor/availability/save', methods=['POST'])
    def save_availability():
        if session.get('role') != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor_user = User.query.get(session.get('user_id'))
        if not doctor_user:
            flash("User not found!", "danger")
            return redirect(url_for('login'))

        doctor = Doctor.query.filter_by(email=doctor_user.email).first()
        if not doctor:
            flash("Doctor record not found!", "danger")
            return redirect(url_for('login'))

        # Build availability for next 7 days
        next_7_days = [date.today() + timedelta(days=i) for i in range(7)]
        new_slots = {}

        for d in next_7_days:
            d_str = d.isoformat()

            slot1 = request.form.get(f"slot1_{d_str}")
            slot2 = request.form.get(f"slot2_{d_str}")

            # Normalize: empty means None (so booking page hides it)
            slot1 = slot1 if slot1.strip() else None
            slot2 = slot2 if slot2.strip() else None

            new_slots[d_str] = {
                "slot1": slot1,
                "slot2": slot2
            }

        # Store JSON
        doctor.available_slots = json.dumps(new_slots)
        db.session.commit()

        flash("Availability updated!", "success")
        return redirect(url_for('doctor_availability'))



    # POST route to book a slot for a patient
    @app.route('/book/<int:doctor_id>/<date>/<slot_key>', methods=['POST'])
    def book_slot(doctor_id, date, slot_key):
        patient_id = session.get('user_id')
        doctor = Doctor.query.get(doctor_id)

        slots_data = json.loads(doctor.available_slots) if doctor.available_slots else {}

        # Validate slot
        if date not in slots_data or not slots_data[date].get(slot_key):
            flash("This slot is not available!", "danger")
            return redirect(url_for('doctor_dashboard'))

        slot_time = slots_data[date][slot_key]

        # Check if already booked
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id, date=date, slot=slot_time, status='Scheduled'
        ).first()
        if existing:
            flash("Slot already booked!", "danger")
            return redirect(url_for('doctor_availability'))

        # Book the appointment storing actual slot time
        appt = Appointment(doctor_id=doctor_id, patient_id=patient_id, date=date, slot=slot_time)
        db.session.add(appt)

        # Mark slot as unavailable
        slots_data[date][slot_key] = None
        doctor.available_slots = json.dumps(slots_data)

        db.session.commit()
        flash("Appointment booked!", "success")
        return redirect('/doctor/dashboard')

    # Show booking appointment form for a department
    @app.route('/patient/department/<int:department_id>/book', methods=['GET', 'POST'])
    def book_appointment(department_id):
        if session.get('role') != 'patient':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        patient = Patient.query.filter_by(user_id=session.get('user_id')).first()
        if not patient:
            flash("Patient record not found!", "danger")
            return redirect(url_for('login'))

        department = Department.query.get_or_404(department_id)
        doctors = Doctor.query.filter_by(department_id=department.id).all()

        # Prepare next 7 days
        next_7_days = [date.today() + timedelta(days=i) for i in range(7)]
        available_dates = [d.isoformat() for d in next_7_days]

        # Determine selected doctor
        if request.method == 'POST':
            doctor_id = request.form.get('doctor_id')
            selected_doctor = Doctor.query.get(int(doctor_id)) if doctor_id else (doctors[0] if doctors else None)
            appointment_date = request.form.get('appointment_date') or (available_dates[0] if available_dates else None)
        else:
            selected_doctor = doctors[0] if doctors else None
            appointment_date = available_dates[0] if available_dates else None

        # Load slots safely
        slots_data = json.loads(selected_doctor.available_slots) if selected_doctor and selected_doctor.available_slots else {}

        # Handle booking POST
        if request.method == 'POST' and 'slot' in request.form:
            slot_key = request.form.get('slot')
            doctor = selected_doctor

            if not doctor or appointment_date not in slots_data or slots_data[appointment_date].get(slot_key) is None:
                flash("Selected slot is not available!", "danger")
                return redirect(url_for('book_appointment', department_id=department_id))

            slot_time = slots_data[appointment_date][slot_key]

            existing = Appointment.query.filter_by(
                doctor_id=doctor.id, date=appointment_date, slot=slot_time, status='Scheduled'
            ).first()
            if existing:
                flash("This slot is already booked!", "danger")
                return redirect(url_for('book_appointment', department_id=department_id))

            # Create appointment
            new_appt = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                department_id=department.id,
                date=appointment_date,
                slot=slot_time
            )
            db.session.add(new_appt)

            # Mark slot unavailable
            slots_data[appointment_date][slot_key] = None
            doctor.available_slots = json.dumps(slots_data)
            db.session.commit()

            flash("Appointment booked successfully!", "success")
            return redirect(url_for('patient_dashboard'))

        return render_template(
            'appointment.html',
            department=department,
            doctors=doctors,
            available_dates=available_dates,
            selected_doctor=selected_doctor,
            slots_data=slots_data,
            appointment_date=appointment_date
        )

    # Patients canceling appointments
    @app.route('/patient/appointment/cancel/<int:appointment_id>', methods=['POST'])
    def cancel_appointment(appointment_id):
        if session.get('role') != 'patient':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        patient = Patient.query.filter_by(user_id=session.get('user_id')).first()
        if not patient:
            flash("Patient record not found!", "danger")
            return redirect(url_for('login'))

        appointment = Appointment.query.get_or_404(appointment_id)

        if appointment.patient_id != patient.id:
            flash("You cannot cancel this appointment.", "danger")
            return redirect(url_for('patient_dashboard'))

        # Restore the slot in doctor's availability by key
        doctor = Doctor.query.get(appointment.doctor_id)
        slots_data = json.loads(doctor.available_slots) if doctor.available_slots else {}

        if appointment.date in slots_data:
            # Find the first empty slot and restore the time
            for key, val in slots_data[appointment.date].items():
                if val is None:
                    slots_data[appointment.date][key] = appointment.slot
                    break
            doctor.available_slots = json.dumps(slots_data)

        db.session.delete(appointment)
        db.session.commit()
        flash("Appointment cancelled successfully!", "success")
        return redirect(url_for('patient_dashboard'))

    # Show update form
    @app.route('/doctor/patient/<int:patient_id>/update', methods=['GET'])
    def update_patient_history(patient_id):
        if 'role' not in session or session['role'] != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        patient = Patient.query.get_or_404(patient_id)
        doctor = Doctor.query.get_or_404(session['user_id'])

        # Fetch department
        department = Department.query.get_or_404(doctor.department_id)

        # Get existing history record OR create empty object
        history = TreatmentHistory.query.filter_by(
            doctor_id=doctor.id,
            patient_id=patient.id
        ).first()

        if not history:
            history = TreatmentHistory(
                doctor_id=doctor.id,
                patient_id=patient.id,
                department_id=doctor.department_id,
                visit_type='',
                test_done='',
                diagnosis='',
                prescription='',
                medicines=''
            )
            db.session.add(history)
            db.session.commit()

        return render_template(
            'update_history.html',
            patient=patient,
            doctor=doctor,
            department=department,
            history=history
        )


    # Save updates
    @app.route('/doctor/patient/<int:patient_id>/update', methods=['POST'])
    def save_patient_history(patient_id):
        if 'role' not in session or session['role'] != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        doctor_id = session['user_id']

        history = TreatmentHistory.query.filter_by(
            doctor_id=doctor_id, 
            patient_id=patient_id
        ).first_or_404()

        history.visit_type = request.form.get('visit_type')
        history.test_done = request.form.get('test_done')
        history.diagnosis = request.form.get('diagnosis')
        history.prescription = request.form.get('prescription')
        history.medicines = request.form.get('medicines')

        db.session.commit()

        flash("Patient history updated successfully!", "success")
        return redirect(url_for('view_patient_history', patient_id=patient_id))


    # View patient history
    @app.route('/doctor/patient/<int:patient_id>/history')
    def view_patient_history(patient_id):
        if 'role' not in session:
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        history_data = TreatmentHistory.query.filter_by(patient_id=patient_id).all()

        return render_template(
            'patient_history.html',
            history_data=history_data,
            user_role=session['role'],
            back_url=url_for('doctor_dashboard')
        )


    @app.route('/doctor/appointment/<int:appointment_id>/update', methods=['GET'])
    def doctor_update_appointment(appointment_id):
        if session.get('role') != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        appointment = Appointment.query.get_or_404(appointment_id)
        doctor = Doctor.query.filter_by(email=User.query.get(session['user_id']).email).first()
        if appointment.doctor_id != doctor.id:
            flash("You cannot edit this appointment.", "danger")
            return redirect(url_for('doctor_dashboard'))

        patient = Patient.query.get(appointment.patient_id)
        department = Department.query.get(appointment.department_id)

        # Fetch existing history OR create empty one
        history = TreatmentHistory.query.filter_by(
            doctor_id=doctor.id,
            patient_id=patient.id
        ).first()

        if not history:
            history = TreatmentHistory(
                doctor_id=doctor.id,
                patient_id=patient.id,
                department_id=doctor.department_id,
                visit_type='',
                test_done='',
                diagnosis='',
                prescription='',
                medicines=''
            )
            db.session.add(history)
            db.session.commit()

        return render_template(
            'update_history.html',
            appointment=appointment,
            patient=patient,
            doctor=doctor,
            department=department,
            history=history  # <-- pass it here
        )



    # MARK Appointment as Completed
    @app.route('/doctor/appointment/<int:appointment_id>/complete')
    def doctor_complete_appointment(appointment_id):
        if session.get('role') != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        appointment = Appointment.query.get_or_404(appointment_id)
        doctor = Doctor.query.filter_by(email=User.query.get(session['user_id']).email).first()
        if appointment.doctor_id != doctor.id:
            flash("You cannot modify this appointment.", "danger")
            return redirect(url_for('doctor_dashboard'))

        appointment.status = 'Completed'
        db.session.commit()
        flash("Appointment marked as completed!", "success")
        return redirect(url_for('doctor_dashboard'))


    # CANCEL Appointment (doctor cancels)
    @app.route('/doctor/appointment/<int:appointment_id>/cancel', methods=['POST'])
    def doctor_cancel_appointment(appointment_id):
        if session.get('role') != 'doctor':
            flash("Access denied!", "danger")
            return redirect(url_for('login'))

        appointment = Appointment.query.get_or_404(appointment_id)
        doctor = Doctor.query.filter_by(email=User.query.get(session['user_id']).email).first()
        if appointment.doctor_id != doctor.id:
            flash("You cannot cancel this appointment.", "danger")
            return redirect(url_for('doctor_dashboard'))

        # Optional: restore slot in doctor's availability
        if doctor.available_slots:
            slots_data = json.loads(doctor.available_slots)
            if appointment.date in slots_data:
                for key, val in slots_data[appointment.date].items():
                    if val is None:
                        slots_data[appointment.date][key] = appointment.slot
                        break
                doctor.available_slots = json.dumps(slots_data)

        db.session.delete(appointment)
        db.session.commit()
        flash("Appointment canceled successfully!", "success")
        return redirect(url_for('doctor_dashboard'))
