from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session
import datetime
from utils import *

app = Flask(__name__)

# --- Flask App Configuration ---
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
    """
    Sets up the user session variables after successful authentication.
    Stores user details like name, passport, and contact info in the session.
    """
    session['user_email'] = email
    session['user_type'] = 'customer'
    session['user_first_name'] = details['first_name']
    session['user_last_name'] = details['last_name']
    session['user_passport'] = details['passport']
    session['user_birth_date'] = str(details['birth_date'])
    session['user_phones'] = phones


@app.errorhandler(404)
def invalid_route(e):
    """
    Handles 404 errors by redirecting the user to the homepage.
    """
    return redirect("/")


@app.route('/')
def homepage():
    """
    Main entry point. Renders homepages based on user authorization:
    - Manager: Admin dashboard.
    - Customer: Personalized customer view with flight search.
    - Guest: Default landing page with flight search.
    """
    user_type = session.get('user_type')
    origins = get_flights_origins()
    destinations = get_flights_destinations()
    today_str = date.today().isoformat()

    if user_type == 'manager':
        return render_template('admin_homepage.html', name=session.get('user_first_name'))

    elif user_type == 'customer':
        return render_template('customer_homepage.html', name=session.get('user_first_name'), origins=origins,
                               destinations=destinations, today=today_str)

    return render_template('homepage.html', origins=origins, destinations=destinations, today=today_str)

#----Client Interface----
#----User Authentication and Registration Interface----

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login logic.
    - GET: Shows the login form.
    - POST: Validates email/password and redirects to the previous URL or home.
    """
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    # Validate credentials using external utility functions
    if not registered_customer_exists(email) or not check_password_customer(email, password):
        return render_template('login.html', error="Invalid email or password", email=email)

    else:
        details = get_customer_details(email)
        phones = get_customer_phones(email)
        if details:
            login_user(email, details, phones)
            # Redirect to originally requested page or default to home
            return redirect(session.pop('next_url', '/'))

    return render_template('login.html', error="An error occurred while logging in.")


@app.route('/logout')
def logout():
    """
    Clears all session data and redirects to the public homepage.
    """
    session.clear()
    return redirect('/')


def get_current_user_dict():
    """
    Utility function to retrieve current session data formatted as a dictionary.
    Used for passing user information to templates.
    """
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
    """
    Handles user profile viewing and updates.
    - Only accessible to 'customer' user types.
    - Updates both the database and the active session upon changes.
    """
    user_type = session.get('user_type')
    if user_type != 'customer':
        return redirect('/')

    if request.method == 'GET':
        return render_template('customer_profile.html', user=get_current_user_dict())

    # Handle profile updates (POST)
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    passport = request.form.get('passport')
    email = session.get('user_email')
    raw_phones = request.form.getlist('phones')

    # Filter out empty phone fields
    updated_phones = [p for p in raw_phones if p.strip()]

    # Update Database
    update_customer_in_db(email, first_name, last_name, passport)
    update_customer_phones_in_db(email, updated_phones)

    # Sync Session with new data
    session['user_first_name'] = first_name
    session['user_last_name'] = last_name
    session['user_passport'] = passport
    session['user_phones'] = updated_phones

    return render_template('customer_profile.html', user=get_current_user_dict(), success="Details updated!")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Handles user registration.
    - GET: Renders the signup form with 'today' as the maximum birth date allowed.
    - POST: Checks if email exists. If guest, upgrades to registered; otherwise, adds as new.
    """
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
        # Convert an existing guest customer to a registered member
        turn_into_registered_db(email,first_name,last_name,passport_number,birth_date,date.today(),password,phones)

    else:
        # Create a completely new registered customer record
        add_customer_to_db(email,first_name,last_name,passport_number,birth_date,date.today(),password, phones)

    details = {
        'first_name': first_name,
        'last_name': last_name,
        'passport': passport_number,
        'birth_date': birth_date
    }
    login_user(email, details, phones)

    return redirect('/')


