
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from datetime import timedelta, date
from utils import *

app = Flask(__name__)

app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_FILE_DIR="/flask_session_data",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    SESSION_REFRESH_EACH_REQUEST=True,
    SESSION_COOKIE_SECURE=True
)
Session(app)

def login_user(email, details, phones):
    session['user_email'] = email
    session['user_type'] = 'customer'
    session['user_first_name'] = details['first_name']
    session['user_last_name'] = details['last_name']
    session['user_passport'] = details['passport']
    session['user_birth_date'] = str(details['birth_date'])
    session['user_phones'] = phones

@app.errorhandler(404)
def invalid_route(e):
    return redirect("/")


@app.route('/')
def homepage():
    user_type = session.get('user_type')
    origins = get_flights_origins()
    destinations = get_flights_destinations()
    today_str = date.today().isoformat()

    if user_type == 'manager':
        return render_template('manager_homepage.html', name=session.get('user_first_name'))

    elif user_type == 'customer':
        return render_template('customer_homepage.html', name=session.get('user_first_name'),origins=origins, destinations=destinations, today=today_str)

    return render_template('homepage.html',origins=origins, destinations=destinations,today=today_str)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    if not registered_customer_exists(email) or not check_password_customer(email, password):
        return render_template('login.html', error="Invalid email or password, email=email")

    else:
        details = get_customer_details(email)
        phones = get_customer_phones(email)
        if details:
            login_user(email, details, phones)
            return redirect(session.pop('next_url', '/'))

    return render_template('login.html', error="An error occurred while logging in.")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html',today=date.today().isoformat())

    email = request.form.get('email')
    passport_number=request.form.get('passport_number')
    birth_date= request.form.get('birth_date')
    password = request.form.get('password')
    first_name=request.form.get('first_name')
    last_name=request.form.get('last_name')
    raw_phones= request.form.getlist('phones')
    phones = [p for p in raw_phones if p.strip()]


    if registered_customer_exists(email):
        return render_template('signup.html', error="This email is taken",today=date.today().isoformat())

    if guest_customer_exists(email):
        turn_into_registered_db(email,first_name,last_name,passport_number,birth_date,date.today(),password,phones)

    else:
        add_customer_to_db(email,first_name,last_name,passport_number,birth_date,date.today(),password, phones)

    details = {
        'first_name': first_name,
        'last_name': last_name,
        'passport': passport_number,
        'birth_date': birth_date
    }
    login_user(email, details, phones)

    return redirect('/')



@app.route('/search_flights', methods=['POST'])
def search_flights():

    flight_date= request.form.get('flight_date')
    origin = request.form.get('origin')
    destination=request.form.get('destination')
    num_seats = int(request.form.get('num_seats'))

    result = get_relevant_flights(flight_date,origin, destination, num_seats)
    if not result:
        return render_template('homepage.html', origins=get_flights_origins(),
                               destinations=get_flights_destinations(),today=date.today().isoformat(), error='No available flights found for the selected criteria.')
    return render_template('show_flights.html', flights=result, requested_seats=num_seats)



@app.route('/select_seats', methods=['POST'])
def select_seats():

    selected_data = request.form.get('selected_option')
    num_seats = int(request.form.get('num_seats'))

    flight_id, class_type, aircraft_id = selected_data.split(',')
    price_per_seat = get_price_for_class(flight_id, class_type)

    session['booking_data'] = {
        'flight_id': flight_id,
        'class_type': class_type,
        'num_seats': num_seats,
        'price_per_seat': price_per_seat,
        'total_price': price_per_seat * num_seats,
        'aircraft_id':aircraft_id
    }

    class_info = get_class_layout(flight_id, class_type)
    vacant_seats = get_vacant_seats(flight_id)
    vacant_set = {(s[1], s[2]) for s in vacant_seats if s[0] == class_type}
    return render_template('seat_selection.html',flight_id=flight_id, class_type=class_type, layout=class_info,vacant_set=vacant_set, num_seats=num_seats)

@app.route('/validate_seats', methods=['POST'])
def validate_seats():
    selected_seats=request.form.getlist("selected_seats")
    booking = session.get('booking_data')

    if len(selected_seats) != booking['num_seats']:
        class_info = get_class_layout(booking['flight_id'], booking['class_type'])
        vacant_seats = get_vacant_seats(booking['flight_id'])
        vacant_set = {(s[1], s[2]) for s in vacant_seats if s[0] == booking['class_type']}
        return render_template('seat_selection.html',
                               flight_id=booking['flight_id'],
                               class_type=booking['class_type'],
                               layout=class_info,
                               vacant_set=vacant_set,
                               num_seats=booking['num_seats'],
                               error=f"Choose exactly {booking['num_seats']} Seats!")

    else:
        booking['selected_seats'] = selected_seats
        session['booking_data'] = booking
        return render_template("passenger_details.html", seats=selected_seats, today=date.today().isoformat())


