
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
def homepage():
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
        return redirect('/homepage')



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
        return redirect('/homepage')

    else:
        add_customer_to_db(email,first_name,last_name,passport_number,birth_date,date.today(),password)
        return redirect('/homepage')

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
        return redirect('/homepage')

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

@app.route('/select_flight', methods=['POST'])
def select_flight():
    flight_id = request.form.get('flight_id')

    classes = class_in_plane(flight_id)

    if len(classes) == 1:
        pass

    else:
        pass



if __name__=="__main__":
    app.run(debug=True)
