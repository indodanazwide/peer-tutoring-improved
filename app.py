from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Module, TutorModule, TutorAvailability, Booking
from datetime import datetime, date
import os
from flask_mail import Mail, Message

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'peer_tutoring.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'  # For session management and flash messages

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tloumoloto2003@gmail.com'  # Your email
app.config['MAIL_PASSWORD'] = 'yttncbjvlsaxqtyd'  # App password after turning on 2-step verification
app.config['MAIL_DEFAULT_SENDER'] = 'tloumoloto2003@gmail.com'

db.init_app(app)
mail = Mail(app)

def send_booking_confirmation(student_email, student_name, tutor_name, session_time):
    """
    Sends a booking confirmation email to the student.
    """
    subject = "Booking Confirmation"
    body = f"""Hi {student_name},
    Your tutoring session has been successfully booked!

    Details:
    Tutor: {tutor_name}
    Date and Time: {session_time.strftime('%Y-%m-%d %H:%M')}

    We look forward to helping you succeed!

    Best,
    The Tutoring Team
    """
    msg = Message(subject=subject, recipients=[student_email], body=body)
    try:
        mail.send(msg)
        flash("Booking successful! A confirmation email has been sent.", 'success')
    except Exception as e:
        flash(f"Booking successful, but the email failed to send: {str(e)}", 'warning')

