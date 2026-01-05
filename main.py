
from flask import Flask, redirect, render_template, request, session, url_for
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

def get_current_user_dict():
    return {
        'first_name': session.get('user_first_name'),
        'last_name': session.get('user_last_name'),
        'email': session.get('user_email'),
        'passport': session.get('user_passport'),
        'birth_date': session.get('user_birth_date'),
        'phones': session.get('user_phones', [])
    }

@app.route('/profile_details', methods=['GET', 'POST'])
def profile_details():
    user_type = session.get('user_type')
    if user_type != 'customer':
        return redirect('/')

    if request.method=='GET':
        return render_template('customer_profile.html', user=get_current_user_dict())

    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    passport = request.form.get('passport')
    email = session.get('user_email')
    raw_phones = request.form.getlist('phones')

    updated_phones = [p for p in raw_phones if p.strip()]
    update_customer_in_db(email, first_name, last_name, passport)
    update_customer_phones_in_db(email, updated_phones)

    session['user_first_name'] = first_name
    session['user_last_name'] = last_name
    session['user_passport'] = passport
    session['user_phones'] = updated_phones

    return render_template('customer_profile.html',user=get_current_user_dict(), success="Details updated!")


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

    cancel_booking_in_db(booking_id,cancellation_fee)

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
    flight_date = request.form.get('flight_date')
    departure_time = request.form.get("departure_time")
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    aircraft_id = request.form.get('selected_aircraft')
    user_name = session.get('user_first_name')

    size = request.form.get(f'size_{aircraft_id}')
    manufacturer = request.form.get(f'manufacturer_{aircraft_id}')

    pilot_result = get_available_pilots(flight_date, origin, destination, departure_time)
    attendant_result = get_available_attendants(flight_date, origin, destination, departure_time)

    required_pilots = 2 if size == 'Small' else 3
    required_attendants = 3 if size == 'Small' else 6

    if len(pilot_result) >= required_pilots and len(attendant_result) >= required_attendants:
        aircraft_data = {
            'aircraft_id': aircraft_id,
            'size': size,
            'manufacturer': manufacturer
        }

        return render_template(
            'add_flight_3.html',
            aircraft=aircraft_data,
            size=size, # הוספתי את זה כאן כדי שה-HTML יזהה את הגודל למחירים
            pilots=pilot_result,
            attendants=attendant_result,
            flight_date=flight_date,
            departure_time=departure_time,
            origin=origin,
            destination=destination,
            required_pilots=required_pilots,
            required_attendants=required_attendants,
            name=user_name
        )
    else:
        # לוגיקת שגיאה (נשארת אותו דבר)
        error_msg = ""
        if len(pilot_result) < required_pilots:
            error_msg += f"Not enough Pilots ({len(pilot_result)}/{required_pilots} available). "
        if len(attendant_result) < required_attendants:
            error_msg += f"Not enough Attendants ({len(attendant_result)}/{required_attendants} available)."

        return render_template(
            'add_flight_1.html',
            name=user_name,
            origins=get_flights_origins(),
            destinations=get_flights_destinations(),
            today=date.today().isoformat(),
            error=error_msg,
            saved_date=flight_date,
            saved_origin=origin,
            saved_destination=destination,
            saved_time=departure_time
        )

@app.route('/add_flight_step3', methods=['POST'])
def add_flight_step3():
    # 1. שליפת נתוני טיסה מהשדות הנסתרים
    flight_date = request.form.get('flight_date')
    departure_time = request.form.get('departure_time')
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    aircraft_id = request.form.get('aircraft_id')
    size = request.form.get('size')

    # 2. שליפת רשימות הצוות
    selected_pilot_ids = request.form.getlist('selected_pilots')
    selected_attendant_ids = request.form.getlist('selected_attendants')

    # 3. שליפת מחירים מהטופס
    prices = {
        'economy': request.form.get('economy_price'),
        'business': request.form.get('business_price')  # יחזור None אם לא הוצג בטופס
    }

    # 4. ולידציית כמויות צוות
    req_pilots = 2 if size == 'Small' else 3
    req_attendants = 3 if size == 'Small' else 6

    if len(selected_pilot_ids) != req_pilots or len(selected_attendant_ids) != req_attendants:
        from utils import get_available_pilots, get_available_attendants
        pilots = get_available_pilots(flight_date, origin, destination, departure_time)
        attendants = get_available_attendants(flight_date, origin, destination, departure_time)
        return render_template('add_flight_3.html',
                               aircraft={'aircraft_id': aircraft_id, 'size': size},
                               pilots=pilots, attendants=attendants,
                               error=f"Selection error: Please select {req_pilots} pilots and {req_attendants} attendants.",
                               flight_date=flight_date, departure_time=departure_time, origin=origin,
                               destination=destination, size=size)

    # 5. שמירה בבסיס הנתונים (קריאה ל-Utils)
    from utils import create_new_flight_complete, get_crew_names_by_ids
    f_data = {'flight_date': flight_date, 'departure_time': departure_time, 'origin': origin,
              'destination': destination, 'aircraft_id': aircraft_id}

    if create_new_flight_complete(f_data, selected_pilot_ids, selected_attendant_ids, prices):
        # שליפת שמות מלאים של הצוות לתצוגה
        p_info, a_info = get_crew_names_by_ids(selected_pilot_ids, selected_attendant_ids)

        return render_template('add_flight_confirm.html',
                               origin=origin, destination=destination, date=flight_date, time=departure_time,
                               aircraft_id=aircraft_id, size=size,
                               pilot_names=p_info,
                               attendant_names=a_info,
                               economy_price=prices['economy'],
                               business_price=prices['business'])
    else:
        return "Internal Server Error: Could not save flight data.", 500

