import mysql.connector
from contextlib import contextmanager

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

class FlightResult:
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
def customer_exists(email):
    with db_cur() as cursor:
        cursor.execute("SELECT 1 FROM Customer WHERE email = %s", (email,))
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
        cursor.execute("SELECT first_name_english, last_name_english,passport_number,birth_date FROM Customer as c join registered_customer as rc on c.email=rc.email WHERE c.email = %s", (email,))
        result = cursor.fetchone()
        if result:
            return result

##signup func
def turn_into_registered_db(email,first_name,last_name,passport_number,birth_date,registration_date,password, phones):
    with db_cur() as cursor:
        cursor.execute("UPDATE Customer SET first_name_english = %s, last_name_english = %s WHERE email = %s",(first_name, last_name, email))
        cursor.execute("DELETE FROM Unregistered_Customer WHERE email= %s",(email,))
        cursor.execute("INSERT INTO Registered_Customer VALUES (%s,%s,%s,%s,%s)", (email,passport_number,birth_date,registration_date,password))
        for p in phones:
            cursor.execute("INSERT IGNORE INTO customer_phone_numbers VALUES(%s,%s)",(email,p))

def add_customer_to_db(email,first_name,last_name,passport_number,birth_date,registration_date,password, phones):
    with db_cur() as cursor:
        cursor.execute("INSERT INTO Customer VALUES (%s,%s,%s)", (email,first_name,last_name))
        cursor.execute("INSERT INTO Registered_Customer VALUES (%s,%s,%s,%s,%s)",
                       (email, passport_number, birth_date, registration_date, password))
        for p in phones:
            cursor.execute("INSERT INTO customer_phone_numbers VALUES(%s,%s)",(email,p))


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





