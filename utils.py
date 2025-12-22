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

def turn_into_registered_db(email,first_name,last_name,passport_number,birth_date,registration_date,password):
    with db_cur() as cursor:
        cursor.execute("UPDATE Customer SET first_name_english = %s, last_name_english = %s WHERE email = %s",(first_name, last_name, email))
        cursor.execute("DELETE FROM Unregistered_Customer WHERE email= %s",(email,))
        cursor.execute("INSERT INTO Registered_Customer VALUES (%s,%s,%s,%s,%s)", (email,passport_number,birth_date,registration_date,password))

def add_customer_to_db(email,first_name,last_name,passport_number,birth_date,registration_date,password):
    with db_cur() as cursor:
        cursor.execute("INSERT INTO Customer VALUES (%s,%s,%s)", (email,first_name,last_name))
        cursor.execute("INSERT INTO Registered_Customer VALUES (%s,%s,%s,%s,%s)",
                       (email, passport_number, birth_date, registration_date, password))


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

def get_flights_origins():
    with db_cur() as cursor:
        cursor.execute("SELECT DISTINCT origin_airport FROM Flight")
        result = cursor.fetchall()
        return result

def get_flights_destinations():
    with db_cur() as cursor:
        cursor.execute("SELECT DISTINCT destination_airport FROM Flight")
        result = cursor.fetchall()
        return result

def get_relevant_flights(date, origin, destination):
    with db_cur() as cursor:
        cursor.execute( ''' SELECT flight_id, flight_duration, departure_time, departure_date, origin_airport, destination_airport, aircraft_id,
            DATE(
                    ADDTIME(
                        TIMESTAMP(departure_date, departure_time),
                        SEC_TO_TIME(flight_duration * 60)
                    )
                ) AS arrival_date,

                TIME(
                    ADDTIME(
                        TIMESTAMP(departure_date, departure_time),
                        SEC_TO_TIME(flight_duration * 60)
                    )
                ) AS arrival_time

            FROM Flight
            WHERE departure_date = %s AND origin_airport = %s AND destination_airport = %s AND flight_status = %s''',
            (date, origin, destination, 'Active'))
        return cursor.fetchall()

def class_in_plane(aircraft_id):
    with db_cur() as cursor:
        cursor.execute('SELECT class_type FROM class WHERE aircraft_id=%s', (aircraft_id,))
        return [row[0] for row in cursor.fetchall()]