@app.route('/flight_added_success')
def flight_added_success():
    # דף אישור לאחר הוספת טיסה חדשה [cite: 265, 266]
    pass

@app.route('/flight_board', methods=['GET', 'POST'])    #rona
def flight_board():
    # לוח הטיסות למנהל כולל סינונים [cite: 179, 276, 289]
    pass

@app.route('/flight_board', methods=['GET'])
def show_flight_board():
    user_type = session.get('user_type')

    # אם זה מנהל, הוא יכול לסנן או לראות הכל. אם לא, הוא רואה רק Active
    if user_type == 'manager':
        selected_status = request.args.get('status', 'All')
    else:
        selected_status = 'Active'

    flights = flight_board(selected_status)

    return render_template('flight_board.html',
                           flights=flights,
                           user_type=user_type,
                           current_status=selected_status)



@app.route('/aircraft_management')  #rona
def aircraft_management():
    aircrafts = get_all_aircrafts()
    return render_template("manage_aircrafts.html", aircrafts=aircrafts)

@app.route("/admin_add_aircraft1", methods=["GET", "POST"])
def admin_add_aircraft():
    if request.method == "POST":
        session["new_aircraft"] = {
            "manufacturer": request.form["manufacturer"],
            "size": request.form["size"]
        }
        return redirect(url_for("admin_add_aircraft2"))

    return render_template("add_aircraft1.html")



@app.route("/admin_add_aircraft2", methods=["GET", "POST"])
def admin_add_aircraft2():
    if "new_aircraft" not in session:
        return redirect(url_for("admin_add_aircraft"))

    if request.method == "POST":
        session["new_aircraft"]["classes"] = {
            "economy": {
                "rows": request.form["economy_rows"],
                "cols": request.form["economy_cols"]
            }
        }

        if session["new_aircraft"]["size"] == "Large":
            session["new_aircraft"]["classes"]["business"] = {
                "rows": request.form["business_rows"],
                "cols": request.form["business_cols"]
            }

        return redirect(url_for("added_aircraft"))

    return render_template("add_aircraft2.html")


@app.route("/added_aircraft")
def added_aircraft():
    data = session.get("new_aircraft")
    if not data:
        return redirect(url_for("admin_add_aircraft"))

    aircraft_id = add_aircraft(
        data["manufacturer"],
        data["size"]
    )

    for class_type, c in data["classes"].items():
        add_class(
            aircraft_id,
            class_type,
            c["rows"],
            c["cols"]
        )

    session.pop("new_aircraft")
    return render_template("aircraft_added.html")


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


@app.route('/staff_management')
def staff_management():
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    show = request.args.get('show', 'all')
    if show == 'Pilot':
        staff = get_pilots_only()
    elif show == 'Attendant':
        staff = get_attendants_only()
    else:
        staff = get_all_staff()
    return render_template('staff_table.html', staff_members=staff)


@app.route('/add_staff', methods=['GET', 'POST'])
def add_staff():
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    if request.method == 'GET':
        return render_template('add_staff.html', today=date.today().isoformat())
    if request.method == 'POST':
        id = request.form.get('id')

        if is_id_exists(id):
            return render_template('add_staff.html', error="Error: This ID already exists in the system!")
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        role = request.form.get('new_role')
        phone = request.form.get('phone')
        city = request.form.get('city')
        street = request.form.get('street')
        h_num = request.form.get('house_num')
        s_date = request.form.get('start_date')
        is_certified = 1 if request.form.get('is_certified') else 0
        table = "Pilots" if role == "Pilot" else "Flight_attendants"

        add_crew_to_db(table,id,f_name,l_name,phone,city,street,h_num,s_date,is_certified)
        return redirect('/staff_management')





if __name__=="__main__":
    app.run(debug=True)

