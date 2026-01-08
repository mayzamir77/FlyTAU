import mysql.connector
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime, date, time, timedelta
import string


print("utils loaded")

@contextmanager
def db_cur():
    mydb = None
    cursor = None
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="FLYTAU",
            autocommit=True
        )
        cursor = mydb.cursor()
        yield cursor

    except mysql.connector.Error as err:
        raise err

    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()


#----homepage functions----
def get_flights_origins():
    """
    Retrieves all unique flight origin airports from the routes table.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT DISTINCT origin_airport FROM routes")
        result = cursor.fetchall()
        return result

def get_flights_destinations():
    """
    Retrieves all unique flight destination airports from the routes table.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT DISTINCT destination_airport FROM routes")
        result = cursor.fetchall()
        return result

#----login functions----
def guest_customer_exists(email):
    """
    Checks if an email exists in the guest_customer table.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM guest_customer WHERE email = %s", (email,))
        result = cursor.fetchone()
        return result is not None

def registered_customer_exists(email):
    """
    Checks if an email is already registered in the Registered_Customer table.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Registered_Customer WHERE email = %s", (email,))
        result = cursor.fetchone()
        return result is not None

def check_password_customer(email, password):
    """
    Validates if the provided email and password match a record in Registered_Customer.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Registered_Customer WHERE email = %s and customer_password= %s", (email,password))
        result = cursor.fetchone()
        return result is not None

def get_customer_details(email):
    """
    Fetches personal details for a registered customer by email and returns them as a dictionary.
    """
    with db_cur() as cursor:
        cursor.execute("""
            SELECT first_name_english, last_name_english, passport_number, birth_date 
            FROM registered_customer WHERE email = %s
        """, (email,))
        res = cursor.fetchone()
        if res:
            return {
                'first_name': res[0],
                'last_name': res[1],
                'passport': res[2],
                'birth_date': res[3]
            }
        return None

def get_customer_phones(email):
    """
    Retrieves all phone numbers associated with a specific customer email.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT phone_number FROM registered_customer_phones WHERE email = %s", (email,))
        result = [row[0] for row in cursor.fetchall()]
        return result

#----profile_details functions----
def update_customer_in_db(email, first_name, last_name, passport):
    """
    Updates the name and passport number for an existing registered customer.
    """
    with db_cur() as cursor:
        query = """
            UPDATE registered_customer 
            SET first_name_english = %s, last_name_english = %s, passport_number = %s 
            WHERE email = %s
        """
        cursor.execute(query, (first_name, last_name, passport, email))


def update_customer_phones_in_db(email, phones):
    """
    Updates customer phone numbers by deleting existing ones and inserting the new list.
    """
    with db_cur() as cursor:
        cursor.execute("DELETE FROM registered_customer_phones WHERE email = %s", (email,))

        for phone in phones:
            cursor.execute("INSERT INTO registered_customer_phones (email, phone_number) VALUES (%s, %s)",
                           (email, phone))

#----signup functions----

def turn_into_registered_db(email, first_name, last_name, passport_number, birth_date, registration_date, password, new_phones):
    """
    Moves a customer from the guest tables to the registered tables,
    merging their previous guest phone numbers with the new ones provided.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT phone_number FROM guest_customer_phones WHERE email = %s", (email,))
        old_phones = [row[0] for row in cursor.fetchall()]
        all_phones = list(set(old_phones + new_phones))
        cursor.execute("DELETE FROM guest_customer_phones WHERE email = %s", (email,))
        cursor.execute("DELETE FROM guest_customer WHERE email = %s", (email,))
        cursor.execute("""
            INSERT INTO registered_customer 
            (email, first_name_english, last_name_english, passport_number, birth_date, registration_date, customer_password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (email, first_name, last_name, passport_number, birth_date, registration_date, password))
        for p in all_phones:
            cursor.execute("INSERT INTO registered_customer_phones (email, phone_number) VALUES(%s, %s)", (email, p))

def add_customer_to_db(email,first_name,last_name,passport_number,birth_date,registration_date,password, phones):
    """
    Inserts a new registered customer and their phone numbers directly into the database.
    """
    with db_cur() as cursor:
        cursor.execute("INSERT INTO Registered_Customer VALUES (%s,%s,%s,%s,%s,%s,%s)",
                       (email, first_name, last_name, passport_number, birth_date, registration_date, password))
        for p in phones:
            cursor.execute("INSERT INTO registered_customer_phones VALUES(%s,%s)",(email,p))


# ----search_flights functions----

class FlightResult:
    """
    A wrapper class used to organize flight data retrieved from the database.
    It maps a raw data tuple into a readable object with attributes like ID, time, and price.
    Used primarily during the flight search process.
    """
    def __init__(self, data_tuple):
        self.id = data_tuple[0]
        self.departure_time = data_tuple[1]
        self.departure_date = data_tuple[2]
        self.aircraft_id = data_tuple[3]
        self.duration = data_tuple[4]
        self.class_type = data_tuple[5]
        self.price = data_tuple[6]
        self.arrival_date = data_tuple[7]
        self.arrival_time = data_tuple[8]
        self.origin=data_tuple[9]
        self.destination=data_tuple[10]

def get_relevant_flights(date, origin, destination, requested_seats):
    """
    Query the database for active flights matching the criteria.
    Calculates arrival time using flight duration and filters results
    by checking if the requested number of seats is available in each class.
    """
    with db_cur() as cursor:
        query = '''
            SELECT f.flight_id, f.departure_time, f.departure_date, f.aircraft_id,
                   r.flight_duration_mins, cif.class_type, cif.seat_price,
                   DATE(ADDTIME(TIMESTAMP(f.departure_date, f.departure_time), SEC_TO_TIME(r.flight_duration_mins * 60))) AS arrival_date,
                   TIME(ADDTIME(TIMESTAMP(f.departure_date, f.departure_time), SEC_TO_TIME(r.flight_duration_mins * 60))) AS arrival_time,
                   f.origin_airport, f.destination_airport
            FROM flight f
            JOIN routes r ON f.origin_airport = r.origin_airport AND f.destination_airport = r.destination_airport
            JOIN classes_in_flight cif ON f.flight_id = cif.flight_id
            WHERE f.departure_date = %s 
              AND f.origin_airport = %s 
              AND f.destination_airport = %s 
              AND f.flight_status = 'Active'
        '''
        cursor.execute(query, (date, origin, destination))
        all_options = cursor.fetchall()

        final_results = []
        for opt in all_options:
            flight_id = opt[0]
            class_type = opt[5]

            # Verify real-time seat availability for the specific class
            vacant_seats = get_vacant_seats(flight_id)
            class_vacant = [s for s in vacant_seats if s[0] == class_type]

            if len(class_vacant) >= int(requested_seats):
                final_results.append(opt)

        final_objects = []
        for opt in final_results:
            final_objects.append(FlightResult(opt))

        return final_objects