#----Flight Search and Ticket Selection Interface----
@app.route('/search_flights', methods=['GET','POST'])
def search_flights():
    """
    Processes the flight search form.
    Retrieves relevant flights based on date, origin, destination, and seat availability.
    If no flights are found, redirects back to homepage with an error message.
    """
    if request.method == 'GET':
        return redirect('/')
    flight_date= request.form.get('flight_date')
    origin = request.form.get('origin')
    destination=request.form.get('destination')
    num_seats = int(request.form.get('num_seats'))

    result = get_relevant_flights(flight_date,origin, destination, num_seats)
    if not result:
        return render_template('homepage.html', origins=get_flights_origins(),
                               destinations=get_flights_destinations(),today=date.today().isoformat(), error='No available flights found for the selected criteria')
    return render_template('show_flights.html', flights=result, requested_seats=num_seats)


@app.route('/select_seats', methods=['GET','POST'])
def select_seats():
    """
    Handles seat selection initialization.
    Parses selected flight/class data, stores booking details in session,
    and prepares the seat map by fetching layout and vacant seat information.
    """
    if request.method == 'GET':
        return redirect('/')
    selected_data = request.form.get('selected_option')
    num_seats = int(request.form.get('num_seats'))

    flight_id, class_type, aircraft_id = selected_data.split(',')
    price_per_seat = get_price_for_class(flight_id, class_type)

    # Store essential booking data in session for later stages
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
    # Create a set of vacant seats for O(1) lookup in the template
    vacant_set = {(s[1], s[2]) for s in vacant_seats if s[0] == class_type}
    return render_template('seat_selection.html',flight_id=flight_id, class_type=class_type, layout=class_info,vacant_set=vacant_set, num_seats=num_seats)


@app.route('/validate_seats', methods=['GET','POST'])
def validate_seats():
    """
    Validates that the user selected the exact number of seats requested.
    If valid: Stores seat selection in session and moves to passenger details.
    If invalid: Reloads the seat selection page with an error message.
    """
    if request.method == 'GET':
        return redirect('/')
    selected_seats = request.form.getlist("selected_seats")
    booking = session.get('booking_data')

    # Verification: Ensure selected count matches requested count
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
        # Success: Update session with selected seats and proceed
        booking['selected_seats'] = selected_seats
        session['booking_data'] = booking
        return render_template("passenger_details.html", seats=selected_seats, today=date.today().isoformat())

@app.route('/review_order', methods=['GET','POST'])
def review_order():
    """
    Final validation before showing the order summary.
    - Checks if the booking session exists.
    - Validates if a guest is trying to use an email that belongs to a registered customer.
    - Updates the booking session with passenger information from the form.
    """
    if request.method == 'GET':
        return redirect('/')
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')

    # Security/Logic Check: Prevent guests from using registered emails
    email = request.form.get('email')
    if registered_customer_exists(email) and session.get('user_email') != email:
        # Save where the user was so they can return after logging in
        session['next_url'] = '/passenger_details_after_login'
        return render_template('passenger_details.html',
                               seats=booking.get('selected_seats'),
                               error=f"the email {email} is already registered.")

    # Clean and collect phone numbers
    raw_phones = request.form.getlist('phones')
    phones = [p for p in raw_phones if p.strip()]

    # Update session object with validated data
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
    """
    Allows the user to go back from the Summary page to the
    Passenger Details page to correct information.
    """
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')
    return render_template("passenger_details.html",
                           seats=booking.get('selected_seats'),
                           today=date.today().isoformat())


@app.route('/passenger_details_after_login')
def passenger_details_after_login():
    """
    Redirects the user back to the passenger details form after a
    successful login during the booking process.
    """
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')

    return render_template("passenger_details.html",
                           seats=booking.get('selected_seats'),
                           today=date.today().isoformat())


