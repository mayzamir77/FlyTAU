import mysql.connector
from contextlib import contextmanager
from datetime import datetime, date, time, timedelta
from decimal import Decimal


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

class FlightResult:     #flight info
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

##login checks
def guest_customer_exists(email):
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM guest_customer WHERE email = %s", (email,))
        result = cursor.fetchone()
        return result is not None

def registered_customer_exists(email):
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Registered_Customer WHERE email = %s", (email,))
        result = cursor.fetchone()
        return result is not None

def check_password_customer(email, password):
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Registered_Customer WHERE email = %s and customer_password= %s", (email,password))
        result = cursor.fetchone()
        return result is not None

def get_customer_details(email):
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
    with db_cur() as cursor:
        cursor.execute("SELECT phone_number FROM registered_customer_phones WHERE email = %s", (email,))
        result = [row[0] for row in cursor.fetchall()]
        return result


##signup func
def turn_into_registered_db(email, first_name, last_name, passport_number, birth_date, registration_date, password, new_phones):
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
    with db_cur() as cursor:
        cursor.execute("INSERT INTO Registered_Customer VALUES (%s,%s,%s,%s,%s,%s,%s)",
                       (email, first_name, last_name, passport_number, birth_date, registration_date, password))
        for p in phones:
            cursor.execute("INSERT INTO registered_customer_phones VALUES(%s,%s)",(email,p))


def admin_exists(id):
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Managers WHERE manager_id= %s" ,(id,))
        result = cursor.fetchone()
        return result is not None

def check_password_manager(id,password):
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Managers WHERE manager_id= %s and manager_password=%s" ,(id,password))
        result = cursor.fetchone()
        return result is not None

def update_customer_in_db(email, first_name, last_name, passport):
    with db_cur() as cursor:
        query = """
            UPDATE registered_customer 
            SET first_name_english = %s, last_name_english = %s, passport_number = %s 
            WHERE email = %s
        """
        cursor.execute(query, (first_name, last_name, passport, email))


##search flight func
def get_flights_origins():
    with db_cur() as cursor:
        cursor.execute("SELECT DISTINCT origin_airport FROM routes")
        result = cursor.fetchall()
        return result

def get_flights_destinations():
    with db_cur() as cursor:
        cursor.execute("SELECT DISTINCT destination_airport FROM routes")
        result = cursor.fetchall()
        return result

def get_vacant_seats(flight_id):
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


def get_relevant_flights(date, origin, destination, requested_seats):
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

            vacant_seats = get_vacant_seats(flight_id)
            class_vacant = [s for s in vacant_seats if s[0] == class_type]

            if len(class_vacant) >= int(requested_seats):
                final_results.append(opt)
        final_objects = []
        for opt in final_results:
            final_objects.append(FlightResult(opt))

        return final_objects

def get_price_for_class(flight_id, class_type):
    with db_cur() as cursor:
        cursor.execute("SELECT seat_price from classes_in_flight WHERE flight_id =%s and class_type=%s",(flight_id,class_type))
        result = cursor.fetchone()
        if result:
            return result[0]
        return 0


def get_class_layout(flight_id, class_type):
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

##manage bookings func - rona

def get_booking_details(booking_id, email):
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

class BookingResult:    #saves the info about a booking, row indicates a row in the results table
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

def hours_until_flight(departure_date, departure_time):  #checks time until flight

    flight_datetime = datetime(
        year=departure_date.year,
        month=departure_date.month,
        day=departure_date.day
    )

    if isinstance(departure_time, timedelta):     #if mysql brings the time as timedelta
        flight_datetime = flight_datetime + departure_time
    else:
        flight_datetime = flight_datetime.replace(
            hour=departure_time.hour,
            minute=departure_time.minute,
            second=departure_time.second
        )

    now = datetime.now()
    delta = flight_datetime - now
    return delta.total_seconds() / 3600      #the final time calculation


def can_cancel_booking(departure_date, departure_time):   #checks if can cancel based on time until flight
    return hours_until_flight(departure_date, departure_time) > 36   #returns T/F

def add_booking_to_db(email,first_name,last_name,flight_id,booking_date,booking_status,payment,aircraft_id,class_type,seats,phones):
    with db_cur() as cursor:
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

        cursor.execute("INSERT INTO booking (customer_email, flight_id, booking_date, booking_status, payment) VALUES (%s,%s,%s,%s,%s)",
                       (email,flight_id,booking_date,booking_status,payment))
        new_booking_id = cursor.lastrowid
        for seat in seats:
            row = ''.join(filter(str.isdigit, seat))
            col = ''.join(filter(str.isalpha, seat))
            cursor.execute("""
                            INSERT INTO selected_seats_in_booking (booking_id, aircraft_id, class_type, row_num, column_letter)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (new_booking_id, aircraft_id, class_type, row, col))

        return new_booking_id

def calculate_cancellation_fee(payment):   #checks how much the cancellation fee
    return (payment * Decimal('0.05')).quantize(Decimal('0.01'))

def cancel_booking_in_db(booking_id,cancellation_fee):    #updating the db after a flight is cancelled
    with db_cur() as cursor:     #changing booking status and payment=0
        cursor.execute(
            """
            UPDATE booking
            SET booking_status = 'Customer Cancellation',
                payment = %s
            WHERE booking_id = %s
            """,
            (cancellation_fee,booking_id)
        )

        cursor.execute(      #freeing up the seats
            """
            DELETE FROM selected_seats_in_booking
            WHERE booking_id = %s
            """,
            (booking_id,)
        )

def get_all_bookings_for_customer(email):
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

        return [BookingResult(row) for row in rows]