# Ensure the database and tables are created
with app.app_context():
    db.create_all()

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Sign-up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('signup'))

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))

        # Create a new user
        new_user = User(
            username=username,
            password=password,
            role='student',  # Default role for new users
            name=name,
            surname=surname,
            email=email
        )

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        # Log the user in
        session['user_id'] = new_user.user_id
        session['role'] = new_user.role
        session['username'] = new_user.username

        flash('Sign-up successful! You are now logged in.', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('signup.html')

# View bookings route
@app.route('/view_bookings')
def view_bookings():
    if 'user_id' not in session or session['role'] != 'student':
        flash('Please log in as a student', 'error')
        return redirect(url_for('login'))

    student_id = session['user_id']
    # Fetch bookings with related module, tutor, and availability details
    bookings = (
        Booking.query
        .filter_by(student_id=student_id)
        .join(Module, Booking.module_id == Module.module_id)
        .join(User, Booking.tutor_id == User.user_id)
        .join(TutorAvailability, Booking.availability_id == TutorAvailability.availability_id)
        .all()
    )
    return render_template('view_bookings.html', bookings=bookings)

# List all users (for debugging)
@app.route('/users')
def list_users():
    users = User.query.all()
    return str([(u.username, u.password, u.role) for u in users])

# Homepage
@app.route('/')
def home():
    return render_template('home.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            # Set session data
            session['user_id'] = user.user_id
            session['role'] = user.role
            session['username'] = user.username

            # Redirect based on role
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'tutor':
                return redirect(url_for('tutor_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid role assigned to user.', 'error')
                return redirect(url_for('login'))

        flash('Invalid credentials', 'error')
    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Redirect based on role
    if session['role'] == 'student':
        return redirect(url_for('student_dashboard'))
    elif session['role'] == 'tutor':
        return redirect(url_for('tutor_dashboard'))
    elif session['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid role assigned to user.', 'error')
        return redirect(url_for('login'))

# Student Dashboard
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        flash('Please log in as a student', 'error')
        return redirect(url_for('login'))

    modules = Module.query.all()
    return render_template('student_dash.html', modules=modules)

# Search Modules Route (New)
@app.route('/search_modules', methods=['GET', 'POST'])
def search_modules():
    if 'user_id' not in session or session['role'] != 'student':
        flash('Please log in as a student', 'error')
        return redirect(url_for('login'))

    modules = []
    search_term = ''

    if request.method == 'POST':
        search_term = request.form.get('search_term', '').strip()
        if search_term:
            modules = Module.query.filter(
                (Module.module_code.ilike(f'%{search_term}%')) |
                (Module.module_name.ilike(f'%{search_term}%'))
            ).all()
            
    module_tutors = {}
    for module in modules:
        tutors = User.query.join(TutorModule).filter(
            TutorModule.module_id == module.module_id,
            User.role == 'tutor'
        ).all()
        module_tutors[module.module_id] = tutors

    return render_template('search_modules.html', modules=modules, module_tutors=module_tutors, search_term=search_term)

# Tutor Dashboard
@app.route('/tutor_dashboard')
def tutor_dashboard():
    if 'user_id' not in session or session['role'] != 'tutor':
        flash('Please log in as a tutor', 'error')
        return redirect(url_for('login'))

    # Fetch tutor-specific data (e.g., modules they teach, availability, bookings)
    tutor_id = session['user_id']
    tutor_modules = TutorModule.query.filter_by(tutor_id=tutor_id).all()
    modules = [Module.query.get(tm.module_id) for tm in tutor_modules]

    # Fetch tutor's availability slots
    availability = (
        TutorAvailability.query
        .filter_by(tutor_id=tutor_id)
        .join(Module, TutorAvailability.module_id == Module.module_id)
        .all()
    )

    return render_template('tutor_dash.html', modules=modules, availability=availability)

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Please log in as an admin', 'error')
        return redirect(url_for('login'))

    # Fetch all tutors
    tutors = User.query.filter_by(role='tutor').all()
    return render_template('admin_dash.html', tutors=tutors)

# View Tutor Details
@app.route('/view_tutor/<int:tutor_id>')
def view_tutor(tutor_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Please log in as an admin', 'error')
        return redirect(url_for('login'))

    # Fetch the tutor
    tutor = User.query.get_or_404(tutor_id)

    # Fetch the tutor's assigned modules
    tutor_modules = TutorModule.query.filter_by(tutor_id=tutor_id).all()
    modules = [Module.query.get(tm.module_id) for tm in tutor_modules]

    # Fetch the tutor's availability slots
    availability = (
        TutorAvailability.query
        .filter_by(tutor_id=tutor_id)
        .join(Module, TutorAvailability.module_id == Module.module_id)
        .all()
    )

    return render_template('view_tutor.html', tutor=tutor, modules=modules, availability=availability)

# Edit Tutor Details
@app.route('/edit_tutor/<int:tutor_id>', methods=['GET', 'POST'])
def edit_tutor(tutor_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Please log in as an admin', 'error')
        return redirect(url_for('login'))

    tutor = User.query.get_or_404(tutor_id)
    modules = Module.query.all()
    availability = TutorAvailability.query.filter_by(tutor_id=tutor_id).all()

    if request.method == 'POST':
        # Update tutor details
        tutor.name = request.form['name']
        tutor.surname = request.form['surname']
        tutor.username = request.form['username']
        tutor.password = request.form['password']

        # Update module assignments
        module_ids = request.form.getlist('module_ids')
        TutorModule.query.filter_by(tutor_id=tutor_id).delete()  # Remove existing assignments
        for module_id in module_ids:
            new_assignment = TutorModule(tutor_id=tutor_id, module_id=module_id)
            db.session.add(new_assignment)

        # Update availability
        availability_ids = request.form.getlist('availability_ids')
        TutorAvailability.query.filter_by(tutor_id=tutor_id).delete()  # Remove existing availability
        for availability_id in availability_ids:
            day_of_week = request.form[f'day_of_week_{availability_id}']
            start_time = datetime.strptime(request.form[f'start_time_{availability_id}'], '%H:%M').time()
            end_time = datetime.strptime(request.form[f'end_time_{availability_id}'], '%H:%M').time()
            module_id = request.form[f'module_id_{availability_id}']
            new_availability = TutorAvailability(
                tutor_id=tutor_id,
                module_id=module_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(new_availability)

        db.session.commit()
        flash('Tutor details updated successfully!', 'success')
        return redirect(url_for('view_tutor', tutor_id=tutor_id))  # Redirect to view_tutor after editing

    return render_template('edit_tutor.html', tutor=tutor, modules=modules, availability=availability)

# Remove Tutor
@app.route('/remove_tutor/<int:tutor_id>', methods=['GET', 'POST'])
def remove_tutor(tutor_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Please log in as an admin', 'error')
        return redirect(url_for('login'))

    tutor = User.query.get_or_404(tutor_id)

    if request.method == 'POST':
        # Delete related records
        Booking.query.filter_by(tutor_id=tutor_id).delete()
        TutorAvailability.query.filter_by(tutor_id=tutor_id).delete()
        TutorModule.query.filter_by(tutor_id=tutor_id).delete()
        User.query.filter_by(user_id=tutor_id).delete()

        db.session.commit()
        flash('Tutor removed successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('remove_tutor.html', tutor=tutor)

# Add Tutor
@app.route('/add_tutor', methods=['GET', 'POST'])
def add_tutor():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Please log in as an admin', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']  # Ensure email is included in the form

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('add_tutor'))

        # Check if the email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already exists. Please use a different email address.', 'error')
            return redirect(url_for('add_tutor'))

        # Create a new user
        new_tutor = User(
            username=username,
            password=password,
            role='tutor',
            name=name,
            surname=surname,
            email=email  # Include the email field
        )

        # Add the new user to the database
        db.session.add(new_tutor)
        db.session.commit()

        # Assign modules
        module_ids = request.form.getlist('module_ids')
        for module_id in module_ids:
            new_assignment = TutorModule(tutor_id=new_tutor.user_id, module_id=module_id)
            db.session.add(new_assignment)

        # Add availability
        availability_count = int(request.form['availability_count'])
        for i in range(availability_count):
            day_of_week = request.form[f'day_of_week_{i}']
            start_time = datetime.strptime(request.form[f'start_time_{i}'], '%H:%M').time()
            end_time = datetime.strptime(request.form[f'end_time_{i}'], '%H:%M').time()
            module_id = request.form[f'module_id_{i}']
            new_availability = TutorAvailability(
                tutor_id=new_tutor.user_id,
                module_id=module_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(new_availability)

        db.session.commit()
        flash('Tutor added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    modules = Module.query.all()
    return render_template('add_tutor.html', modules=modules)

# Book a Session
@app.route('/book_session/<int:module_id>', methods=['GET', 'POST'])
def book_session(module_id):
    if 'user_id' not in session or session['role'] != 'student':
        flash('Please log in as a student', 'error')
        return redirect(url_for('login'))

    module = Module.query.get_or_404(module_id)
    tutor_modules = TutorModule.query.filter_by(module_id=module_id).all()
    tutor_ids = [tm.tutor_id for tm in tutor_modules]
    tutors = User.query.filter(User.user_id.in_(tutor_ids), User.role == 'tutor').all()

    if request.method == 'POST':
        try:
            tutor_id = int(request.form['tutor_id'])
            availability_id = int(request.form['availability_id'])
            booking_date_str = request.form['booking_date']
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        except KeyError as e:
            flash(f'Missing required field: {e.args[0]}', 'error')
            return redirect(url_for('book_session', module_id=module_id))
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('book_session', module_id=module_id))

        availability = TutorAvailability.query.filter_by(
            availability_id=availability_id,
            tutor_id=tutor_id,
            module_id=module_id
        ).first()

        if not availability:
            flash('Invalid availability slot.', 'error')
            return redirect(url_for('book_session', module_id=module_id))

        days_of_week = {
            'Monday': 0,
            'Tuesday': 1,
            'Wednesday': 2,
            'Thursday': 3,
            'Friday': 4,
            'Saturday': 5,
            'Sunday': 6
        }

        booking_weekday = booking_date.weekday()
        if booking_weekday != days_of_week.get(availability.day_of_week):
            flash(f'Invalid date. Please select a date that falls on {availability.day_of_week}.', 'error')
            return redirect(url_for('book_session', module_id=module_id))

        if booking_date < date.today():
            flash('Cannot book a session in the past.', 'error')
            return redirect(url_for('book_session', module_id=module_id))

        existing_booking = Booking.query.filter_by(
            tutor_id=tutor_id,
            module_id=module_id,
            availability_id=availability_id,
            booking_date=booking_date
        ).first()

        if existing_booking:
            flash('This slot is already booked.', 'error')
            return redirect(url_for('book_session', module_id=module_id))

        new_booking = Booking(
            student_id=session['user_id'],
            tutor_id=tutor_id,
            module_id=module_id,
            availability_id=availability_id,
            booking_date=booking_date
        )
        db.session.add(new_booking)
        db.session.commit()

        # Fetch student and tutor details
        student = User.query.get(session['user_id'])
        tutor = User.query.get(tutor_id)
        session_time = datetime.combine(booking_date, availability.start_time)

        # Send booking confirmation email
        send_booking_confirmation(
            student_email=student.email,  # Use the student's email from the database
            student_name=student.name,
            tutor_name=f"{tutor.name} {tutor.surname}",
            session_time=session_time
        )

        # Flash message for successful booking
        flash('Your class has been successfully booked!', 'success')

        # Redirect to view_bookings
        return redirect(url_for('view_bookings'))

    selected_tutor_id = request.args.get('tutor_id', type=int)
    availability_slots = []
    if selected_tutor_id:
        availability_slots = TutorAvailability.query.filter_by(
            tutor_id=selected_tutor_id,
            module_id=module_id
        ).all()

    today = date.today().isoformat()
    return render_template('book_session.html', module=module, tutors=tutors, availability_slots=availability_slots, selected_tutor_id=selected_tutor_id, today=today)

# Remove Booking
@app.route('/remove_booking/<int:booking_id>')
def remove_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'tutor':
        flash('Please log in as a tutor', 'error')
        return redirect(url_for('login'))

    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()

    flash('Booking removed successfully!', 'success')
    return redirect(url_for('view_tutor_bookings'))

# Edit Booking
@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'tutor':
        flash('Please log in as a tutor', 'error')
        return redirect(url_for('login'))

    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        # Update booking details
        booking_date_str = request.form['booking_date']
        try:
            booking.booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'error')
            return redirect(url_for('edit_booking', booking_id=booking_id))

        # Notify the student
        flash(f'Booking for {booking.module.module_name} on {booking.booking_date} has been updated.', 'info')

        db.session.commit()
        flash('Booking updated successfully!', 'success')
        return redirect(url_for('view_tutor_bookings'))

    return render_template('edit_booking.html', booking=booking)

# View Tutor Bookings
@app.route('/view_tutor_bookings')
def view_tutor_bookings():
    if 'user_id' not in session or session['role'] != 'tutor':
        flash('Please log in as a tutor', 'error')
        return redirect(url_for('login'))

    # Fetch the logged-in tutor's bookings
    tutor_id = session['user_id']
    bookings = (
        Booking.query
        .filter_by(tutor_id=tutor_id)
        .join(User, Booking.student_id == User.user_id)  # Join to get student details
        .join(Module, Booking.module_id == Module.module_id)  # Join to get module details
        .join(TutorAvailability, Booking.availability_id == TutorAvailability.availability_id)  # Join to get availability details
        .all()
    )

    return render_template('view_tutor_bookings.html', bookings=bookings)


#edit student bookings on there side
@app.route('/edit_student_booking/<int:booking_id>', methods=['GET', 'POST'])
def edit_student_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'student':
        flash('Please log in as a student', 'error')
        return redirect(url_for('login'))

    # Fetch the booking
    booking = Booking.query.get_or_404(booking_id)

    # Ensure the booking belongs to the logged-in student
    if booking.student_id != session['user_id']:
        flash('You do not have permission to edit this booking.', 'error')
        return redirect(url_for('view_bookings'))

    if request.method == 'POST':
        try:
            # Get the new booking date from the form
            booking_date_str = request.form['booking_date']
            new_booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()

            # Fetch the availability slot for the booking
            availability = TutorAvailability.query.get(booking.availability_id)

            # Check if the new date falls on the correct day of the week
            days_of_week = {
                'Monday': 0,
                'Tuesday': 1,
                'Wednesday': 2,
                'Thursday': 3,
                'Friday': 4,
                'Saturday': 5,
                'Sunday': 6
            }

            new_booking_weekday = new_booking_date.weekday()
            if new_booking_weekday != days_of_week.get(availability.day_of_week):
                flash(f'Invalid date. Please select a date that falls on {availability.day_of_week}.', 'error')
                return redirect(url_for('edit_student_booking', booking_id=booking_id))

            # Check if the new date is in the past
            if new_booking_date < date.today():
                flash('Cannot book a session in the past.', 'error')
                return redirect(url_for('edit_student_booking', booking_id=booking_id))

            # Check if the new date and time slot are already booked
            existing_booking = Booking.query.filter(
                Booking.tutor_id == booking.tutor_id,
                Booking.module_id == booking.module_id,
                Booking.availability_id == booking.availability_id,
                Booking.booking_date == new_booking_date
            ).first()

            if existing_booking and existing_booking.booking_id != booking.booking_id:
                flash('This slot is already booked.', 'error')
                return redirect(url_for('edit_student_booking', booking_id=booking_id))

            # Update the booking date
            booking.booking_date = new_booking_date
            db.session.commit()

            flash('Booking updated successfully!', 'success')
            return redirect(url_for('view_bookings'))

        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('edit_student_booking', booking_id=booking_id))

    return render_template('edit_student_booking.html', booking=booking)
#ends here


@app.route('/view_all_users')
def view_all_users():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Please log in as an admin', 'error')
        return redirect(url_for('login'))

    # Fetch all users from the database
    users = User.query.all()
    return render_template('view_all_users.html', users=users)


# Run the application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables
    app.run(debug=True)