import mysql.connector
from contextlib import contextmanager
import datetime




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


def get_admin_details(id):
    with db_cur() as cursor:
        cursor.execute("SELECT first_name_hebrew, last_name_hebrew FROM managers WHERE manager_id = %s", (id,))
        result = cursor.fetchone()
        if result:
            first_name, last_name = result
            return first_name, last_name
        return None, None


import datetime


# פונקציית עזר לנירמול זמן - מעודכנת לטיפול גמיש יותר
def normalize_time(t):
    if isinstance(t, datetime.time):
        return t
    if isinstance(t, datetime.timedelta):
        total_seconds = int(t.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return datetime.time(hours % 24, minutes, seconds)
    if isinstance(t, str):
        # טיפול במחרוזות (למשל "14:30" או "14:30:00")
        try:
            return datetime.datetime.strptime(t[:5], "%H:%M").time()
        except ValueError:
            return datetime.datetime.strptime(t, "%H:%M:%S").time()
    raise TypeError(f"Unsupported time type: {type(t)}")


def get_available_aircraft(flight_date, origin, destination, dep_time):
    if isinstance(flight_date, str):
        flight_date = datetime.datetime.strptime(flight_date, "%Y-%m-%d").date()

    dep_time = normalize_time(dep_time)

    # שליפת משך הטיסה מהמסלול
    with db_cur() as cursor:
        cursor.execute("""
            SELECT flight_duration_mins 
            FROM routes 
            WHERE origin_airport = %s AND destination_airport = %s
        """, (origin, destination))
        row = cursor.fetchone()

    if not row:
        return []  # אין מסלול כזה

    flight_duration_mins = row[0]

    # שאילתה מרכזית - שימוש ב-INTERVAL לצורך דיוק מול MySQL
    # השאילתה מסננת מטוסים שפיזית חופפים בזמן הטיסה (כולל 30 דקות סבב)
    with db_cur() as cursor:
        query = """
        SELECT a.aircraft_id, a.size, a.manufacturer
        FROM aircraft a
        WHERE 
        (
            (%s > 180 AND a.size = 'Large')
            OR 
            (%s <= 180)
        )
        AND a.aircraft_id NOT IN (
            SELECT f.aircraft_id
            FROM flight f
            JOIN routes r2 
              ON f.origin_airport = r2.origin_airport 
             AND f.destination_airport = r2.destination_airport
            WHERE 
              -- בדיקת חפיפה: הטיסה הקיימת מתחילה לפני שהחדשה נגמרת
              -- וגם הטיסה הקיימת נגמרת אחרי שהחדשה מתחילה
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
    if isinstance(new_date, str):
        new_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").date()

    new_dep_time = normalize_time(new_dep_time)
    new_start = datetime.datetime.combine(new_date, new_dep_time)

    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        # אופטימיזציה: שליפת טיסות רק מטווח זמן רלוונטי (יום לפני)
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

        # מחפשים את הטיסה האחרונה שנחתה לפני זמן ההמראה המתוכנן
        if f_landing <= new_start:
            if latest_landing is None or f_landing > latest_landing:
                latest_landing = f_landing
                latest_dest = f_dest

    if latest_landing:
        # אם המטוס נחת ביעד אחר, דורשים 12 שעות. אם באותו יעד, רק 30 דקות.
        required_gap = turnaround if latest_dest == new_origin else half_day
        if latest_landing + required_gap > new_start:
            return False

    return True


def check_aircraft_continuity_forward(aircraft_id, new_destination, new_date, new_dep_time, new_duration):
    if isinstance(new_date, str):
        new_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").date()

    new_dep_time = normalize_time(new_dep_time)
    new_start = datetime.datetime.combine(new_date, new_dep_time)
    new_landing = new_start + datetime.timedelta(minutes=new_duration)

    turnaround = datetime.timedelta(minutes=30)
    half_day = datetime.timedelta(hours=12)

    with db_cur() as cursor:
        # אופטימיזציה: שליפת טיסות רק מטווח זמן רלוונטי (יום אחרי)
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

        # מחפשים את הטיסה הראשונה שיוצאת אחרי שהטיסה הנוכחית נחתה
        if f_start >= new_landing:
            if earliest_next_departure is None or f_start < earliest_next_departure:
                earliest_next_departure = f_start
                next_origin = f_origin

    if earliest_next_departure:
        # אם הטיסה הבאה יוצאת מיעד אחר מזה שנחתנו בו, דורשים 12 שעות
        required_gap = turnaround if next_origin == new_destination else half_day
        if new_landing + required_gap > earliest_next_departure:
            return False

    return True


def check_aircraft_continuity_full(aircraft_id, origin, destination, flight_date, dep_time, duration):
    # בדיקה אחורה - האם המטוס פנוי להמריא מהמוצא
    if not check_aircraft_continuity_backward(aircraft_id, origin, flight_date, dep_time):
        return False

    # בדיקה קדימה - האם המטוס יוכל לבצע את טיסותיו הבאות אחרי שינחת ביעד
    if not check_aircraft_continuity_forward(aircraft_id, destination, flight_date, dep_time, duration):
        return False

    return True


def get_available_pilots(flight_date, origin, destination, dep_time):
    if isinstance(flight_date, str):
        flight_date = datetime.datetime.strptime(flight_date, "%Y-%m-%d").date()

    dep_time = normalize_time(dep_time)

    # 1. שליפת משך הטיסה
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

    # 2. שאילתה מרכזית לטייסים - סינון לפי הכשרה וחפיפת זמנים
    with db_cur() as cursor:
        query = """
        SELECT p.pilot_id, p.first_name_hebrew, p.last_name_hebrew, p.long_flight_certified
        FROM pilots p
        WHERE 
        (
            (%s > 180 AND p.long_flight_certified = 1)
            OR 
            (%s <= 180)
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
        # בדיקת המשכיות מלאה (אחורה וקדימה)
        if check_pilot_continuity_full(p_id, origin, destination, flight_date, dep_time, flight_duration_mins):
            available_pilots.append({
                "pilot_id": p_id,
                "first_name": fname,
                "last_name": lname,
                "long_flight_certified": long_cert
            })

    return available_pilots


def check_pilot_continuity_backward(pilot_id, new_origin, new_date, new_dep_time):
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
    if not check_pilot_continuity_backward(pilot_id, origin, flight_date, dep_time):
        return False
    if not check_pilot_continuity_forward(pilot_id, destination, flight_date, dep_time, duration):
        return False
    return True
def get_flight_details(flight_id):
    with db_cur() as cursor:
        cursor.execute('''SELECT flight_id, flight_status, departure_time,
         departure_date, origin_airport, destination_airport, 
         aircraft_id FROM flight WHERE flight_id=%s''', (flight_id,))
        result=cursor.fetchone()
        return result

def can_cant_cancel_flight(flight_id):
    with db_cur() as cursor:
        cursor.execute('''SELECT departure_time,
         departure_date FROM flight WHERE flight_id=%s''', (flight_id,))
        departure_time, departure_date =cursor.fetchone()
        time_obj = normalize_time(departure_time)
        flight_datetime = datetime.datetime.combine(departure_date, time_obj)
        now = datetime.datetime.now()
        diff_hours = (flight_datetime - now).total_seconds() / 3600
        return diff_hours >= 72

def cancel_flight(flight_id):
    with db_cur() as cursor:
        cursor.execute("UPDATE flight SET flight_status = 'Cancelled' WHERE flight_id = %s", (flight_id,))

def cancel_booking(flight_id):
    with db_cur() as cursor:
        # וודאי ש 'System Cancellation' כתוב בדיוק כמו ב-CHECK CONSTRAINT בסכימה
        cursor.execute("""
            UPDATE booking 
            SET booking_status = 'System Cancellation', 
                payment = 0.00 
            WHERE flight_id = %s AND booking_status != 'System Cancellation'
        """, (flight_id,))