@app.route('/confirm_booking', methods=['GET','POST'])
def confirm_booking():
    """
    Finalizes the booking process.
    - Extracts all booking data from the session.
    - Saves the booking, passengers, and seats to the database via 'add_booking_to_db'.
    - Clears the temporary booking data from the session.
    - Renders the success page with the new Order ID.
    """
    if request.method == 'GET':
        return redirect('/')
    booking = session.get('booking_data')
    if not booking:
        return redirect('/')

    # Extracting all details stored during the multi-step process
    email = booking['email']
    first_name = booking['first_name']
    last_name = booking['last_name']
    flight_id = booking['flight_id']
    booking_date = date.today()
    booking_status = 'Active'
    payment = booking['total_price']
    aircraft_id = booking['aircraft_id']
    class_type = booking['class_type']
    seats = booking['selected_seats']
    phones = booking['phones']

    # Execute the database insertion and get the generated Order ID
    order_id = add_booking_to_db(email, first_name, last_name, flight_id, booking_date,
                                 booking_status, payment, aircraft_id, class_type, seats, phones)

    vacant_seats = get_vacant_seats(flight_id)
    if not vacant_seats:
        update_flight_status_in_db(flight_id, 'Fully Booked')

    # Clean up: Remove booking data from session after successful save
    session.pop('booking_data', None)

    return render_template('booking_success.html',
                           order_id=order_id,
                           first_name=first_name,
                           last_name=last_name,
                           flight_id=flight_id,
                           selected_seats=seats)


#----Booking Management Interface----

@app.route('/manage_booking', methods=['GET', 'POST'])
def manage_booking():
    """
    Handles requests to view and manage a specific booking.
    - If accessed via GET: Redirects to homepage.
    - If accessed via POST: Validates booking ID against the user's email.
    - Checks booking status and time constraints for potential cancellation.
    """
    if request.method == 'GET':
        return redirect('/')

    # Retrieve input data
    booking_id = int(request.form.get('booking_ID'))

    # Determine email source: session for logged-in users, form for guests
    if session.get('user_type') == 'customer':
        email = session.get('user_email')
    else:
        email = request.form.get('booking_email')

    # Fetch booking data from database
    booking = get_booking_details(booking_id, email)

    # Error handling: Booking not found
    if not booking:
        origins = get_flights_origins()
        destinations = get_flights_destinations()
        today_str = datetime.now().date().isoformat()
        error_text = "Booking doesn't exist. Please check details."

        if session.get('user_type') == 'customer':
            return render_template('customer_homepage.html', name=session.get('user_first_name'),
                                   origins=origins, destinations=destinations, today=today_str,
                                   manage_booking_error=error_text)

        return render_template('homepage.html', origins=origins, destinations=destinations,
                               today=today_str, manage_booking_error=error_text)

    # Validation: Only active bookings can be managed
    if booking.booking_status != 'Active':
        origins = get_flights_origins()
        destinations = get_flights_destinations()
        today_str = datetime.now().date().isoformat()
        error_msg = "This booking is no longer active and cannot be managed."

        if session.get('user_type') == 'customer':
            return render_template('customer_homepage.html', name=session.get('user_first_name'),
                                   origins=origins, destinations=destinations, today=today_str,
                                   manage_booking_error=error_msg)

        return render_template('homepage.html', origins=origins, destinations=destinations,
                               today=today_str, manage_booking_error=error_msg)

    # Calculations for the management view
    departure_date = booking.departure_date
    departure_time = booking.departure_time
    payment = booking.payment

    # Check if cancellation is allowed based on time policy
    can_cancel = can_cancel_booking(departure_date, departure_time)
    cancellation_fee = calculate_cancellation_fee(payment)

    return render_template('manage_booking.html',
                           booking=booking,
                           can_cancel=can_cancel,
                           cancellation_fee=cancellation_fee,
                           back_url=request.referrer)

@app.route('/cancel_booking_request', methods=['GET', 'POST'])
def cancel_booking_request():
    """
    Processes the flight cancellation request.
    - Validates the booking ownership (email/ID).
    - Calculates the final cancellation fee.
    - Updates the booking status in the database to 'Cancelled'.
    - Renders a confirmation page for the user.
    """
    if request.method == 'GET':
        return redirect('/')

    # Retrieve booking details for processing
    booking_id = int(request.form.get('booking_id'))

    # Determine user identity to ensure security
    if session.get('user_type') == 'customer':
        email = session.get('user_email')
    else:
        email = request.form.get('booking_email')

    # Fetch booking data and calculate the 5% penalty fee
    booking = get_booking_details(booking_id, email)
    if not booking:
        return redirect('/')
    flight_id = booking.flight_id

    payment = booking.payment
    cancellation_fee = calculate_cancellation_fee(payment)

    # Perform the update in the database
    cancel_booking_in_db(booking_id, cancellation_fee)
    update_flight_status_in_db(flight_id, 'Active')

    return render_template(
        'booking_cancelled.html',
        booking_id=booking_id,
        cancellation_fee=cancellation_fee
    )