@app.route('/review_order', methods=['POST'])
def review_order():
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')

    email = request.form.get('email')
    if registered_customer_exists(email) and session.get('user_email') != email:
        session['next_url'] = '/passenger_details_after_login'
        return render_template('passenger_details.html',
                               seats=booking.get('selected_seats'),
                               error=f"the email {email} is already registered.")

    raw_phones = request.form.getlist('phones')
    phones = [p for p in raw_phones if p.strip()]

    booking['phones'] = phones
    booking['first_name'] = request.form.get('first_name')
    booking['last_name'] = request.form.get('last_name')
    booking['email'] = request.form.get('email')
    booking['passport'] = request.form.get('passport')
    booking['birth_date'] = request.form.get('birth_date')

    session['booking_data'] = booking

    return render_template('order_summary.html', data=booking)

@app.route('/edit_passenger_details')
def edit_passenger_details():
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')
    return render_template("passenger_details.html",
                           seats=booking.get('selected_seats'),
                           today=date.today().isoformat())


@app.route('/passenger_details_after_login')
def passenger_details_after_login():
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')

    return render_template("passenger_details.html",
                           seats=booking.get('selected_seats'),
                           today=date.today().isoformat())

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')
    email = booking['email']
    first_name=booking['first_name']
    last_name=booking['last_name']
    flight_id=booking['flight_id']
    booking_date=date.today()
    booking_status='Active'
    payment=booking['total_price']
    aircraft_id=booking['aircraft_id']
    class_type=booking['class_type']
    seats=booking['selected_seats']
    phones=booking['phones']

    order_id=add_booking_to_db(email,first_name,last_name,flight_id,booking_date,booking_status,payment,aircraft_id,class_type,seats,phones)
    session.pop('booking_data', None)
    return render_template('booking_success.html', order_id=order_id)



# --- ממשק לקוח / אורח ---


@app.route('/manage_booking', methods=['GET', 'POST'])
def manage_booking():
    # ניהול הזמנה לפי מספר הזמנה ואימייל [cite: 14, 20, 129]
    pass

@app.route('/booking_history')
def booking_history():
    # צפייה בהיסטוריית הזמנות למשתמשים רשומים בלבד [cite: 66, 71, 158]
    pass


@app.route('/cancel_booking_request', methods=['POST'])
def cancel_booking_request():
    # עמוד ביטול הזמנה ובדיקת תנאי 36 שעות [cite: 134, 138]
    pass

@app.route('/booking_cancelled')
def booking_cancelled():
    # הצגת פרטי הזמנה שבוטלה בהצלחה [cite: 151, 152]
    pass

# --- ממשק מנהל (Admin) ---

@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'GET':
        return render_template('adminlogin.html')

    id=request.form.get('ID')
    password=request.form.get('password')

    if not admin_exists(id):
        return render_template('adminlogin.html' ,error="This ID does not belong to an admin")

    if not check_password_manager(id,password):
        return render_template('adminlogin.html' , error="Incorrect Passsword")

    else:
        return redirect('/')

@app.route('/admin_homepage')
def admin_dashboard():
    # עמוד הבית של המנהל [cite: 168]
    pass

@app.route('/add_flight_step1', methods=['GET', 'POST'])
def add_flight_step1():
    # שלב 1 בהוספת טיסה: בחירת יעד, מקור ותאריך [cite: 187, 192]
    pass

@app.route('/add_flight_step2', methods=['GET', 'POST'])
def add_flight_step2():
    # שלב 2 בהוספת טיסה: בחירת מטוס, צוות ומחירים [cite: 214, 237, 249]
    pass

@app.route('/flight_added_success')
def flight_added_success():
    # דף אישור לאחר הוספת טיסה חדשה [cite: 265, 266]
    pass

@app.route('/flight_board', methods=['GET', 'POST'])
def flight_board():
    # לוח הטיסות למנהל כולל סינונים [cite: 179, 276, 289]
    pass

@app.route('/admin_cancel_flight', methods=['POST'])
def admin_cancel_flight():
    # ביטול טיסה על ידי מנהל ועדכון כל ההזמנות הקשורות [cite: 173, 293, 299]
    pass

if __name__=="__main__":
    app.run(debug=True)

if __name__=="__main__":
    app.run(debug=True)
