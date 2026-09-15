# Import the tools needed to build the website and handle data
from flask import Flask, g, render_template, request, redirect, session, url_for
import sqlite3, hashlib

# Defines the database as a constant
DATABASE = 'subvay.db'

# Create and set up the website application
app = Flask(__name__)
# security password that protects users logins from hackers
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

# Sign in / Register Page
@app.route('/signin')
def signin():
    return render_template("signin.html", warning=None, register_warning=None, show_register=False)

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

    # Finds the cheapest bread and cheese to work out a starting price for a custom sub
    cheapest_bread = cursor.execute("SELECT MIN(price) FROM BREAD").fetchone()[0]
    cheapest_cheese = cursor.execute("SELECT MIN(price) FROM CHEESE").fetchone()[0]
    custom_starting_price = cheapest_bread + cheapest_cheese

    db.close()
        
    # Send the sandwich information layout
    return render_template(
        'menu.html', 
        all_sandwiches=all_sandwiches, 
        user=user,
        custom_starting_price=custom_starting_price
    )

# Custom sandwich builder page
@app.route('/custom-sandwich')
def custom_sandwich():
    return render_template("custom_sandwich.html")

# --- DATABASE LOGIN HANDLING  --- #

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
        # Reload the sign-in page with a red error warning text on the login box
        return render_template('signin.html', warning=True, register_warning=None, show_register=False)

# Check password and email
def verification(email, password):
    # Find the password belonging to the typed email address
    query = "SELECT password FROM CUSTOMER WHERE email = ?"
    actual_password = query_db(query, (email,), one=True)
    
    # Compare the user's typed password with the actual saved password
    if actual_password:
        return hash_password(password) == actual_password[0]
    return False

# --- DATABASE REGISTRATION HANDLING --- #

# Finds the store's ID number that matches the name chosen in the dropdown
def get_store_id(store_name):
    query = "SELECT ID FROM STORES WHERE name = ?"
    result = query_db(query, (store_name,), one=True)
    return result[0] if result else None

# Finds the gender's ID number that matches the option chosen in the dropdown
def get_gender_id(gender_name):
    query = "SELECT ID FROM GENDER WHERE name = ?"
    result = query_db(query, (gender_name,), one=True)
    return result[0] if result else None

# Processes the data when a user submits the registration form
@app.post('/handle_register_data')
def handle_register_data():
    # Read the details typed into the registration form boxes
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    email = request.form['email']
    phonenumber = request.form['phonenumber']
    password = request.form['password']
    confirm_password = request.form['conpassword']
    prefstore_name = request.form['prefstore']
    gender_name = request.form['gender']

    # Passwords must match before doing anything else
    if password != confirm_password:
        return render_template('signin.html', warning=None, register_warning="Passwords do not match.", show_register=True)

    # Check if an account with this email already exists
    existing = query_db("SELECT ID FROM CUSTOMER WHERE email = ?", (email,), one=True)
    if existing:
        return render_template('signin.html', warning=None, register_warning="An account with that email already exists.", show_register=True)

    # Convert the chosen store name into its matching ID from the STORES table
    store_id = get_store_id(prefstore_name)
    if store_id is None:
        return render_template('signin.html', warning=None, register_warning="Please select a valid store.", show_register=True)

    # Convert the chosen gender name into its matching ID from the GENDER table
    gender_id = get_gender_id(gender_name)
    if gender_id is None:
        return render_template('signin.html', warning=None, register_warning="Please select a valid gender.", show_register=True)

    # Hash the password before storing it
    hashed = hash_password(password)

    # Insert the new customer, storing the looked-up IDs rather than the raw text
    db = get_db()
    db.execute(
        "INSERT INTO CUSTOMER (firstname, lastname, email, ph_number, password, pref_store, gender) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (firstname, lastname, email, phonenumber, hashed, store_id, gender_id)
    )
    db.commit()

    # Log the new user in immediately and send them home
    session['user'] = email
    return redirect('/')

# Account details Page (Only avaliable if the user is logged in)
@app.route('/account')
def account_details():
    if 'user' not in session:
        return redirect('/signin')
    email = session['user']
    # Joins the customer's store and gender IDs against their name tables
    query = """
        SELECT CUSTOMER.ID, CUSTOMER.firstname, CUSTOMER.lastname, CUSTOMER.ph_number,
               CUSTOMER.email, STORES.name, GENDER.name
        FROM CUSTOMER
        LEFT JOIN STORES ON CUSTOMER.pref_store = STORES.ID
        LEFT JOIN GENDER ON CUSTOMER.gender = GENDER.ID
        WHERE CUSTOMER.email = ?
    """
    customer_info = query_db(query, (email,), one=True)
    return render_template("account.html", customer=customer_info)

# Logs the user out and sends them back to the home page
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Starts up the website server
if __name__ == "__main__":
    migrate_passwords()
    app.run(debug=True)