@app.route('/my_orders')
def my_orders():
    """
    Displays the booking history for a logged-in customer.
    - Restricts access to registered customers only.
    - Retrieves all bookings associated with the customer's email.
    - Supports optional filtering by booking status (Active, Cancelled, etc.).
    """
    # Security check: Ensure only logged-in customers can access this page
    if session.get('user_type') != 'customer':
        return redirect('/')

    email = session.get('user_email')

    # Get the status filter from the URL parameters (e.g., /my_orders?status=Active)
    status = request.args.get('status')

    # Fetch all records from the database
    orders = get_all_bookings_for_customer(email)

    # Apply filtering logic if a specific status was selected in the UI
    if status:
        orders = [o for o in orders if o.booking_status == status]

    return render_template('my_orders.html', orders=orders, selected_status=status)

#----Admin Interface----

@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    """
    Handles the administrative login process.
    - GET: Displays the admin login form.
    - POST: Validates the Admin ID and password.
    - Sets the session to 'manager' type upon successful authentication.
    - Redirects to the admin dashboard.
    """
    if request.method == 'GET':
        return render_template('adminlogin.html')

    id = request.form.get('ID')
    password = request.form.get('password')

    # Security check 1: Verify if the ID exists in the managers table
    if not admin_exists(id):
        return render_template('adminlogin.html', error="This ID does not belong to an admin")

    # Security check 2: Verify the password against the stored record
    if not check_password_manager(id, password):
        return render_template('adminlogin.html', error="Incorrect Password")

    # Retrieve admin details to personalize the session
    first_name, last_name = get_admin_details(id)
    if first_name is None:
        return render_template('adminlogin.html', error="Admin details not found")

    else:
        # Successful login: Set session variables to grant manager access
        session['user_type'] = 'manager'
        session['user_id'] = id
        session['user_first_name'] = first_name
        session['user_last_name'] = last_name
        return redirect('/admin_homepage')


@app.route('/admin_homepage')
def admin_dashboard():
    """
    Renders the central control panel for administrators.
    - Security: Verification that the current session belongs to a 'manager'.
    - Functionality: Supports an optional 'show_cancel' toggle via URL parameters
      to display cancellation-related notifications or data.
    - Access Control: Redirects unauthorized users back to the admin login page.
    """
    user_type = session.get('user_type')

    # Access Control: Only allow users with 'manager' privileges
    if user_type == 'manager':
        # Retrieve optional toggle from URL (e.g., /admin_homepage?show_cancel=true)
        show_cancel = request.args.get('show_cancel') == 'true'

        return render_template('admin_homepage.html',
                               name=session.get('user_first_name'),
                               show_cancel=show_cancel)

    else:
        # Unauthorized access attempt
        return redirect("/")

