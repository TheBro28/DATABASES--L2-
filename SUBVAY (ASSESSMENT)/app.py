from flask import Flask, g, render_template, request, redirect, session, url_for
import sqlite3

DATABASE = 'subvay(3).db'

# Initialise app
app = Flask(__name__)
# A secret key is required to use Flask sessions for logging in
app.secret_key = '4a9f83b21cde567890abcdef1234567890abcdef12345678' 

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# --- MENU CARD RENDERING --- #

@app.route('/menu', methods=['GET'])
def menu():
    user = session.get('user')
    
    # Connect to database and fetch all sandwiches
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    # Query all data selecting name, image_url, and price
    query = "SELECT name, image_url, price FROM PRE_SANDWICH"
    cursor.execute(query)
    all_sandwiches = cursor.fetchall()
    db.close()
        
    return render_template(
        'menu.html', 
        all_sandwiches=all_sandwiches, 
        user=user
    )

# --- ROUTE PATHS --- #

@app.route('/')
def home():
    return render_template("index.html") 

@app.route('/offers')
def offers():
    return render_template("offers.html")

@app.route('/history')
def history():
    return render_template("history.html")

@app.route('/checkout')
def checkout():
    return render_template("checkout.html")

@app.route('/signin')
def signin():
    return render_template("signin.html")

# --- DATABASE LOGIN HANDLING  --- #

@app.route('/log-in')
def login():
    return render_template('login.html', warning=None)

@app.post('/get_login_data')
def handle_login_data():
    email = str(request.form['email'])
    password = str(request.form['password'])
    
    verify = verification(email, password)
    if verify:
        session['user'] = email
        return redirect('/')
    else:
        return render_template('login.html', warning=True)

def verification(email, password):
    query = "SELECT password FROM user WHERE email = ?"
    actual_password = query_db(query, (email,), one=True)
    
    if actual_password:
        return password == actual_password[0]
    return False

if __name__ == "__main__":
    app.run(debug=True)