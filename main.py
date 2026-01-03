
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
        return render_template('admin_homepage.html', name=session.get('user_first_name'))

    elif user_type == 'customer':
        return render_template('customer_homepage.html', name=session.get('user_first_name'),origins=origins, destinations=destinations, today=today_str)

    return render_template('homepage.html',origins=origins, destinations=destinations,today=today_str)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    if not customer_exists(email):
        return render_template(
            'login.html',
            error="User not found. Please register or place an order as a guest."
        )

    if not registered_customer_exists(email):
        return render_template(
            'login.html',
            error="This email belongs to a guest. Please register to log in."
        )

    if not check_password_customer(email, password):
        return render_template(
            'login.html',
            error="Incorrect password.", email=email
        )

    else:
        session['user_email'] = email
        session['user_type'] = 'customer'
        session['user_first_name'] = get_customer_details(email)[0]
        session['user_last_name'] = get_customer_details(email)[1]
        session['user_passport'] = get_customer_details(email)[2]
        session['user_birth_date'] = get_customer_details(email)[3]
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        today_str = date.today().isoformat()
        return render_template('signup.html',today=today_str)

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

    if customer_exists(email):
        turn_into_registered_db(email,first_name,last_name,passport_number,birth_date,date.today(),password,phones)
        session['user_email'] = email
        session['user_type'] = 'customer'
        session['user_first_name'] = get_customer_details(email)[0]
        session['user_last_name'] = get_customer_details(email)[1]
        session['user_passport'] = get_customer_details(email)[2]
        session['user_birth_date'] = get_customer_details(email)[3]
        return redirect('/')

    else:
        add_customer_to_db(email,first_name,last_name,passport_number,birth_date,date.today(),password, phones)
        session['user_email'] = email
        session['user_type'] = 'customer'
        session['user_first_name'] = get_customer_details(email)[0]
        session['user_last_name'] = get_customer_details(email)[1]
        session['user_passport'] = get_customer_details(email)[2]
        session['user_birth_date'] = get_customer_details(email)[3]
        return redirect('/')



@app.route('/search_flights', methods=['POST'])
def search_flights():
    flight_date= request.form.get('flight_date')
    origin = request.form.get('origin')
    destination=request.form.get('destination')
    num_seats = request.form.get('num_seats')

    result = get_relevant_flights(flight_date,origin, destination, num_seats)
    if not result:
        return render_template('homepage.html', origins=get_flights_origins(),
                               destinations=get_flights_destinations(),today=date.today().isoformat(), error='No available flights. Please select differently')
    return render_template('show_flights.html', flights=result, requested_seats=num_seats)



