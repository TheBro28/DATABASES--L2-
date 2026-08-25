# Import the tools needed to build the website and handle data
from flask import Flask, g, render_template, request, redirect, session, url_for
import sqlite3, hashlib

# Defines the database as a constant
DATABASE = 'subvay.db'

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

# Converts a plain text password into a sequre one
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def migrate_passwords():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    # Retrieves the unique ID and current password for every customer account
    cursor.execute("SELECT ID, password FROM CUSTOMER")
    users = cursor.fetchall()
    
    # Loops through each customer
    for user_id, password in users:
        # Checks if the password length is not 64 characters (Type of Hash is 64 characters)
        if len(password) != 64:
            # Converts text password into a secure hashed string
            hashed = hash_password(password)
            # Updates the database to overwrite current unhashed passwords
            cursor.execute("UPDATE CUSTOMER SET password = ? WHERE ID = ?", (hashed, user_id))
            
    # Saves updates to the database permanently
    db.commit()
    db.close()


@app.context_processor
def inject_user_name():
    # Checks if a user's email is currently saved
    email = session.get('user')
    
    # If a user is logged in, look up their name in the database
    if email:
        query = "SELECT firstname FROM CUSTOMER WHERE email = ?"
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        db.close()
        
        # If an account is found, pass their first name as 'user_name'
        if result:
            return dict(user_name=result[0])
            
    # If no one is logged in, pass None so the templates know to show the "Sign In" button instead
    return dict(user_name=None)


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

# Account details Page (Only avaliable if the user is logged in)
@app.route('/account')
def account_details():
    if 'user' not in session:
        return redirect('/signin')
    email = session['user']
    query = "SELECT firstname, lastname, ph_number, email FROM CUSTOMER WHERE email = ?"
    customer_info = query_db(query, (email,), one=True)
    return render_template("account.html", customer=customer_info)

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

# Single sandwich page opens when you click a specific sandwich
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
    
    # Check if the email and password are in database
    verify = verification(email, password)
    if verify:
        # Log them in and redirect them to the home page
        session['user'] = email
        return redirect('/')
    else:
        # Reload the login page with a red error warning text
        return render_template('login.html', warning=True)

# Check password and email
def verification(email, password):
    # Find the password belonging to the typed email address
    query = "SELECT password FROM CUSTOMER WHERE email = ?"
    actual_password = query_db(query, (email,), one=True)
    
    # Compare the user's typed password with the actual saved password
    if actual_password:
        return hash_password(password) == actual_password[0]
    return False

# Starts up the website server
if __name__ == "__main__":
    migrate_passwords()
    app.run(debug=True)
