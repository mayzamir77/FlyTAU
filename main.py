
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
def homepage():## נעשה ניתובים לדף הבית הרלוונטי לפי סשנים
    return render_template('homepage.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    if not customer_exists(email):
        return render_template(
            'login.html',
            error="User not found. Please register or place an order as an unregistered customer."
        )

    if not registered_customer_exists(email):
        return render_template(
            'login.html',
            error="This email belongs to an unregistered customer. Please register to log in."
        )

    if not check_password_customer(email, password):
        return render_template(
            'login.html',
            error="Incorrect password.", email=email
        )

    else:
        return redirect('/')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    email = request.form.get('email')
    passport_number=request.form.get('passport_number')
    birth_date= request.form.get('birth_date')
    password = request.form.get('password')
    first_name=request.form.get('first_name')
    last_name=request.form.get('last_name')

    if registered_customer_exists(email):
        return render_template('signup.html', error="This email is taken")

    if customer_exists(email):
        turn_into_registered_db(email,first_name,last_name,passport_number,birth_date,date.today(),password)
        return redirect('/')

    else:
        add_customer_to_db(email,first_name,last_name,passport_number,birth_date,date.today(),password)
        return redirect('/')

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

##נעביר להומפייג את כל הממשק של סרצ פלייטס
@app.route('/search_flights', methods=['GET', 'POST'])
def search_flights():
    if request.method == 'GET':
        return render_template('search_flights.html', origins= get_flights_origins(), destinations=get_flights_destinations())

    date= request.form.get('flight_date')
    origin = request.form.get('origin')
    destination=request.form.get('destination')

    result = get_relevant_flights(date,origin, destination)
    if not result:
        return render_template('search_flights.html', origins=get_flights_origins(),
                               destinations=get_flights_destinations(), error='No available flights. Please select differently')
    return render_template('show_flights.html', flights= result)


##הולך להיות שואו פלייטס שמראה את כל הטיסות הרלוונטיות
@app.route('/select_flight', methods=['POST'])
def select_flight():
    flight_id = request.form.get('flight_id')

    classes = class_in_plane(flight_id)

    if len(classes) == 1:
        pass

    else:
        pass


@app.route('/select_seats_economy')
def select_seats_economy():
    # בחירת מושבים למחלקת תיירים [cite: 84, 88]
    pass


@app.route('/select_seats_business')
def select_seats_business():
    # בחירת מושבים למחלקת עסקים [cite: 85, 99]
    pass

@app.route('/passenger_details')
def passenger_details():
    # להוסיף / מתמלא אוטומטית פרטי הנוסעים
    #להוסיף לפה אם הגענו בפוסט אז לשים את פרטי ההזמנה הסופיים
    pass


# --- ממשק לקוח / אורח ---

@app.route('/logout')
def logout():
    # ניתוב לדף הבית + מחיקת סשן [cite: 69, 73]
    pass

@app.route('/manage_booking', methods=['GET', 'POST'])
def manage_booking():
    # ניהול הזמנה לפי מספר הזמנה ואימייל [cite: 14, 20, 129]
    pass

@app.route('/booking_history')
def booking_history():
    # צפייה בהיסטוריית הזמנות למשתמשים רשומים בלבד [cite: 66, 71, 158]
    pass




@app.route('/order_summary', methods=['GET', 'POST'])
def order_summary():
    # סיכום הזמנה ומילוי פרטי נוסע [cite: 96, 110, 111]
    pass

@app.route('/confirm_order')
def confirm_order():
    # דף אישור סופי לאחר ביצוע הזמנה ועדכון DB [cite: 117, 119]
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

if __name__=="__main__":
    app.run(debug=True)
