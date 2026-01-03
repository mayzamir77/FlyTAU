import mysql.connector
from contextlib import contextmanager
import datetime  # ייבוא המודול כולו
from decimal import Decimal

# אם את צריכה את date ו-time בנפרד, אפשר להוסיף:
from datetime import date, time, timedelta

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

def get_admin_details(id):
    with db_cur() as cursor:
        cursor.execute("SELECT first_name_hebrew, last_name_hebrew FROM managers WHERE manager_id = %s", (id,))
        result = cursor.fetchone()
        if result:
            first_name, last_name = result
            return first_name, last_name
        return None, None




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
def check_attendant_continuity_backward(attendant_id, new_origin, new_date, new_dep_time):
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
    if not check_attendant_continuity_backward(attendant_id, origin, flight_date, dep_time):
        return False
    if not check_attendant_continuity_forward(attendant_id, destination, flight_date, dep_time, duration):
        return False
    return True

def get_available_attendants(flight_date, origin, destination, dep_time):
    if isinstance(flight_date, str):
        flight_date = datetime.datetime.strptime(flight_date, "%Y-%m-%d").date()

    dep_time = normalize_time(dep_time)

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
        query = """
        SELECT a.attendant_id, a.first_name_hebrew, a.last_name_hebrew
        FROM flight_attendants a
        WHERE a.attendant_id NOT IN (
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
            flight_date, dep_time, flight_duration_mins,
            flight_date, dep_time
        ))
        all_potential_attendants = cursor.fetchall()

    available_attendants = []
    for att_id, fname, lname in all_potential_attendants:
        if check_attendant_continuity_full(att_id, origin, destination, flight_date, dep_time, flight_duration_mins):
            available_attendants.append({
                "attendant_id": att_id,
                "first_name": fname,
                "last_name": lname
            })

    return available_attendants


def get_crew_names_by_ids(pilot_ids, attendant_ids):
    pilot_info = []
    attendant_info = []

    with db_cur() as cursor:
        # שליפת שמות טייסים + ה-ID שלהם
        if pilot_ids:
            format_strings = ','.join(['%s'] * len(pilot_ids))
            cursor.execute(
                f"SELECT pilot_id, first_name_hebrew, last_name_hebrew FROM pilots WHERE pilot_id IN ({format_strings})",
                tuple(pilot_ids))
            # יוצר פורמט: "P1 - דני כהן"
            pilot_info = [f"{row[0]} - {row[1]} {row[2]}" for row in cursor.fetchall()]

        # שליפת שמות דיילים + ה-ID שלהם
        if attendant_ids:
            format_strings = ','.join(['%s'] * len(attendant_ids))
            cursor.execute(
                f"SELECT attendant_id, first_name_hebrew, last_name_hebrew FROM flight_attendants WHERE attendant_id IN ({format_strings})",
                tuple(attendant_ids))
            # יוצר פורמט: "A1 - מיכל אברהם"
            attendant_info = [f"{row[0]} - {row[1]} {row[2]}" for row in cursor.fetchall()]

    return pilot_info, attendant_info


def create_new_flight_complete(f_data, pilot_ids, attendant_ids, prices):
    """
    פונקציה שיוצרת טיסה קומפלט:
    1. רישום הטיסה
    2. שיבוץ צוות
    3. עדכון מחירים לכל מחלקה (כדי שיופיע בחיפוש)
    """
    try:
        with db_cur() as cursor:
            # שלב 1: הכנסת הטיסה לטבלת flight
            # סטטוס ברירת מחדל הוא 'Active'
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

            # קבלת ה-ID האוטומטי של הטיסה שנוצרה הרגע
            new_flight_id = cursor.lastrowid

            # שלב 2: שיבוץ טייסים
            for p_id in pilot_ids:
                cursor.execute("""
                    INSERT INTO pilots_assignment (flight_id, pilot_id) 
                    VALUES (%s, %s)
                """, (new_flight_id, p_id))

            # שלב 3: שיבוץ דיילים
            for a_id in attendant_ids:
                cursor.execute("""
                    INSERT INTO flight_attendants_assignment (flight_id, attendant_id) 
                    VALUES (%s, %s)
                """, (new_flight_id, a_id))

            # שלב 4: עדכון מחירים בטבלת classes_in_flight
            # זה השלב הקריטי שמאפשר לחיפוש למצוא את הטיסה ולדעת מה המחיר שלה

            # אקונומי (תמיד קיים בכל מטוס)
            cursor.execute("""
                INSERT INTO classes_in_flight (flight_id, aircraft_id, class_type, seat_price)
                VALUES (%s, %s, 'economy', %s)
            """, (new_flight_id, f_data['aircraft_id'], prices['economy']))

            # ביזנס (רק אם זה מטוס Large וקיבלנו מחיר ביזנס)
            if f_data.get('size') == 'Large' and prices.get('business'):
                cursor.execute("""
                    INSERT INTO classes_in_flight (flight_id, aircraft_id, class_type, seat_price)
                    VALUES (%s, %s, 'business', %s)
                """, (new_flight_id, f_data['aircraft_id'], prices['business']))

            return True

    except Exception as e:
        print(f"Error creating complete flight: {e}")
        # במקרה של שגיאה, המערכת לא תבצע Commit (אם ה-Connection מוגדר כך)
        return False

def get_crew_names_by_ids(pilot_ids, attendant_ids):
    pilot_info = []
    attendant_info = []
    with db_cur() as cursor:
        if pilot_ids:
            format_strings = ','.join(['%s'] * len(pilot_ids))
            cursor.execute(
                f"SELECT pilot_id, first_name_hebrew, last_name_hebrew FROM pilots WHERE pilot_id IN ({format_strings})",
                tuple(pilot_ids))
            pilot_info = [f"{row[0]} - {row[1]} {row[2]}" for row in cursor.fetchall()]

        if attendant_ids:
            format_strings = ','.join(['%s'] * len(attendant_ids))
            cursor.execute(
                f"SELECT attendant_id, first_name_hebrew, last_name_hebrew FROM flight_attendants WHERE attendant_id IN ({format_strings})",
                tuple(attendant_ids))
            attendant_info = [f"{row[0]} - {row[1]} {row[2]}" for row in cursor.fetchall()]
    return pilot_info, attendant_info

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
