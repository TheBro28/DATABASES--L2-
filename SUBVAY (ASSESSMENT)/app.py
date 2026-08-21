# Import the tools needed to build the website and handle data
from flask import Flask, g, render_template, request, redirect, session, url_for
import sqlite3

# Defines the database as a constant
DATABASE = 'subvay(3).db'

# Create and set up the website application
app = Flask(__name__)
# security password that protects user logins from hackers
app.secret_key = '4a9f83b21cde567890abcdef1234567890abcdef12345678' 

# Open connection to database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# Automatically close database connection when page finishes loading
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Tool to search or look up information inside the database
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# --- ROUTE PATHS --- #

# Home page
@app.route('/')
def home():
    return render_template("index.html") 

# Offers page
@app.route('/offers')
def offers():
    return render_template("offers.html")

# History Page
@app.route('/history')
def history():
    return render_template("history.html")

# Checkout Page
@app.route('/checkout')
def checkout():
    return render_template("checkout.html")

# Sign in Page
@app.route('/signin')
def signin():
    return render_template("signin.html")

# --- MENU CARD RENDERING --- #

# Menu page
@app.route('/menu', methods=['GET'])
def menu():
    # Check if a user is currently logged in
    user = session.get('user')
    
    # Open the database to read information
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    # Get the ID, name, description, image, and price for every sandwich
    query = "SELECT ID, name, description, image_url, price FROM PRE_SANDWICH"
    cursor.execute(query)
    all_sandwiches = cursor.fetchall()
    db.close()
        
    # Send the sandwich information layout
    return render_template(
        'menu.html', 
        all_sandwiches=all_sandwiches, 
        user=user
    )

# --- SANDWICH PAGE RENDERING --- #

# Single sandwich page: opens when you click a specific sandwich
@app.route('/sandwich/<int:id>')
def sandwich(id):
    # Search the database for the single sandwich that matches the clicked ID
    query = "SELECT ID, name, description, image_url, price FROM PRE_SANDWICH WHERE ID = ?"
    sandwich = query_db(query, (id,), one=True)
    
    # Error message if the sandwich ID doesn't exist
    if sandwich is None:
        return "Sandwich not found", 404
        
    # Render single sandwich's details on screen
    return render_template("sandwich.html", sandwich=sandwich)

# --- DATABASE LOGIN HANDLING  --- #

# Login box
@app.route('/log-in')
def login():
    return render_template('login.html', warning=None)

# Processes the data when a user types their details and clicks "Login"
@app.post('/get_login_data')
def handle_login_data():
    # Read the email and password typed into the form boxes
    email = str(request.form['email'])
    password = str(request.form['password'])
    
    # Check if the credentials match our saved customer accounts
    verify = verification(email, password)
    if verify:
        # Log them in and redirect them to the home page
        session['user'] = email
        return redirect('/')
    else:
        # Reload the login page with a red error warning text
        return render_template('login.html', warning=True)

# Check that cross-references passwords with the database
def verification(email, password):
    # Find the password belonging to the typed email address
    query = "SELECT password FROM user WHERE email = ?"
    actual_password = query_db(query, (email,), one=True)
    
    # Compare the user's typed password with the actual saved password
    if actual_password:
        return password == actual_password[0]
    return False

# Starts up the website server
if __name__ == "__main__":
    app.run(debug=True)