# ----select_seats functions----

def get_price_for_class(flight_id, class_type):
    """
    Fetches the price for a specific class within a specific flight.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT seat_price from classes_in_flight WHERE flight_id =%s and class_type=%s",(flight_id,class_type))
        result = cursor.fetchone()
        if result:
            return result[0]
        return 0

def get_vacant_seats(flight_id):
    """
    Retrieves all seats for the aircraft assigned to a flight that are NOT
    currently occupied by an 'Active' booking.
    """
    with db_cur() as cursor:
        query = '''
            SELECT s.class_type, s.row_num, s.column_letter
            FROM seat s
            JOIN flight f ON s.aircraft_id = f.aircraft_id
            WHERE f.flight_id = %s
            AND (s.row_num, s.column_letter, s.class_type) NOT IN (
                SELECT ss.row_num, ss.column_letter, ss.class_type
                FROM selected_seats_in_booking ss
                JOIN booking b ON ss.booking_id = b.booking_id
                WHERE b.flight_id = %s AND b.booking_status = 'Active'
            )
        '''
        cursor.execute(query, (flight_id, flight_id))
        return cursor.fetchall()

def get_class_layout(flight_id, class_type):
    """
    Retrieves dimensions (rows/columns) and the starting row number
    for a specific class on the aircraft assigned to the flight.
    """
    with db_cur() as cursor:
        query = """
            SELECT c.num_rows, c.num_columns, (SELECT min(row_num) 
            FROM seat s join flight f2 on f2.aircraft_id=s.aircraft_id
            WHERE f2.flight_id=%s and s.class_type= %s)
            FROM class c
            JOIN flight f ON c.aircraft_id = f.aircraft_id
            WHERE f.flight_id = %s AND c.class_type = %s
        """
        cursor.execute(query, (flight_id, class_type, flight_id, class_type))
        return cursor.fetchone()


# ----confirm_booking functions----

def add_booking_to_db(email, first_name, last_name, flight_id, booking_date, booking_status, payment, aircraft_id,
                      class_type, seats, phones):
    """
    Finalizes the booking in the database.
    1. If the customer is a guest, it ensures their details exist in guest tables.
    2. Creates a new record in the 'booking' table.
    3. Links the selected seats to the newly created booking ID.
    """
    with db_cur() as cursor:
        # Check if the user is not registered; if so, manage them as a guest
        if not registered_customer_exists(email):
            cursor.execute("""
                        INSERT INTO guest_customer (email, first_name_english, last_name_english) 
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            first_name_english = VALUES(first_name_english),
                            last_name_english = VALUES(last_name_english)
                    """, (email, first_name, last_name))
            for p in phones:
                cursor.execute("INSERT IGNORE INTO guest_customer_phones VALUES (%s, %s)", (email, p))

        # Insert the main booking record
        cursor.execute(
            "INSERT INTO booking (customer_email, flight_id, booking_date, booking_status, payment) VALUES (%s,%s,%s,%s,%s)",
            (email, flight_id, booking_date, booking_status, payment))

        # Retrieve the auto-generated ID for this booking
        new_booking_id = cursor.lastrowid

        # Process and link each selected seat
        for seat in seats:
            # Extract row number (digits) and column letter (alpha) from string (e.g., '12A' -> '12', 'A')
            row = ''.join(filter(str.isdigit, seat))
            col = ''.join(filter(str.isalpha, seat))
            cursor.execute("""
                            INSERT INTO selected_seats_in_booking (booking_id, aircraft_id, class_type, row_num, column_letter)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (new_booking_id, aircraft_id, class_type, row, col))

        return new_booking_id


# ----manage_booking functions----

def get_booking_details(booking_id, email):
    """
    Retrieves complete booking information, including flight and route details.
    Calculates arrival time using flight duration and ensures the booking belongs to the provided email.
    """
    with db_cur() as cursor:
        query = """
        SELECT b.booking_id, b.customer_email, b.payment, b.booking_status,
            f.flight_id, f.departure_date, f.departure_time, 
            r.origin_airport, r.destination_airport, r.flight_duration_mins,
            DATE(ADDTIME(TIMESTAMP(f.departure_date, f.departure_time),SEC_TO_TIME(r.flight_duration_mins * 60))) AS arrival_date,
            TIME(ADDTIME(TIMESTAMP(f.departure_date, f.departure_time),SEC_TO_TIME(r.flight_duration_mins * 60))) AS arrival_time
        FROM booking b JOIN flight f
        ON b.flight_id = f.flight_id
        JOIN routes r
        ON f.origin_airport = r.origin_airport AND f.destination_airport = r.destination_airport
        WHERE b.booking_id = %s AND b.customer_email = %s
        """
        cursor.execute(query, (booking_id, email))
        row=cursor.fetchone()

        if not row:
            return None

        return BookingResult(row)

class BookingResult:
    """
    A data class to store and organize booking information retrieved from the database.
    Maps raw database row indexes to descriptive object attributes.
    """
    def __init__(self, row):
        self.booking_id = row[0]
        self.customer_email = row[1]
        self.payment = row[2]
        self.booking_status=row[3]

        self.flight_id = row[4]
        self.departure_date = row[5]
        self.departure_time = row[6]

        self.origin = row[7]
        self.destination = row[8]
        self.flight_duration_mins = row[9]

        self.arrival_date = row[10]
        self.arrival_time = row[11]