@app.route('/select_seats', methods=['POST'])
def select_seats():
    selected_data = request.form.get('selected_option')
    num_seats = int(request.form.get('num_seats'))
    flight_id, class_type = selected_data.split(',')
    price_per_seat = get_price_for_class(flight_id, class_type)

    session['booking_data'] = {
        'flight_id': flight_id,
        'class_type': class_type,
        'num_seats': num_seats,
        'price_per_seat': price_per_seat,
        'total_price': price_per_seat * num_seats
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

    booking['first_name'] = request.form.get('first_name')
    booking['last_name'] = request.form.get('last_name')
    booking['email'] = request.form.get('email')
    booking['passport'] = request.form.get('passport')
    booking['birth_date'] = request.form.get('birth_date')

    session['booking_data'] = booking

    return render_template('order_summary.html', data=booking)

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    pass


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

    first_name, last_name = get_admin_details(id)
    if first_name is None:
        return render_template('adminlogin.html', error="Admin details not found")

    else:
        session['user_type'] = 'manager'
        session['user_id'] = id
        session['user_first_name'] = first_name
        session['user_last_name'] = last_name
        return redirect('/admin_homepage')


@app.route('/admin_homepage')
def admin_dashboard():
    user_type = session.get('user_type')
    if user_type == 'manager':
        show_cancel = request.args.get('show_cancel') == 'true'
        return render_template('admin_homepage.html', name=session.get('user_first_name'),show_cancel=show_cancel)

    else:
        return redirect("/adminlogin")


@app.route('/add_flight_step1', methods=['POST', 'GET'])
def add_flight_step1():
    # הוצאת נתוני בסיס למשתנה כדי למנוע כפילויות בקוד
    common_data = {
        'origins': get_flights_origins(),
        'destinations': get_flights_destinations(),
        'today': date.today().isoformat(),
        'name': session.get('user_first_name')
    }

    if request.method == 'GET':
        return render_template('add_flight_1.html', **common_data)

    # שליפת נתונים מהטופס
    flight_date = request.form.get('flight_date')
    departure_time = request.form.get("departure_time")
    origin = request.form.get('origin')
    destination = request.form.get('destination')

    # בדיקת תקינות בסיסית לפני הניתוח הכבד
    if not all([flight_date, departure_time, origin, destination]):
        return render_template('add_flight_1.html', **common_data, error='All fields are required.')

    # קריאה לפונקציית השירות (היוטילס) שעברנו עליה
    aircraft_result = get_available_aircraft(flight_date, origin, destination, departure_time)

    if not aircraft_result:
        return render_template(
            'add_flight_1.html',
            **common_data,
            error='No available Aircraft for this route/time. Please select differently.'
        )

    # מעבר לשלב 2 עם כל הנתונים הדרושים
    return render_template(
        'add_flight_2.html',
        aircraft=aircraft_result,
        flight_date=flight_date,
        departure_time=departure_time,
        origin=origin,
        destination=destination,
        name=common_data['name']  # שמירה על עקביות שם המשתמש
    )


@app.route('/add_flight_step2', methods=['POST'])
def add_flight_step2():
    # שליפת נתוני הטיסה מהשלב הקודם
    flight_date = request.form.get('flight_date')
    departure_time = request.form.get("departure_time")
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    aircraft_id = request.form.get('selected_aircraft')
    user_name = session.get('user_first_name')

    # קבלת פרטי המטוס הספציפי שנבחר
    size = request.form.get(f'size_{aircraft_id}')
    manufacturer = request.form.get(f'manufacturer_{aircraft_id}')

    # קריאה ליוטילס החדש של הטייסים
    pilot_result = get_available_pilots(flight_date, origin, destination, departure_time)

    # לוגיקה לפי גודל מטוס
    required_pilots = 2 if size == 'Small' else 3

    if len(pilot_result) >= required_pilots:
        aircraft_data = {
            'aircraft_id': aircraft_id,
            'size': size,
            'manufacturer': manufacturer
        }

        return render_template(
            'add_flight_3.html',
            aircraft=aircraft_data,
            pilots=pilot_result,
            flight_date=flight_date,
            departure_time=departure_time,
            origin=origin,
            destination=destination,
            required_pilots=required_pilots,
            name=user_name
        )
    else:
        # <<< שינוי כאן: הוספת הנתונים שנבחרו כדי להחזיר אותם לטופס >>>
        return render_template(
            'add_flight_1.html',
            name=user_name,
            origins=get_flights_origins(),
            destinations=get_flights_destinations(),
            today=date.today().isoformat(),
            error=f'Not enough available Pilots for a {size} aircraft ({len(pilot_result)}/{required_pilots} available).',
            # הנתונים האלו יישלחו בחזרה לדף הראשון:
            saved_date=flight_date,
            saved_origin=origin,
            saved_destination=destination,
            saved_time=departure_time
        )

@app.route('/add_flight_step3', methods=['POST'])
def add_flight_step3():
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
    flight_id=request.form.get('flight_number')
    flight_id, flight_status, departure_time, departure_date, origin_airport, destination_airport, aircraft_id= get_flight_details(flight_id)
    cancel_time=can_cant_cancel_flight(flight_id)
    return render_template('cancel_flight.html',flight_id=flight_id,flight_status=flight_status,
                           departure_time=departure_time,departure_date=departure_date,
                           origin_airport=origin_airport,destination_airport=destination_airport,
                           aircraft_id=aircraft_id,cancel_time=cancel_time)

@app.route('/admin_cancel_flight/confirm', methods=['POST'])
def admin_cancel_flight_confirm():
    flight_id = request.form.get('flight_number')
    cancel_flight(flight_id)
    cancel_booking(flight_id)
    return render_template('cancel_flight_confirm.html', flight_id=flight_id)


if __name__=="__main__":
    app.run(debug=True)

if __name__=="__main__":
    app.run(debug=True)