@app.route('/add_flight_step1', methods=['POST', 'GET'])
def add_flight_step1():
    """
    Handles the first step of the flight creation process.
    - Collects origin, destination, date, and time.
    - Validates inputs and searches for available aircraft.
    - On success: Passes all flight details to step 2.
    - On failure: Returns to step 1 with an error message.
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')

    # Base data for the form to prevent code duplication
    common_data = {
        'origins': get_flights_origins(),
        'destinations': get_flights_destinations(),
        'today': date.today().isoformat(),
        'name': session.get('user_first_name')
    }

    if request.method == 'GET':
        return render_template('add_flight_1.html', **common_data)

    # Retrieve data from the form
    flight_date = request.form.get('flight_date')
    departure_time = request.form.get("departure_time")
    origin = request.form.get('origin')
    destination = request.form.get('destination')

    # Basic validation before heavy processing
    if not all([flight_date, departure_time, origin, destination]):
        return render_template('add_flight_1.html', **common_data, error='All fields are required.')

    # Call the utility function to find available aircraft
    aircraft_result = get_available_aircraft(flight_date, origin, destination, departure_time)

    if not aircraft_result:
        return render_template(
            'add_flight_1.html',
            **common_data,
            error='No available Aircraft for this route/time. Please select differently.'
        )

    # Proceed to step 2 with all necessary data
    return render_template(
        'add_flight_2.html',
        aircraft=aircraft_result,
        flight_date=flight_date,
        departure_time=departure_time,
        origin=origin,
        destination=destination,
        name=common_data['name']
    )

@app.route('/add_flight_step2', methods=['GET','POST'])
def add_flight_step2():
    """
    Controller for the second stage of flight creation: Staff Allocation.
    - Receives the selected aircraft and original flight details.
    - Determines crew requirements based on aircraft size (Small vs. Large).
    - Fetches available pilots and flight attendants from the database.
    - Validates if the minimum required staff is available to proceed.
    """
    if request.method == 'GET':
        return redirect('/')
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    flight_date = request.form.get('flight_date')
    departure_time = request.form.get("departure_time")
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    aircraft_id = request.form.get('selected_aircraft')
    user_name = session.get('user_first_name')

    # Retrieve aircraft metadata passed from the previous form
    size = request.form.get(f'size_{aircraft_id}')
    manufacturer = request.form.get(f'manufacturer_{aircraft_id}')

    # Business Logic: Fetch eligible staff members for this specific time and route
    pilot_result = get_available_pilots(flight_date, origin, destination, departure_time)
    attendant_result = get_available_attendants(flight_date, origin, destination, departure_time)

    # Crewing Rules: Define staffing requirements based on aircraft capacity
    required_pilots = 2 if size == 'Small' else 3
    required_attendants = 3 if size == 'Small' else 6

    # Validation: Ensure the available pool meets the minimum requirements
    if len(pilot_result) >= required_pilots and len(attendant_result) >= required_attendants:
        aircraft_data = {
            'aircraft_id': aircraft_id,
            'size': size,
            'manufacturer': manufacturer
        }

        return render_template(
            'add_flight_3.html',
            aircraft=aircraft_data,
            size=size,
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
        # Error Handling: If staff is insufficient, return to step 1 with a detailed message
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


@app.route('/add_flight_step3', methods=['GET','POST'])
def add_flight_step3():
    """
    Final stage of flight creation: Data verification and Database insertion.
    Fixes UndefinedError by passing required counts back to the template upon error.
    """
    if request.method == 'GET':
        return redirect('/')
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    # 1. Retrieve flight data from hidden fields
    flight_date = request.form.get('flight_date')
    departure_time = request.form.get('departure_time')
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    aircraft_id = request.form.get('aircraft_id')
    size = request.form.get('size')
    user_name = session.get('user_first_name')

    # 2. Retrieve selected crew lists (lists of IDs)
    selected_pilot_ids = request.form.getlist('selected_pilots')
    selected_attendant_ids = request.form.getlist('selected_attendants')

    # 3. Retrieve pricing information
    prices = {
        'economy': request.form.get('economy_price'),
        'business': request.form.get('business_price')
    }

    # 4. Final Crew Quantity Validation
    req_pilots = 2 if size == 'Small' else 3
    req_attendants = 3 if size == 'Small' else 6

    num_selected_pilots = len(selected_pilot_ids)
    num_selected_attendants = len(selected_attendant_ids)

    if num_selected_pilots != req_pilots or num_selected_attendants != req_attendants:
        err_list = []
        if num_selected_pilots != req_pilots:
            err_list.append(f"Pilots: {num_selected_pilots}/{req_pilots}")
        if num_selected_attendants != req_attendants:
            err_list.append(f"Attendants: {num_selected_attendants}/{req_attendants}")

        full_error_msg = "Wrong selection: " + " & ".join(err_list)

        from utils import get_available_pilots, get_available_attendants
        pilots = get_available_pilots(flight_date, origin, destination, departure_time)
        attendants = get_available_attendants(flight_date, origin, destination, departure_time)

        return render_template('add_flight_3.html',
                               aircraft={'aircraft_id': aircraft_id, 'size': size,
                                         'manufacturer': request.form.get('manufacturer')},
                               pilots=pilots,
                               attendants=attendants,
                               error=full_error_msg,
                               flight_date=flight_date,
                               departure_time=departure_time,
                               origin=origin,
                               destination=destination,
                               size=size,
                               required_pilots=req_pilots,
                               required_attendants=req_attendants,
                               name=user_name
                               )

    # 5. Database persistence
    from utils import create_new_flight_complete, get_crew_names_by_ids
    f_data = {
        'flight_date': flight_date,
        'departure_time': departure_time,
        'origin': origin,
        'destination': destination,
        'aircraft_id': aircraft_id,
        'size': size
    }

    if create_new_flight_complete(f_data, selected_pilot_ids, selected_attendant_ids, prices):
        p_info, a_info = get_crew_names_by_ids(selected_pilot_ids, selected_attendant_ids)

        return render_template('add_flight_confirm.html',
                               origin=origin, destination=destination, date=flight_date, time=departure_time,
                               aircraft_id=aircraft_id, size=size,
                               pilot_names=p_info,
                               attendant_names=a_info,
                               economy_price=prices['economy'],
                               business_price=prices['business'],
                               name=user_name)
    else:
        return "Internal Server Error: Could not save flight data.", 500



@app.route('/flight_board', methods=['GET'])
def show_flight_board():
    """
    Displays the flight board based on user permissions.
    - Managers can view all flights or filter by status.
    - Other users can only see 'Active' flights.
    - Automatically updates flights to 'Completed' if they have already landed.
    """
    update_completed_flights()
    user_type = session.get('user_type')

    # Determine status filter based on user role
    if user_type == 'manager':
        selected_status = request.args.get('status', 'All')
    else:
        selected_status = 'Active'

    # Get flight data and render board
    flights = flight_board(selected_status)

    return render_template('flight_board.html',
                           flights=flights,
                           user_type=user_type,
                           current_status=selected_status)



@app.route('/aircraft_management')
def aircraft_management():
    """
    Route for the aircraft management dashboard.
    Fetches all aircraft data and displays it to the administrator.
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    aircrafts = get_all_aircrafts()
    return render_template("manage_aircrafts.html", aircrafts=aircrafts)


