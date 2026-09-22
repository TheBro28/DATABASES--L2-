# Import the tools needed to build the website and handle data
from flask import Flask, g, render_template, request, redirect, session, url_for, Blueprint, flash
import sqlite3, hashlib

# Defines the database as a constant
DATABASE = 'subvay.db'

# Create and set up the website application
app = Flask(__name__, static_folder='Static')
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

# --- CUSTOM SANDWICH BUILDER --- #

# Works out the running total for whatever is currently stored in the session
def calculate_custom_sandwich_price(selection):
    total = 0.0

    # Adds the price of the chosen bread, if one has been picked yet
    if selection.get('bread'):
        bread_row = query_db("SELECT price FROM BREAD WHERE ID = ?", (selection['bread'],), one=True)
        if bread_row:
            total += bread_row[0]

    # Adds the price of the chosen cheese, if one has been picked yet
    if selection.get('cheese'):
        cheese_row = query_db("SELECT price FROM CHEESE WHERE ID = ?", (selection['cheese'],), one=True)
        if cheese_row:
            total += cheese_row[0]

    # Adds the price of every chosen sauce
    for sauce_id in selection.get('sauces', []):
        sauce_row = query_db("SELECT price FROM SAUCE WHERE ID = ?", (sauce_id,), one=True)
        if sauce_row:
            total += sauce_row[0]

    # Adds the price of every chosen topping
    for topping_id in selection.get('toppings', []):
        topping_row = query_db("SELECT price FROM TOPPINGS WHERE ID = ?", (topping_id,), one=True)
        if topping_row:
            total += topping_row[0]

    return total

# Custom sandwich builder page
@app.route('/custom-sandwich')
def custom_sandwich():
    # Pulls every available bread and cheese, including their descriptions, to fill the option lists
    breads = query_db("SELECT ID, name, description, price FROM BREAD")
    cheeses = query_db("SELECT ID, name, description, price FROM CHEESE")
    # Selects sauces and toppings name and price
    sauces = query_db("SELECT ID, name, price FROM SAUCE")
    toppings = query_db("SELECT ID, name, price FROM TOPPINGS")

    # ID-to-price lookup dictionaries for price calculator in script.js
    bread_prices = {row[0]: row[3] for row in breads}
    cheese_prices = {row[0]: row[3] for row in cheeses}
    sauce_prices = {row[0]: row[2] for row in sauces}
    topping_prices = {row[0]: row[2] for row in toppings}

    # Reads back whatever the customer has picked so far this session - never touches the database
    selection = session.get('custom_sandwich', {'bread': None, 'cheese': None, 'sauces': [], 'toppings': []})
    total_price = calculate_custom_sandwich_price(selection)

    return render_template(
        "custom_sandwich.html",
        breads=breads,
        cheeses=cheeses,
        sauces=sauces,
        toppings=toppings,
        bread_prices=bread_prices,
        cheese_prices=cheese_prices,
        sauce_prices=sauce_prices,
        topping_prices=topping_prices,
        selected_bread=selection.get('bread'),
        selected_cheese=selection.get('cheese'),
        selected_sauces=selection.get('sauces', []),
        selected_toppings=selection.get('toppings', []),
        total_price=total_price
    )

# Saves the customer's current choices into the session
@app.post('/custom-sandwich/update')
def update_custom_sandwich():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    # Overwrites the in-progress build in the session (Doesn't touch the database at all until the customer finalises the order)
    session['custom_sandwich'] = {
        'bread': bread_id,
        'cheese': cheese_id,
        'sauces': sauce_ids,
        'toppings': topping_ids
    }

    # Used every time a choice is made, no reload is needed
    return {'status': 'saved'}

# Wipes the in-progress sandwich out of the session, discarding it completely and sends the user back to the menu page
@app.post('/custom-sandwich/cancel')
def cancel_custom_sandwich():
    session.pop('custom_sandwich', None)
    return redirect(url_for('menu'))

# --- SESSION CART MANAGEMENT --- #

@app.post('/custom-sandwich/save-progress')
def save_custom_progress():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    session['custom_sandwich'] = {
        'bread': bread_id,
        'cheese': cheese_id,
        'sauces': sauce_ids,
        'toppings': topping_ids
    }
    return {'status': 'saved'}


@app.route('/add-premade-to-session/<int:item_id>')
def add_premade_to_session(item_id):
    if 'premade_cart' not in session:
        session['premade_cart'] = {}
        
    item_id_str = str(item_id)
    sandwich = query_db("SELECT name FROM PRE_SANDWICH WHERE ID = ?", (item_id,), one=True)
    if not sandwich:
        return "Sandwich not found", 404
        
    cart = session['premade_cart']
    cart[item_id_str] = cart.get(item_id_str, 0) + 1
    session['premade_cart'] = cart
    
    flash(f'{sandwich[0]} added to your order!')
    return redirect(request.referrer or '/menu')


@app.post('/add-custom-to-session')
def add_custom_to_session():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    if not bread_id or not cheese_id:
        flash("Please select both a bread and a cheese first!")
        return redirect(url_for('custom_sandwich'))

    if 'custom_cart' not in session:
        session['custom_cart'] = []

    new_sub_blueprint = {
        'bread': bread_id,
        'cheese': cheese_id,
        'sauces': sorted(sauce_ids),
        'toppings': sorted(topping_ids)
    }

    cart = session['custom_cart']
    
    # Check if custom sandwich already exists in the cart
    match_found = False
    for item in cart:
        # Compare to see if it matches the new sandwich (ignoring quantity)
        item_blueprint = {k: item[k] for k in item if k != 'quantity'}
        if item_blueprint == new_sub_blueprint:
            item['quantity'] = item.get('quantity', 1) + 1
            match_found = True
            break

    if not match_found:
        # Add new custom sandwich to the cart with a quantity of 1
        new_sub_blueprint['quantity'] = 1
        cart.append(new_sub_blueprint)

    session['custom_cart'] = cart
    session.pop('custom_sandwich', None)

    flash("Your custom sandwich has been added to the cart!")
    return redirect(url_for('menu'))


