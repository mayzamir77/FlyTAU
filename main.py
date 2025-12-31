
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from datetime import timedelta, date
from utils import *

print("main started")

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


# --- ממשק לקוח / אורח --- רונה

@app.route('/manage_booking', methods=['GET', 'POST'])   #when customer searches booking in homepage
def manage_booking():

    if request.method == 'GET':     #when the form wasnt filled
        return redirect('/')    #go to homepage

    booking_id = int(request.form.get('booking_ID'))  #getting the fields the customer filled

    if session.get('user_type') == 'customer':   #if customer in session
        email = session.get('user_email')

    else:
        email = request.form.get('booking_email')    #customer not in session

    booking = get_booking_details(booking_id, email)    #getting all the booking details from db

    if not booking:  #if booking doesnt exist
        origins = get_flights_origins()
        destinations = get_flights_destinations()
        today_str = date.today().isoformat()

        if session.get('user_type') == 'customer':   #if registered customer
            return render_template(
                'customer_homepage.html',
                name=session.get('user_first_name'),
                origins=origins,
                destinations=destinations,
                today=today_str,
                manage_booking_error="Booking doesn't exist. Please check details."
            )

        return render_template(                #if not registered customer
            'homepage.html',
            origins=origins,
            destinations=destinations,
            today=today_str,
            manage_booking_error="Booking doesn't exist. Please check details."
        )

    if booking.booking_status != 'Active':
        origins = get_flights_origins()
        destinations = get_flights_destinations()
        today_str = date.today().isoformat()

        error_msg = "This booking is no longer active and cannot be managed."

        if session.get('user_type') == 'customer':
            return render_template(
                'customer_homepage.html',
                name=session.get('user_first_name'),
                origins=origins,
                destinations=destinations,
                today=today_str,
                manage_booking_error=error_msg
            )

        return render_template(
            'homepage.html',
            origins=origins,
            destinations=destinations,
            today=today_str,
            manage_booking_error=error_msg
        )

    departure_date = booking.departure_date
    departure_time = booking.departure_time
    payment = booking.payment
    can_cancel = can_cancel_booking(departure_date, departure_time)
    cancellation_fee = calculate_cancellation_fee(payment)

    return render_template('manage_booking.html',booking=booking, can_cancel=can_cancel, cancellation_fee=cancellation_fee, back_url=request.referrer)  #if booking exists


@app.route('/cancel_booking_request', methods=['GET', 'POST'])
def cancel_booking_request():

    if request.method == 'GET':     #when the form wasnt filled
        return redirect('/')    #go to homepage

    booking_id = int(request.form.get('booking_id'))

    if session.get('user_type') == 'customer':
        email = session.get('user_email')
    else:
        email = request.form.get('booking_email')

    booking = get_booking_details(booking_id, email)
    payment = booking.payment

    cancellation_fee = calculate_cancellation_fee(payment)

    cancel_booking_in_db(booking_id)

    return render_template(
        'booking_cancelled.html',
        booking_id=booking_id,
        cancellation_fee=cancellation_fee
    )


@app.route('/my_orders')   #show all bookings for customer. no post/get because this is with a link.
def my_orders():
    if session.get('user_type') != 'customer':
        return redirect('/login')

    email = session.get('user_email')
    status = request.args.get('status')  # מה-select

    orders = get_all_bookings_for_customer(email)

    if status:
        orders = [o for o in orders if o.booking_status == status]

    return render_template('my_orders.html', orders=orders, selected_status=status)

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