@app.route("/admin_add_aircraft1", methods=["GET", "POST"])
def admin_add_aircraft():
    """
    Step 1 of the Add Aircraft process.
    - GET: Displays the initial form to select manufacturer and aircraft size.
    - POST: Saves the selection into the session and redirects to Step 2
            for seat configuration (Class definitions).
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    if request.method == "POST":
        # Store basic aircraft details in session to pass to the next stage
        session["new_aircraft"] = {
            "manufacturer": request.form["manufacturer"],
            "size": request.form["size"]
        }
        return redirect(url_for("admin_add_aircraft2"))

    return render_template("add_aircraft1.html")

@app.route("/admin_add_aircraft2", methods=["GET", "POST"])
def admin_add_aircraft2():
    """
    Step 2 of the Add Aircraft process: Seat Configuration.
    - Validates that the aircraft session exists.
    - Collects row and column counts for seat classes.
    - Dynamically requires Business Class details only for 'Large' aircraft.
    - Redirects to the final persistence stage.
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    # Safety check: Ensure the user completed Step 1
    if "new_aircraft" not in session:
        return redirect(url_for("admin_add_aircraft"))

    if request.method == "POST":
        # Initialize the classes dictionary with Economy (mandatory for all)
        session["new_aircraft"]["classes"] = {
            "economy": {
                "rows": request.form["economy_rows"],
                "cols": request.form["economy_cols"]
            }
        }

        # Add Business class configuration only if aircraft size is Large
        if session["new_aircraft"]["size"] == "Large":
            session["new_aircraft"]["classes"]["business"] = {
                "rows": request.form["business_rows"],
                "cols": request.form["business_cols"]
            }

        return redirect(url_for("added_aircraft"))

    # Pass the aircraft size to the template to render the appropriate input fields
    return render_template("add_aircraft2.html",
        aircraft_size=session["new_aircraft"]["size"])