# --- CHECKOUT PAGE --- #

@app.route('/checkout')
def checkout():
    checkout_items = []
    grand_total = 0.0

    premade_cart = session.get('premade_cart', {})
    for item_id_str, quantity in premade_cart.items():
        sandwich = query_db("SELECT name, price FROM PRE_SANDWICH WHERE ID = ?", (int(item_id_str),), one=True)
        if sandwich:
            name, price = sandwich
            subtotal = price * quantity
            grand_total += subtotal
            checkout_items.append({
                'id': item_id_str,
                'name': name,
                'type': 'Pre-made Sub',
                'is_premade': True,
                'quantity': quantity,
                'price': price,
                'subtotal': subtotal
            })

    custom_cart = session.get('custom_cart', [])
    for index, custom in enumerate(custom_cart):
        single_unit_price = calculate_custom_sandwich_price(custom)
        qty = custom.get('quantity', 1)
        
        subtotal = single_unit_price * qty
        grand_total += subtotal
        
        bread_row = query_db("SELECT name FROM BREAD WHERE ID = ?", (custom['bread'],), one=True)
        cheese_row = query_db("SELECT name FROM CHEESE WHERE ID = ?", (custom['cheese'],), one=True)
        
        b_name = bread_row if bread_row else "Unknown Bread"
        c_name = cheese_row if cheese_row else "Unknown Cheese"
        description = f"Bread: {b_name}, Cheese: {c_name}"
        
        checkout_items.append({
            'cart_index': int(index),
            'name': f'Custom Sub #{index + 1}',
            'type': description,
            'is_premade': False,
            'quantity': qty,
            'price': single_unit_price,
            'subtotal': subtotal
        })

    return render_template("checkout.html", items=checkout_items, grand_total=grand_total)

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

# Error handling for 404 page not found
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# --- CHECKOUT ROUTES --- #

# Updates the number of pre-made subs in the cart or deletes them if set to 0
@app.post('/cart/update-quantity/<string:item_id>')
def update_cart_quantity(item_id):
    # Reads the number chosen in dropdown
    quantity = request.form.get('quantity', type=int)
    
    if 'premade_cart' in session:
        cart = session['premade_cart']
        # If the quantity is 1 or more, update the cart, otherwise remove the item
        if quantity and quantity > 0:
            cart[item_id] = quantity
        else:
            cart.pop(item_id, None)
        session['premade_cart'] = cart
        
    return redirect(url_for('checkout'))

@app.post('/cart/update-custom-quantity/<int:index>')
def update_custom_quantity(index):
    quantity = request.form.get('quantity', type=int)
    
    if 'custom_cart' in session:
        cart = session['custom_cart']
        if 0 <= index < len(cart):
            if quantity and quantity > 0:
                cart[index]['quantity'] = quantity
            else:
                cart.pop(index)
            session['custom_cart'] = cart
            
    return redirect(url_for('checkout'))

# Deletes a pre-made sandwich from the cart
@app.route('/cart/delete-premade/<string:item_id>')
def delete_premade_item(item_id):
    if 'premade_cart' in session:
        cart = session['premade_cart']
        cart.pop(item_id, None)
        session['premade_cart'] = cart
        flash("Pre-made sub removed.")
        
    return redirect(url_for('checkout'))


# Deletes a custom sandwich from the cart
@app.route('/cart/delete-custom/<int:index>')
def delete_custom_item(index):
    if 'custom_cart' in session:
        cart = session['custom_cart']
        # Prevents python from crashing if the index is out of range
        idx = int(index)
        if 0 <= idx < len(cart):
            cart.pop(idx)
            session['custom_cart'] = cart
            flash("Custom sub removed.")
            
    return redirect(url_for('checkout'))


    # NOT COMPLETED TO BE CONTINUED

# --- THANK YOU, ORDER COMPLETION, & DATABASE COMMIT --- #
"""
@app.route('/checkout/thanks')
def purchase_thanks():
    # Make sure the user is logged in before processing the order
    email = session.get('user')
    if not email:
        flash("You must be logged in to complete a purchase!")
        return redirect(url_for('signin'))

    premade_cart = session.get('premade_cart', {})
    custom_cart = session.get('custom_cart', [])

    # Make sure the cart isn't empty 
    if not premade_cart and not custom_cart:
        flash("Your cart is empty.")
        return redirect(url_for('menu'))

    db = get_db()

    try:
        # Look up customer ID based on the logged-in email
        customer_row = query_db("SELECT ID FROM CUSTOMER WHERE email = ?", (email,), one=True)
        if not customer_row:
            flash("User account not found.")
            return redirect(url_for('signin'))
        customer_id = customer_row[0]

        # Calculate the grand total for the order
        grand_total = 0.0
        
        for item_id_str, quantity in premade_cart.items():
            price_row = query_db("SELECT price FROM PRE_SANDWICH WHERE ID = ?", (int(item_id_str),), one=True)
            if price_row:
                grand_total += price_row[0] * quantity

        for custom in custom_cart:
            single_unit_price = calculate_custom_sandwich_price(custom)
            qty = custom.get('quantity', 1)
            grand_total += single_unit_price * qty

    return render_template("thanks.html")
"""
# Starts up the website server
if __name__ == "__main__":
    migrate_passwords()
    app.run(debug=True)