def hours_until_flight(departure_date, departure_time):
    """
    Calculates the total hours remaining from the current moment until the flight's departure.
    Handles different time formats (timedelta or time objects) for accuracy.
    """
    flight_datetime = datetime(year=departure_date.year,month=departure_date.month,day=departure_date.day)

    if isinstance(departure_time, timedelta):
        flight_datetime = flight_datetime + departure_time
    else:
        flight_datetime = flight_datetime.replace(
            hour=departure_time.hour,
            minute=departure_time.minute,
            second=departure_time.second
        )

    now = datetime.now()
    delta = flight_datetime - now
    return delta.total_seconds() / 3600


def can_cancel_booking(departure_date, departure_time):
    """
    Determines if a booking is eligible for cancellation based on the 36-hour policy.
    Returns True if the flight is more than 36 hours away.
    """
    return hours_until_flight(departure_date, departure_time) > 36


def calculate_cancellation_fee(payment):
    """
    Calculates a 5% cancellation fee based on the total payment amount.
    Uses Decimal for high-precision financial rounding (2 decimal places).
    """
    return (payment * Decimal('0.05')).quantize(Decimal('0.01'))

# ----cancel_booking functions----

def cancel_booking_in_db(booking_id, cancellation_fee):
    """
    Updates the database to reflect a customer cancellation.
    1. Changes booking status to 'Customer Cancellation'.
    2. Updates the payment field to the calculated cancellation fee.
    3. Deletes the seat assignments to make them available for other passengers.
    """
    with db_cur() as cursor:
        # Update the booking record with new status and fee
        cursor.execute(
            """
            UPDATE booking
            SET booking_status = 'Customer Cancellation',
                payment = %s
            WHERE booking_id = %s
            """,
            (cancellation_fee, booking_id)
        )

        # Free up the seats associated with this booking
        cursor.execute(
            """
            DELETE FROM selected_seats_in_booking
            WHERE booking_id = %s
            """,
            (booking_id,)
        )

# ----my_orders functions----

def get_all_bookings_for_customer(email):
    """
    Retrieves the complete booking history for a specific customer.
    - Joins booking, flight, and routes tables to provide a full overview.
    - Calculates arrival date and time for each flight.
    - Orders results by departure date (most recent first).
    - Returns a list of BookingResult objects.
    """
    with db_cur() as cursor:
        query = """
        SELECT 
            b.booking_id,
            b.customer_email,
            b.payment,
            b.booking_status,
            f.flight_id,
            f.departure_date,
            f.departure_time,
            r.origin_airport,
            r.destination_airport,
            r.flight_duration_mins,
            DATE(ADDTIME(TIMESTAMP(f.departure_date, f.departure_time), SEC_TO_TIME(r.flight_duration_mins * 60))) AS arrival_date,
            TIME(ADDTIME(TIMESTAMP(f.departure_date, f.departure_time), SEC_TO_TIME(r.flight_duration_mins * 60))) AS arrival_time
        FROM booking b
        JOIN flight f ON b.flight_id = f.flight_id
        JOIN routes r 
          ON f.origin_airport = r.origin_airport 
         AND f.destination_airport = r.destination_airport
        WHERE b.customer_email = %s
        ORDER BY f.departure_date DESC, f.departure_time DESC
        """
        cursor.execute(query, (email,))
        rows = cursor.fetchall()

        # Efficiently convert raw database rows into a list of BookingResult objects
        return [BookingResult(row) for row in rows]

# ----adminlogin functions----

def admin_exists(id):
    """
    Checks if a manager ID exists in the database.
    Uses 'SELECT 1' for optimized performance as we only need to verify existence.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Managers WHERE manager_id = %s", (id,))
        result = cursor.fetchone()
        return result is not None

def check_password_manager(id, password):
    """
    Validates the manager's credentials by checking both ID and password.
    Returns True if a matching record is found, False otherwise.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Managers WHERE manager_id = %s AND manager_password = %s", (id, password))
        result = cursor.fetchone()
        return result is not None

def get_admin_details(id):
    """
    Retrieves the Hebrew name of the manager for session personalization.
    Returns a tuple of (first_name, last_name) or (None, None) if not found.
    """
    with db_cur() as cursor:
        cursor.execute("SELECT first_name_hebrew, last_name_hebrew FROM managers WHERE manager_id = %s", (id,))
        result = cursor.fetchone()
        if result:
            first_name, last_name = result
            return first_name, last_name
        return None, None


# ----add_flight1 functions----