@app.route("/added_aircraft")
def added_aircraft():
    """
    Final stage of aircraft creation: Persistence and Cleanup.
    - Validates aircraft data from the session.
    - Inserts the aircraft and its seat classes into the database.
    - Generates individual seat records with continuous row numbering across classes.
    - Clears the session to finalize the process.
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')

    data = session.get("new_aircraft")
    if not data:
        # Redirect to the start if session data is missing
        return redirect(url_for("admin_add_aircraft"))

    # Step 1: Insert the aircraft record and retrieve its unique ID
    aircraft_id = add_aircraft(data["manufacturer"], data["size"])

    # Variable to track the starting row number for the current class
    # Ensures numbering continues (e.g., Business 1-5, Economy starts at 6)
    current_start_row = 1

    # Step 2: Iterate through defined classes.
    # Sorting ensures 'business' is processed before 'economy' for correct row order.
    sorted_classes = sorted(data["classes"].items())

    for class_type, c in sorted_classes:
        # Save class configuration (e.g., Economy, 20 rows, 6 columns)
        add_class(aircraft_id, class_type, c["rows"], c["cols"])

        # Generate individual seat records for this class in the 'seat' table
        add_seats_for_class(
            aircraft_id,
            class_type,
            int(c["rows"]),
            int(c["cols"]),
            current_start_row
        )

        # Increment the row counter for the next class
        current_start_row += int(c["rows"])

    # Step 3: Clear session data and show success page
    session.pop("new_aircraft")
    return render_template("aircraft_added.html")


@app.route('/admin_cancel_flight', methods=['GET','POST'])
def admin_cancel_flight():
    """
    Controller for the flight cancellation confirmation page.
    - Retrieves flight ID from the form.
    - Fetches full flight details for display.
    - Checks if the flight can be cancelled based on the 72-hour rule AND status.
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    if request.method == 'GET':
        return redirect('/')
    flight_id = request.form.get('flight_number')

    # Check flight existence and status eligibility before proceeding to the cancellation page
    is_eligible, error_msg = check_flight_cancellation_eligibility(flight_id)
    if not is_eligible:
        return render_template('admin_homepage.html',
                               error=error_msg,
                               name=session.get('user_first_name'))

    # Unpack flight details for the template
    flight_id, flight_status, departure_time, departure_date, \
        origin_airport, destination_airport, aircraft_id = get_flight_details(flight_id)

    # Check cancellation eligibility (True/False based on time remaining AND status)
    cancel_time = can_cant_cancel_flight(flight_id)

    return render_template('cancel_flight.html',
                           flight_id=flight_id,
                           flight_status=flight_status,
                           departure_time=departure_time,
                           departure_date=departure_date,
                           origin_airport=origin_airport,
                           destination_airport=destination_airport,
                           aircraft_id=aircraft_id,
                           cancel_time=cancel_time)


@app.route('/admin_cancel_flight/confirm', methods=['GET','POST'])
def admin_cancel_flight_confirm():
    """
    Final execution of flight cancellation.
    - Retrieves the flight ID to be cancelled.
    - Updates the flight status to 'Cancelled' in the database.
    - Handles the cancellation of all associated bookings for this flight.
    - Renders the confirmation success page.
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')
    if request.method == 'GET':
        return redirect('/')
    flight_id = request.form.get('flight_number')

    # Update flight status in the 'flight' table
    cancel_flight(flight_id)

    # Handle related records (e.g., notifying passengers or marking bookings as cancelled)
    cancel_booking(flight_id)

    #Removes all pilots and flight attendants assigned This flight and frees them up to be scheduled for other flights.
    unassign_crew(flight_id)

    return render_template('cancel_flight_confirm.html', flight_id=flight_id)

@app.route('/staff_management')
def staff_management():
    """
    Route to manage and display airline staff members.
    - Restricts access to managers only.
    - Filters list based on the 'show' query parameter (Pilot, Attendant, or All).
    """
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
    """
    Route to add a new staff member (Pilot or Flight Attendant).
    - GET: Displays the staff registration form.
    - POST: Validates that the ID is unique, determines the target table based on the selected role,
            and saves the new record.
    """
    user_type = session.get('user_type')
    if user_type != 'manager':
        return redirect('/')

    if request.method == 'GET':
        return render_template('add_staff.html', today=date.today().isoformat())

    if request.method == 'POST':
        id = request.form.get('id')

        # Check for ID conflicts across both staff tables
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

        # Handle checkbox boolean logic (1 for certified, 0 otherwise)
        is_certified = 1 if request.form.get('is_certified') else 0

        # Dynamically select target table based on the selected role
        table = "Pilots" if role == "Pilot" else "Flight_attendants"

        add_crew_to_db(table, id, f_name, l_name, phone, city, street, h_num, s_date, is_certified)
        return render_template('staff_added.html')



if __name__=="__main__":
    app.run(debug=True)