def normalize_time(t):
    """
    Standardizes various time formats into a python datetime.time object.
    Supports timedelta (from MySQL), strings (from forms), and time objects.
    """
    if isinstance(t, datetime.time):
        return t
    if isinstance(t, datetime.timedelta):
        total_seconds = int(t.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return datetime.time(hours % 24, minutes, seconds)
    if isinstance(t, str):
        try:
            return datetime.datetime.strptime(t[:5], "%H:%M").time()
        except ValueError:
            return datetime.datetime.strptime(t, "%H:%M:%S").time()
    raise TypeError(f"Unsupported time type: {type(t)}")


def get_available_aircraft(flight_date, origin, destination, dep_time):
    """
    Finds available aircraft based on technical and operational constraints.
    - Enforces aircraft size rules: Flights over 6 hours (360 mins) require 'Large' aircraft.
    - Excludes aircraft scheduled for overlapping flights (including a 30-min turnaround buffer).
    - Checks location continuity using check_aircraft_continuity_full.
    """
    if isinstance(flight_date, str):
        flight_date = datetime.datetime.strptime(flight_date, "%Y-%m-%d").date()

    dep_time = normalize_time(dep_time)

    # Fetch flight duration for the specific route
    with db_cur() as cursor:
        cursor.execute("""
            SELECT flight_duration_mins 
            FROM routes 
            WHERE origin_airport = %s AND destination_airport = %s
        """, (origin, destination))
        row = cursor.fetchone()

    if not row:
        return []

    flight_duration_mins = row[0]

    with db_cur() as cursor:
        # Complex SQL to filter out overlapping flight schedules
        # Logic updated: Only Large aircraft for flights > 360 minutes (6 hours)
        query = """
        SELECT a.aircraft_id, a.size, a.manufacturer
        FROM aircraft a
        WHERE 
        (
            (%s > 360 AND a.size = 'Large')
            OR 
            (%s <= 360)
        )
        AND a.aircraft_id NOT IN (
            SELECT f.aircraft_id
            FROM flight f
            JOIN routes r2 
              ON f.origin_airport = r2.origin_airport 
             AND f.destination_airport = r2.destination_airport
            WHERE 
              TIMESTAMP(f.departure_date, f.departure_time) < 
                TIMESTAMP(%s, %s) + INTERVAL %s MINUTE + INTERVAL 30 MINUTE
              AND
              TIMESTAMP(f.departure_date, f.departure_time) + INTERVAL r2.flight_duration_mins MINUTE + INTERVAL 30 MINUTE > 
                TIMESTAMP(%s, %s)
        );
        """
        cursor.execute(query, (
            flight_duration_mins, flight_duration_mins,
            flight_date, dep_time, flight_duration_mins,
            flight_date, dep_time
        ))
        all_available_aircraft = cursor.fetchall()

    available_aircraft = []
    for ac_id, size, manufacturer in all_available_aircraft:
        if check_aircraft_continuity_full(
                ac_id, origin, destination, flight_date, dep_time, flight_duration_mins
        ):
            available_aircraft.append({
                "aircraft_id": ac_id,
                "size": size,
                "manufacturer": manufacturer
            })

    return available_aircraft

def check_aircraft_continuity_backward(aircraft_id, new_origin, new_date, new_dep_time):
    """
    Checks if the aircraft is available to depart from the origin.
    - Locates the last flight that landed before the new scheduled departure.
    - If the aircraft is already at the correct airport, a 30-minute buffer is required.
    - If it's at a different airport, a 12-hour gap is required to account for potential ferry flights or scheduling shifts.
    """
    if isinstance(new_date, str):
        new_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").date()

    new_dep_time = normalize_time(new_dep_time)
    new_start = datetime.datetime.combine(new_date, new_dep_time)

    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        # Fetching flights for the specific aircraft up to the new flight date
        cursor.execute("""
            SELECT f.departure_date, f.departure_time, r.flight_duration_mins, f.destination_airport
            FROM flight f
            JOIN routes r ON f.origin_airport = r.origin_airport AND f.destination_airport = r.destination_airport
            WHERE f.aircraft_id = %s 
              AND f.departure_date <= %s
        """, (aircraft_id, new_date))
        flights = cursor.fetchall()

    latest_landing = None
    latest_dest = None

    for f_date, f_time, duration, f_dest in flights:
        f_time = normalize_time(f_time)
        f_start = datetime.datetime.combine(f_date, f_time)
        f_landing = f_start + datetime.timedelta(minutes=duration)

        # Identify the most recent landing before the new departure time
        if f_landing <= new_start:
            if latest_landing is None or f_landing > latest_landing:
                latest_landing = f_landing
                latest_dest = f_dest

    if latest_landing:
        # Determine gap requirements based on location match
        required_gap = turnaround if latest_dest == new_origin else half_day
        if latest_landing + required_gap > new_start:
            return False

    return True


def check_aircraft_continuity_forward(aircraft_id, new_destination, new_date, new_dep_time, new_duration):
    """
    Checks if the new flight would conflict with any future flights already assigned to this aircraft.
    - Calculates the landing time of the new flight.
    - Ensures that any subsequent flight departs from the same destination after at least a 30-minute buffer.
    - Requires a 12-hour gap if the next flight departs from a different airport.
    """
    if isinstance(new_date, str):
        new_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").date()

    new_dep_time = normalize_time(new_dep_time)
    new_start = datetime.datetime.combine(new_date, new_dep_time)
    new_landing = new_start + datetime.timedelta(minutes=new_duration)

    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        # Fetching flights for the specific aircraft starting from the new flight date
        cursor.execute("""
            SELECT f.departure_date, f.departure_time, f.origin_airport
            FROM flight f
            WHERE f.aircraft_id = %s 
              AND f.departure_date >= %s
        """, (aircraft_id, new_date))
        flights = cursor.fetchall()

    earliest_next_departure = None
    next_origin = None

    for f_date, f_time, f_origin in flights:
        f_time = normalize_time(f_time)
        f_start = datetime.datetime.combine(f_date, f_time)

        # Identify the first departure occurring after the new flight's landing
        if f_start >= new_landing:
            if earliest_next_departure is None or f_start < earliest_next_departure:
                earliest_next_departure = f_start
                next_origin = f_origin

    if earliest_next_departure:
        # Determine gap requirements based on location match
        required_gap = turnaround if next_origin == new_destination else half_day
        if new_landing + required_gap > earliest_next_departure:
            return False

    return True


def check_aircraft_continuity_full(aircraft_id, origin, destination, flight_date, dep_time, duration):
    """
    The master verification function that combines both backward and forward checks.
    Ensures that the aircraft is available to start the flight and capable of continuing its future schedule.
    """
    # Verify the aircraft can reach the departure airport on time
    if not check_aircraft_continuity_backward(aircraft_id, origin, flight_date, dep_time):
        return False

    # Verify the aircraft's next flights are not negatively impacted by this landing
    if not check_aircraft_continuity_forward(aircraft_id, destination, flight_date, dep_time, duration):
        return False

    return True

# ----add_flight2 functions----

def get_available_pilots(flight_date, origin, destination, dep_time):
    """
    Identifies available pilots based on certification and schedule.
    - Pilots must be certified for long flights if duration exceeds 6 hours (360 mins).
    - Checks for schedule overlaps with existing assignments.
    - Verifies physical location continuity.
    """
    if isinstance(flight_date, str):
        flight_date = datetime.datetime.strptime(flight_date, "%Y-%m-%d").date()

    dep_time = normalize_time(dep_time)

    # 1. Fetch flight duration
    with db_cur() as cursor:
        cursor.execute("""
            SELECT flight_duration_mins 
            FROM routes 
            WHERE origin_airport = %s AND destination_airport = %s
        """, (origin, destination))
        row = cursor.fetchone()

    if not row:
        return []

    flight_duration_mins = row[0]

    # 2. Main query for pilots - filtering by certification and time overlap
    with db_cur() as cursor:
        query = """
        SELECT p.pilot_id, p.first_name_hebrew, p.last_name_hebrew, p.long_flight_certified
        FROM pilots p
        WHERE 
        (
            (%s > 360 AND p.long_flight_certified = 1)
            OR 
            (%s <= 360)
        )
        AND p.pilot_id NOT IN (
            SELECT pa.pilot_id
            FROM pilots_assignment pa
            JOIN flight f ON pa.flight_id = f.flight_id
            JOIN routes r2 ON f.origin_airport = r2.origin_airport 
                           AND f.destination_airport = r2.destination_airport
            WHERE 
              TIMESTAMP(f.departure_date, f.departure_time) < 
                TIMESTAMP(%s, %s) + INTERVAL %s MINUTE + INTERVAL 30 MINUTE
              AND
              TIMESTAMP(f.departure_date, f.departure_time) + INTERVAL r2.flight_duration_mins MINUTE + INTERVAL 30 MINUTE > 
                TIMESTAMP(%s, %s)
        );
        """
        cursor.execute(query, (
            flight_duration_mins, flight_duration_mins,
            flight_date, dep_time, flight_duration_mins,
            flight_date, dep_time
        ))
        all_potential_pilots = cursor.fetchall()

    available_pilots = []
    for p_id, fname, lname, long_cert in all_potential_pilots:
        # Full continuity check (backward and forward)
        if check_pilot_continuity_full(p_id, origin, destination, flight_date, dep_time, flight_duration_mins):
            available_pilots.append({
                "pilot_id": p_id,
                "first_name": fname,
                "last_name": lname,
                "long_flight_certified": long_cert
            })

    return available_pilots


def check_pilot_continuity_backward(pilot_id, new_origin, new_date, new_dep_time):
    """
    Checks if the pilot can reach the origin airport from their last landing location.
    Requires a 30-min buffer if at the same airport, or 12 hours if a transfer is needed.
    """
    new_start = datetime.datetime.combine(new_date, new_dep_time)
    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        cursor.execute("""
            SELECT f.departure_date, f.departure_time, r.flight_duration_mins, f.destination_airport
            FROM flight f
            JOIN routes r ON f.origin_airport = r.origin_airport AND f.destination_airport = r.destination_airport
            JOIN pilots_assignment pa ON pa.flight_id = f.flight_id
            WHERE pa.pilot_id = %s AND f.departure_date <= %s
        """, (pilot_id, new_date))
        flights = cursor.fetchall()

    latest_landing = None
    latest_dest = None

    for f_date, f_time, duration, f_dest in flights:
        f_time = normalize_time(f_time)
        f_start = datetime.datetime.combine(f_date, f_time)
        f_landing = f_start + datetime.timedelta(minutes=duration)

        # Look for the last landing before the new departure
        if f_landing <= new_start:
            if latest_landing is None or f_landing > latest_landing:
                latest_landing = f_landing
                latest_dest = f_dest

    if latest_landing:
        required_gap = turnaround if latest_dest == new_origin else half_day
        if latest_landing + required_gap > new_start:
            return False
    return True


def check_pilot_continuity_forward(pilot_id, new_destination, new_date, new_dep_time, duration):
    """
    Ensures the new flight doesn't conflict with future flights already assigned to the pilot.
    """
    new_start = datetime.datetime.combine(new_date, new_dep_time)
    new_landing = new_start + datetime.timedelta(minutes=duration)
    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        cursor.execute("""
            SELECT f.departure_date, f.departure_time, f.origin_airport
            FROM flight f
            JOIN pilots_assignment pa ON pa.flight_id = f.flight_id
            WHERE pa.pilot_id = %s AND f.departure_date >= %s
        """, (pilot_id, new_date))
        flights = cursor.fetchall()

    earliest_next_dep = None
    next_origin = None

    for f_date, f_time, f_origin in flights:
        f_time = normalize_time(f_time)
        f_start = datetime.datetime.combine(f_date, f_time)

        # Look for the first departure after the new landing
        if f_start >= new_landing:
            if earliest_next_dep is None or f_start < earliest_next_dep:
                earliest_next_dep = f_start
                next_origin = f_origin

    if earliest_next_dep:
        required_gap = turnaround if next_origin == new_destination else half_day
        if new_landing + required_gap > earliest_next_dep:
            return False
    return True


def check_pilot_continuity_full(pilot_id, origin, destination, flight_date, dep_time, duration):
    """
    Performs both backward and forward continuity checks for a pilot.
    """
    if not check_pilot_continuity_backward(pilot_id, origin, flight_date, dep_time):
        return False
    if not check_pilot_continuity_forward(pilot_id, destination, flight_date, dep_time, duration):
        return False
    return True


def check_attendant_continuity_backward(attendant_id, new_origin, new_date, new_dep_time):
    """
    Checks if the flight attendant can reach the origin airport from their last landing location.
    """
    new_start = datetime.datetime.combine(new_date, new_dep_time)
    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        cursor.execute("""
            SELECT f.departure_date, f.departure_time, r.flight_duration_mins, f.destination_airport
            FROM flight f
            JOIN routes r ON f.origin_airport = r.origin_airport AND f.destination_airport = r.destination_airport
            JOIN flight_attendants_assignment aa ON aa.flight_id = f.flight_id
            WHERE aa.attendant_id = %s AND f.departure_date <= %s
        """, (attendant_id, new_date))
        flights = cursor.fetchall()

    latest_landing = None
    latest_dest = None

    for f_date, f_time, duration, f_dest in flights:
        f_time = normalize_time(f_time)
        f_start = datetime.datetime.combine(f_date, f_time)
        f_landing = f_start + datetime.timedelta(minutes=duration)

        if f_landing <= new_start:
            if latest_landing is None or f_landing > latest_landing:
                latest_landing = f_landing
                latest_dest = f_dest

    if latest_landing:
        required_gap = turnaround if latest_dest == new_origin else half_day
        if latest_landing + required_gap > new_start:
            return False
    return True

def check_attendant_continuity_forward(attendant_id, new_destination, new_date, new_dep_time, duration):
    """
    Ensures the new flight doesn't conflict with future flights assigned to the attendant.
    """
    new_start = datetime.datetime.combine(new_date, new_dep_time)
    new_landing = new_start + datetime.timedelta(minutes=duration)
    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        cursor.execute("""
            SELECT f.departure_date, f.departure_time, f.origin_airport
            FROM flight f
            JOIN flight_attendants_assignment aa ON aa.flight_id = f.flight_id
            WHERE aa.attendant_id = %s AND f.departure_date >= %s
        """, (attendant_id, new_date))
        flights = cursor.fetchall()

    earliest_next_dep = None
    next_origin = None

    for f_date, f_time, f_origin in flights:
        f_time = normalize_time(f_time)
        f_start = datetime.datetime.combine(f_date, f_time)

        if f_start >= new_landing:
            if earliest_next_dep is None or f_start < earliest_next_dep:
                earliest_next_dep = f_start
                next_origin = f_origin

    if earliest_next_dep:
        required_gap = turnaround if next_origin == new_destination else half_day
        if new_landing + required_gap > earliest_next_dep:
            return False
    return True

def check_attendant_continuity_full(attendant_id, origin, destination, flight_date, dep_time, duration):
    """
    Performs both backward and forward continuity checks for a flight attendant.
    """
    if not check_attendant_continuity_backward(attendant_id, origin, flight_date, dep_time):
        return False
    if not check_attendant_continuity_forward(attendant_id, destination, flight_date, dep_time, duration):
        return False
    return True

def get_available_attendants(flight_date, origin, destination, dep_time):
    """
    Identifies available flight attendants.
    - Standardizes date and time format.
    - Filters by long-flight certification if the flight exceeds 6 hours (360 mins).
    - Excludes staff with overlapping schedules.
    - Verifies physical location continuity.
    """
    if isinstance(flight_date, str):
        flight_date = datetime.datetime.strptime(flight_date, "%Y-%m-%d").date()

    dep_time = normalize_time(dep_time)

    # 1. Fetch flight duration to check certification requirements
    with db_cur() as cursor:
        cursor.execute("""
            SELECT flight_duration_mins 
            FROM routes 
            WHERE origin_airport = %s AND destination_airport = %s
        """, (origin, destination))
        row = cursor.fetchone()

    if not row:
        return []

    flight_duration_mins = row[0]

    with db_cur() as cursor:
        # 2. Main query: Fetch REAL certification data and filter by it
        # Threshold: 360 minutes (6 hours)
        query = """
        SELECT a.attendant_id, a.first_name_hebrew, a.last_name_hebrew, a.long_flight_certified
        FROM flight_attendants a
        WHERE 
        (
            (%s > 360 AND a.long_flight_certified = 1)
            OR 
            (%s <= 360)
        )
        AND a.attendant_id NOT IN (
            SELECT aa.attendant_id
            FROM flight_attendants_assignment aa
            JOIN flight f ON aa.flight_id = f.flight_id
            JOIN routes r2 ON f.origin_airport = r2.origin_airport 
                           AND f.destination_airport = r2.destination_airport
            WHERE 
              TIMESTAMP(f.departure_date, f.departure_time) < 
                TIMESTAMP(%s, %s) + INTERVAL %s MINUTE + INTERVAL 30 MINUTE
              AND
              TIMESTAMP(f.departure_date, f.departure_time) + INTERVAL r2.flight_duration_mins MINUTE + INTERVAL 30 MINUTE > 
                TIMESTAMP(%s, %s)
        );
        """
        cursor.execute(query, (
            flight_duration_mins, flight_duration_mins,
            flight_date, dep_time, flight_duration_mins,
            flight_date, dep_time
        ))
        all_potential_attendants = cursor.fetchall()

    available_attendants = []
    for att_id, fname, lname, long_cert in all_potential_attendants:
        # 3. Continuity check (physical location)
        if check_attendant_continuity_full(att_id, origin, destination, flight_date, dep_time, flight_duration_mins):
            available_attendants.append({
                "attendant_id": att_id,
                "first_name": fname,
                "last_name": lname,
                "long_flight_certified": long_cert  # This now comes from the DB, not a 'True' string
            })

    return available_attendants

# ----add_flight3 functions----

def get_crew_names_by_ids(pilot_ids, attendant_ids):
    """
    Fetches names and IDs of selected crew members for display on the confirmation page.
    Standardized to return formatted strings (ID - First Last).
    """
    pilot_info = []
    attendant_info = []

    with db_cur() as cursor:
        # Fetch Pilot details
        if pilot_ids:
            format_strings = ','.join(['%s'] * len(pilot_ids))
            cursor.execute(
                f"SELECT pilot_id, first_name_hebrew, last_name_hebrew FROM pilots WHERE pilot_id IN ({format_strings})",
                tuple(pilot_ids))
            pilot_info = [f"{row[0]} - {row[1]} {row[2]}" for row in cursor.fetchall()]

        # Fetch Flight Attendant details
        if attendant_ids:
            format_strings = ','.join(['%s'] * len(attendant_ids))
            cursor.execute(
                f"SELECT attendant_id, first_name_hebrew, last_name_hebrew FROM flight_attendants WHERE attendant_id IN ({format_strings})",
                tuple(attendant_ids))
            attendant_info = [f"{row[0]} - {row[1]} {row[2]}" for row in cursor.fetchall()]

    return pilot_info, attendant_info


def create_new_flight_complete(f_data, pilot_ids, attendant_ids, prices):
    """
    Creates a complete flight record across multiple tables:
    1. Registers the flight in the 'flight' table.
    2. Assigns the selected crew (pilots and attendants).
    3. Sets pricing for each available class (Economy and Business if applicable).
    """
    try:
        with db_cur() as cursor:
            # Step 1: Insert the flight into the 'flight' table
            # Default status is set to 'Active'
            cursor.execute("""
                INSERT INTO flight (
                    flight_status, 
                    departure_time, 
                    departure_date, 
                    origin_airport, 
                    destination_airport, 
                    aircraft_id
                ) VALUES ('Active', %s, %s, %s, %s, %s)
            """, (
                f_data['departure_time'],
                f_data['flight_date'],
                f_data['origin'],
                f_data['destination'],
                f_data['aircraft_id']
            ))

            # Retrieve the auto-generated ID of the newly created flight
            new_flight_id = cursor.lastrowid

            # Step 2: Assign Pilots
            for p_id in pilot_ids:
                cursor.execute("""
                    INSERT INTO pilots_assignment (flight_id, pilot_id) 
                    VALUES (%s, %s)
                """, (new_flight_id, p_id))

            # Step 3: Assign Flight Attendants
            for a_id in attendant_ids:
                cursor.execute("""
                    INSERT INTO flight_attendants_assignment (flight_id, attendant_id) 
                    VALUES (%s, %s)
                """, (new_flight_id, a_id))

            # Step 4: Update pricing in 'classes_in_flight' table
            # This allows the search function to find the flight and display its price.

            # Economy Class (Always exists regardless of aircraft size)
            cursor.execute("""
                INSERT INTO classes_in_flight (flight_id, aircraft_id, class_type, seat_price)
                VALUES (%s, %s, 'economy', %s)
            """, (new_flight_id, f_data['aircraft_id'], prices['economy']))

            # Business Class (Only for 'Large' aircraft if business price is provided)
            if f_data.get('size') == 'Large' and prices.get('business'):
                cursor.execute("""
                    INSERT INTO classes_in_flight (flight_id, aircraft_id, class_type, seat_price)
                    VALUES (%s, %s, 'business', %s)
                """, (new_flight_id, f_data['aircraft_id'], prices['business']))

            return True

    except Exception as e:
        print(f"Error creating complete flight: {e}")
        # If an error occurs, the transaction will not commit (depending on connection settings)
        return False

# ----show_flight_board functions----

def update_completed_flights():
    """
    Automatically updates flight status to 'Completed' for flights that have already landed.
    """
    with db_cur() as cursor:
        query = """
        UPDATE flight f
        JOIN routes r ON f.origin_airport = r.origin_airport 
                      AND f.destination_airport = r.destination_airport
        SET f.flight_status = 'Completed'
        WHERE f.flight_status IN ('Active', 'Fully Booked')
        AND TIMESTAMP(f.departure_date, f.departure_time) + INTERVAL r.flight_duration_mins MINUTE < NOW()
        """
        cursor.execute(query)

def flight_board(status_filter):
    """
    Fetches flight records from the database.
    - If status_filter is 'All', it retrieves everything.
    - Otherwise, it filters by the specific status (Active, Cancelled, etc.).
    - Joins with classes_in_flight to calculate the minimum starting price.
    """
    with db_cur() as cursor:
        # Build dynamic WHERE clause based on filter
        if status_filter == 'All':
            where_clause = "1=1"
            params = []
        else:
            where_clause = "f.flight_status = %s"
            params = [status_filter]

        # Query to fetch flight info and the lowest available price
        query = f"""
            SELECT 
                f.flight_id, 
                f.departure_date, 
                f.departure_time, 
                f.origin_airport, 
                f.destination_airport, 
                f.aircraft_id,
                MIN(cif.seat_price) as starting_price,
                f.flight_status
            FROM flight f
            JOIN classes_in_flight cif ON f.flight_id = cif.flight_id
            WHERE {where_clause}
            GROUP BY 
                f.flight_id, f.departure_date, f.departure_time, 
                f.origin_airport, f.destination_airport, f.aircraft_id, f.flight_status
            ORDER BY f.departure_date ASC
        """
        cursor.execute(query, params)
        return cursor.fetchall()

# ----aircraft_management functions----

def get_all_aircrafts():
    """
    Retrieves all aircraft from the database along with their seat classes.
    Organizes the data into a nested dictionary structure where each aircraft
    contains a list of its seat classes (Economy, Business, etc.).
    """
    with db_cur() as cursor:
        cursor.execute("""
            SELECT a.aircraft_id, a.manufacturer, a.size, a.purchase_date,
                   c.class_type, c.num_rows, c.num_columns
            FROM aircraft a
            LEFT JOIN class c ON a.aircraft_id = c.aircraft_id
            ORDER BY a.aircraft_id, c.class_type
        """)
        rows = cursor.fetchall()

    aircrafts = {}

    for row in rows:
        aircraft_id, manufacturer, size, purchase_date, class_type, num_rows, num_columns = row

        # Initialize aircraft entry if it's the first time seeing this ID
        if aircraft_id not in aircrafts:
            aircrafts[aircraft_id] = {
                "aircraft_id": aircraft_id,
                "manufacturer": manufacturer,
                "size": size,
                "purchase_date": purchase_date,
                "classes": []
            }

        # Add seat class info if it exists
        if class_type is not None:
            aircrafts[aircraft_id]["classes"].append({
                "class_type": class_type,
                "num_rows": num_rows,
                "num_columns": num_columns
            })

    # Return only the values (list of aircraft dictionaries)
    return aircrafts.values()

# ----admin_add_aircraft functions----

def add_aircraft(manufacturer, size):
    """
    Inserts a new aircraft into the 'aircraft' table.
    Returns the newly generated aircraft_id.
    """
    with db_cur() as cursor:

        cursor.execute("""
            INSERT INTO aircraft (manufacturer, size, purchase_date)
            VALUES (%s, %s, CURDATE())
        """, (manufacturer, size))

        aircraft_id = cursor.lastrowid
        return aircraft_id

def add_class(aircraft_id, class_type, num_rows, num_columns):
    """
    Inserts seat class configuration for a specific aircraft.
    """
    with db_cur() as cursor:
        cursor.execute("""
            INSERT INTO class (aircraft_id, class_type, num_rows, num_columns)
            VALUES (%s, %s, %s, %s)
        """, (aircraft_id, class_type, num_rows, num_columns))


def add_seats_for_class(aircraft_id, class_type, num_rows, num_cols, start_row):
    """
    Generates and inserts individual seat records into the 'seat' table.
    - aircraft_id: The ID of the aircraft these seats belong to.
    - class_type: 'economy' or 'business'.
    - num_rows/num_cols: The grid dimensions for this specific class.
    - start_row: The offset used to maintain continuous row numbering across the entire aircraft.
    """
    with db_cur() as cursor:
        # Loop through each row in the class configuration
        for r in range(num_rows):
            # Calculate the actual row number based on the starting offset
            row_num = start_row + r

            # Loop through each column to create individual seats (e.g., 1A, 1B, 1C)
            for c in range(num_cols):
                # Map the column index to a letter (0 -> 'A', 1 -> 'B', etc.)
                col_letter = string.ascii_uppercase[c]

                # Insert the specific seat coordinate into the database
                cursor.execute("""
                    INSERT INTO seat (aircraft_id, class_type, row_num, column_letter)
                    VALUES (%s, %s, %s, %s)
                """, (aircraft_id, class_type, row_num, col_letter))


# ----admin_cancel_flight functions----

def can_cant_cancel_flight(flight_id):
    """
    Business logic: Checks if a flight is more than 72 hours away.
    Returns True if cancellation is allowed, False otherwise.
    """
    with db_cur() as cursor:
        cursor.execute('''SELECT departure_time, departure_date 
                          FROM flight WHERE flight_id=%s''', (flight_id,))
        departure_time, departure_date = cursor.fetchone()

        # Normalize time and calculate the difference from 'now'
        time_obj = normalize_time(departure_time)
        flight_datetime = datetime.datetime.combine(departure_date, time_obj)
        now = datetime.datetime.now()

        diff_hours = (flight_datetime - now).total_seconds() / 3600
        return diff_hours >= 72


def get_flight_details(flight_id):
    """
    Helper function to fetch all attributes of a specific flight by ID.
    """
    with db_cur() as cursor:
        cursor.execute('''SELECT flight_id, flight_status, departure_time,
                         departure_date, origin_airport, destination_airport, 
                         aircraft_id FROM flight WHERE flight_id=%s''', (flight_id,))
        return cursor.fetchone()

# ----/admin_cancel_flight/confirm functions----

def cancel_flight(flight_id):
    """
    Updates the flight status to 'Cancelled' in the database.
    This preserves the flight record for historical purposes while marking it inactive.
    """
    with db_cur() as cursor:
        cursor.execute("UPDATE flight SET flight_status = 'Cancelled' WHERE flight_id = %s", (flight_id,))

def cancel_booking(flight_id):
    """
    Handles mass cancellation of all bookings associated with a specific flight.
    - Sets booking_status to 'System Cancellation' for all active bookings.
    - Resets payment to 0.00 as the flight is no longer operational.
    - Only affects bookings that haven't been cancelled already.
    """
    with db_cur() as cursor:
        # Updates all related bookings to reflect the system-wide cancellation
        cursor.execute("""
            UPDATE booking 
            SET booking_status = 'System Cancellation', 
                payment = 0.00 
            WHERE flight_id = %s AND booking_status != 'System Cancellation'
        """, (flight_id,))

# ----staff_management functions----


def get_all_staff():
    """
    Combines records from Pilots and Flight_attendants into a single list.
    Uses SQL UNION to align columns and add a hardcoded 'role' for each record.
    """

    with db_cur() as cursor:
        query = """
        SELECT pilot_id AS staff_id, first_name_hebrew, last_name_hebrew, phone, city, street, house_number, start_date, long_flight_certified, 'Pilot' as role
        FROM Pilots
        UNION
        SELECT attendant_id AS staff_id, first_name_hebrew, last_name_hebrew, phone, city, street, house_number, start_date, long_flight_certified, 'Flight Attendant' as role
        FROM Flight_attendants
        """
        cursor.execute(query)
        result=cursor.fetchall()
        return result

def get_pilots_only():
    """Fetches all rows from the Pilots table with a constant 'Pilot' role label."""
    with db_cur() as cursor:
        cursor.execute("SELECT pilot_id, first_name_hebrew, last_name_hebrew, phone, city, street, house_number, start_date, long_flight_certified, 'Pilot' as role FROM Pilots")
        return cursor.fetchall()

def get_attendants_only():
    """Fetches all rows from the Flight_attendants table with a constant 'Flight Attendant' role label."""
    with db_cur() as cursor:
        cursor.execute("SELECT attendant_id, first_name_hebrew, last_name_hebrew, phone, city, street, house_number, start_date, long_flight_certified, 'Flight Attendant' as role FROM Flight_attendants")
        return cursor.fetchall()

# ----add_staff functions----

def add_crew_to_db(table, id, f_name, l_name, phone, city, street, h_num, s_date, is_certified):
    """
    Handles the physical insertion of a staff member into the specified table.
    Uses an f-string to define the table name and column identity while using
    parameterized values for security.
    """
    id_column_name = "pilot_id" if table == "Pilots" else "attendant_id"
    with db_cur() as cursor:
        query = f"""
                INSERT INTO {table} 
                ({id_column_name}, first_name_hebrew, last_name_hebrew, phone, city, street, house_number, start_date, long_flight_certified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        cursor.execute(query, (id, f_name, l_name, phone, city, street, h_num, s_date, is_certified))


def is_id_exists(staff_id):
    """
    Utility function to check if a given ID is already registered in either
    the Pilots or Flight_attendants table.
    """
    with db_cur() as cursor:
        # Check Pilots table
        cursor.execute("SELECT pilot_id FROM Pilots WHERE pilot_id = %s", (staff_id,))
        if cursor.fetchone():
            return True
        # Check Flight Attendants table
        cursor.execute("SELECT attendant_id FROM Flight_attendants WHERE attendant_id = %s", (staff_id,))
        if cursor.fetchone():
            return True

    return False

