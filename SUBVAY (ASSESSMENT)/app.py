# Import the tools needed to build the website and handle data
from flask import Flask, g, render_template, request, redirect, session, url_for, Blueprint, flash
import sqlite3, hashlib
from datetime import datetime, timedelta

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

# Looks up today's offer row and sandwich details - shared by the sotd page and the add-to-cart route
def get_todays_offer():
    # isoweekday() returns 1 for Monday through 7 for Sunday, matching Offer ID 1-7
    today_number = datetime.now().isoweekday()

    offer = query_db(
        """
        SELECT PRE_SANDWICH.ID, PRE_SANDWICH.name, PRE_SANDWICH.ingredients, PRE_SANDWICH.image_url,
               PRE_SANDWICH.price, OFFERS.discounted_price
        FROM OFFERS
        LEFT JOIN PRE_SANDWICH ON OFFERS.pre_sandwich_ID = PRE_SANDWICH.ID
        WHERE OFFERS.ID = ?
        """,
        (today_number,), one=True
    )
    return offer, today_number

# Sub of the Day page - shows whichever OFFERS row matches today's day of the week
@app.route('/sotd')
def sotd():
    offer, today_number = get_todays_offer()

    # Works out today's name to show on the page
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today_name = day_names[today_number - 1]

    return render_template("sotd.html", offer=offer, today_name=today_name)

# Adds today's Sub of the Day to the cart at its discounted price (discounted price only on the sotd page, not the menu page)
@app.route('/sotd/add-to-cart')
def add_sotd_to_cart():
    offer, today_number = get_todays_offer()

    if not offer:
        flash("No offer is available today.")
        return redirect(url_for('sotd'))

    sandwich_id, name, ingredients, image_url, normal_price, discount_amount = offer
    # discounted_price is the amount taken OFF the normal price
    sale_price = normal_price - discount_amount
    item_id_str = str(sandwich_id)

    # Creates an empty Sub of the Day cart in the session if one doesn't exist yet
    if 'sotd_cart' not in session:
        session['sotd_cart'] = {}

    cart = session['sotd_cart']
    current = cart.get(item_id_str, {'quantity': 0, 'unit_price': sale_price})

    # Stops the quantity going past the 99 cap
    if current['quantity'] >= 99:
        flash(f'Maximum number of {name} in cart', 'error')
        return redirect(url_for('sotd'))

    # Increases the quantity and refreshes the stored sale price, in case the offer price has changed
    current['quantity'] += 1
    current['unit_price'] = sale_price
    cart[item_id_str] = current
    session['sotd_cart'] = cart

    flash(f'{name} (Sub of the Day) added to your order!')
    return redirect(url_for('sotd'))

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

# Auto-saves the in-progress custom sandwich to the session (same as update_custom_sandwich, called periodically)
@app.post('/custom-sandwich/save-progress')
def save_custom_progress():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    # Overwrites the in-progress build in the session
    session['custom_sandwich'] = {
        'bread': bread_id,
        'cheese': cheese_id,
        'sauces': sauce_ids,
        'toppings': topping_ids
    }
    return {'status': 'saved'}


# Adds a pre-made sandwich to the cart, or increases its quantity if it's already there
@app.route('/add-premade-to-session/<int:item_id>')
def add_premade_to_session(item_id):
    # Creates an empty pre-made cart in the session if one doesn't exist yet
    if 'premade_cart' not in session:
        session['premade_cart'] = {}
        
    item_id_str = str(item_id)
    # Looks up the sandwich's name so it can be confirmed and shown in the flash message
    sandwich = query_db("SELECT name FROM PRE_SANDWICH WHERE ID = ?", (item_id,), one=True)
    if not sandwich:
        return "Sandwich not found", 404

    cart = session['premade_cart']
    current_qty = cart.get(item_id_str, 0)

    # Stops the quantity going past the cap of 99 and shows an error message if the customer tries to add more
    if current_qty >= 99:
        flash(f'Maximum number of {sandwich[0]} in cart', 'error')
        return redirect(request.referrer or '/menu')

    # Increases the quantity by 1
    cart[item_id_str] = current_qty + 1
    session['premade_cart'] = cart
    
    # Lets the customer know it was added, then sends them back to whichever page they came from
    flash(f'{sandwich[0]} added to your order!')
    return redirect(request.referrer or '/menu')


# Adds the in-progress custom sandwich to the cart, merging it with a matching one if it already exists
@app.post('/add-custom-to-session')
def add_custom_to_session():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    # A bread and cheese must be chosen before the sandwich can be added
    if not bread_id or not cheese_id:
        flash("Please select both a bread and a cheese first!")
        return redirect(url_for('custom_sandwich'))

    # Creates an empty custom cart in the session if one doesn't exist yet
    if 'custom_cart' not in session:
        session['custom_cart'] = []

    # Sorts the sauces/toppings so the sandwich can be compared to existing cart items regardless of pick order
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
    # Clears the in-progress builder now that it's been moved into the cart
    session.pop('custom_sandwich', None)

    flash("Your custom sandwich has been added to the cart!")
    return redirect(url_for('menu'))


# --- CHECKOUT PAGE --- #

# Builds the full list of cart items (pre-made, custom, and Sub of the Day) with prices, ready for the checkout page
@app.route('/checkout')
def checkout():
    checkout_items = []
    grand_total = 0.0

    # Adds every pre-made sandwich in the cart, working out its subtotal and adding it to the grand total
    premade_cart = session.get('premade_cart', {})
    for item_id_str, quantity in premade_cart.items():
        # Shows each sandwich's ingredients list
        sandwich = query_db("SELECT name, ingredients, price FROM PRE_SANDWICH WHERE ID = ?", (int(item_id_str),), one=True)
        if sandwich:
            name, ingredients, price = sandwich
            subtotal = price * quantity
            grand_total += subtotal
            checkout_items.append({
                'id': item_id_str,
                'name': name,
                'description': ingredients,
                'is_premade': True,
                'is_sotd': False,
                'quantity': quantity,
                'price': price,
                'subtotal': subtotal
            })

    # Adds every Sub of the Day item at the discounted price, working out its subtotal and adding it to the grand total
    sotd_cart = session.get('sotd_cart', {})
    for item_id_str, data in sotd_cart.items():
        quantity = data['quantity']
        unit_price = data['unit_price']

        sandwich = query_db("SELECT name, ingredients, price FROM PRE_SANDWICH WHERE ID = ?", (int(item_id_str),), one=True)
        if sandwich:
            name, ingredients, normal_price = sandwich
            subtotal = unit_price * quantity
            grand_total += subtotal
            checkout_items.append({
                'id': item_id_str,
                'name': f'{name} (Sub of the Day)',
                'description': ingredients,
                'is_premade': False,
                'is_sotd': True,
                'original_price': normal_price,
                'quantity': quantity,
                'price': unit_price,
                'subtotal': subtotal
            })

    # Adds every custom sandwich in the cart, working out its subtotal and adding it to the grand total
    custom_cart = session.get('custom_cart', [])
    for index, custom in enumerate(custom_cart):
        single_unit_price = calculate_custom_sandwich_price(custom)
        qty = custom.get('quantity', 1)

        subtotal = single_unit_price * qty
        grand_total += subtotal

        # Looks up the bread, cheese, sauce, and topping names so the checkout page can show a ingredient list
        bread_row = query_db("SELECT name FROM BREAD WHERE ID = ?", (custom['bread'],), one=True)
        cheese_row = query_db("SELECT name FROM CHEESE WHERE ID = ?", (custom['cheese'],), one=True)

        sauce_names = []
        for sauce_id in custom.get('sauces', []):
            sauce_row = query_db("SELECT name FROM SAUCE WHERE ID = ?", (sauce_id,), one=True)
            if sauce_row:
                sauce_names.append(sauce_row[0])

        topping_names = []
        for topping_id in custom.get('toppings', []):
            topping_row = query_db("SELECT name FROM TOPPINGS WHERE ID = ?", (topping_id,), one=True)
            if topping_row:
                topping_names.append(topping_row[0])

        # Builds a plain comma-separated ingredient list, matching the style of a pre-made sandwich's ingredients
        ingredient_list = []
        if bread_row:
            ingredient_list.append(bread_row[0])
        if cheese_row:
            ingredient_list.append(cheese_row[0])
        ingredient_list.extend(topping_names)
        ingredient_list.extend(sauce_names)
        description = ", ".join(ingredient_list)

        checkout_items.append({
            'cart_index': int(index),
            'name': 'Custom Sandwich',
            'description': description,
            'is_premade': False,
            'is_sotd': False,
            'quantity': qty,
            'price': single_unit_price,
            'subtotal': subtotal
        })

    # Pulls the list of all stores to fill the dropdown on the checkout page
    all_stores = query_db("SELECT ID, name FROM STORES")

    # Defaults the selected store to the logged-in customer's saved preferred store, the first time the page is visited this session
    if 'selected_store_id' not in session:
        email = session.get('user')
        if email:
            pref_row = query_db(
                "SELECT STORES.ID FROM CUSTOMER LEFT JOIN STORES ON CUSTOMER.pref_store = STORES.ID WHERE CUSTOMER.email = ?",
                (email,), one=True
            )
            if pref_row and pref_row[0]:
                session['selected_store_id'] = pref_row[0]

    selected_store_id = session.get('selected_store_id')

    # Defaults the pickup time to 15 minutes from now if the customer hasn't chosen one yet
    # Stored in the session so it carries over if the customer leaves and comes back to the checkout page
    if 'pickup_time_value' not in session:
        default_dt = datetime.now() + timedelta(minutes=15)
        session['pickup_time_value'] = default_dt.strftime('%H:%M')
        session['pickup_time_display'] = default_dt.strftime('%I:%M%p').lstrip('0').lower()

    # Finds pre-made sandwiches not already in the cart, for the "Hungry for more?" section
    cart_ids_in_use = set()
    for item_id_str in premade_cart.keys():
        cart_ids_in_use.add(int(item_id_str))

    # Shows each sandwich's ingredients
    all_premade = query_db("SELECT ID, name, ingredients, price FROM PRE_SANDWICH")
    hungry_for_more = []
    for s in all_premade:
        # Skips anything already sitting in the cart
        if s[0] in cart_ids_in_use:
            continue
        # Never shows the "Megatronus Heart Disease" sandwich as its too much to add with other items
        if s[1] == 'Megatronus Heart Disease':
            continue
        hungry_for_more.append(s)
        # Only ever shows 5 sandwiches at a time
        if len(hungry_for_more) == 5:
            break

    return render_template(
        "checkout.html",
        items=checkout_items,
        grand_total=grand_total,
        all_stores=all_stores,
        selected_store_id=selected_store_id,
        pickup_time_value=session.get('pickup_time_value'),
        hungry_for_more=hungry_for_more
    )

# Updates which store the order will be collected from
@app.post('/checkout/set-store')
def set_checkout_store():
    store_id = request.form.get('store_id', type=int)
    if store_id:
        session['selected_store_id'] = store_id
    return redirect(url_for('checkout'))

# Updates the pickup time, only allowing a time at least 10 minutes from right now
@app.post('/checkout/set-time')
def set_checkout_time():
    time_str = request.form.get('pickup_time')

    try:
        hour, minute = map(int, time_str.split(':'))
        chosen_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, AttributeError, TypeError):
        flash("Please choose a valid time.")
        return redirect(url_for('checkout'))

    # Rejects any time less than 10 minutes away from right now
    if chosen_dt < datetime.now() + timedelta(minutes=10):
        flash("Please choose a pickup time at least 10 minutes from now.")
        return redirect(url_for('checkout'))

    # Stores the chosen time in the session in two formats: one for the input box, one for display on screen
    session['pickup_time_value'] = f"{hour:02d}:{minute:02d}"
    session['pickup_time_display'] = chosen_dt.strftime('%I:%M%p').lstrip('0').lower()
    return redirect(url_for('checkout'))

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
    # Reads the number typed or set via the +/- buttons
    quantity = request.form.get('quantity', type=int)

    # Keeps the quantity within the 1-99 range the input allows
    if quantity is not None:
        quantity = max(1, min(quantity, 99))

    if 'premade_cart' in session:
        cart = session['premade_cart']
        # If the quantity is 1 or more, update the cart, otherwise remove the item
        if quantity and quantity > 0:
            cart[item_id] = quantity
        else:
            cart.pop(item_id, None)
        session['premade_cart'] = cart
        
    return redirect(url_for('checkout'))

# Updates the number of a Sub of the Day item in the cart or deletes it if set to 0, keeping its discounted price
@app.post('/cart/update-sotd-quantity/<string:item_id>')
def update_sotd_quantity(item_id):
    # Reads the number typed or set via the +/- buttons
    quantity = request.form.get('quantity', type=int)

    # Keeps the quantity within the 1-99 range the input allows
    if quantity is not None:
        quantity = max(1, min(quantity, 99))

    if 'sotd_cart' in session:
        cart = session['sotd_cart']
        if item_id in cart:
            # If the quantity is 1 or more, update the cart, otherwise remove the item
            if quantity and quantity > 0:
                cart[item_id]['quantity'] = quantity
            else:
                cart.pop(item_id, None)
            session['sotd_cart'] = cart

    return redirect(url_for('checkout'))

# Updates the number of a custom sub in the cart or deletes it if set to 0
@app.post('/cart/update-custom-quantity/<int:index>')
def update_custom_quantity(index):
    # Reads the number typed or set via the +/- buttons
    quantity = request.form.get('quantity', type=int)

    # Keeps the quantity within the 1-99 range the input allows
    if quantity is not None:
        quantity = max(1, min(quantity, 99))

    if 'custom_cart' in session:
        cart = session['custom_cart']
        # Makes sure the index actually exists in the cart before changing anything
        if 0 <= index < len(cart):
            # If the quantity is 1 or more, update the cart, otherwise remove the item
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

# Deletes a Sub of the Day item from the cart
@app.route('/cart/delete-sotd/<string:item_id>')
def delete_sotd_item(item_id):
    if 'sotd_cart' in session:
        cart = session['sotd_cart']
        cart.pop(item_id, None)
        session['sotd_cart'] = cart
        flash("Sub of the Day item removed.")

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

# --- THANK YOU, ORDER COMPLETION, & DATABASE COMMIT --- #

@app.route('/checkout/thanks')
def purchase_thanks():
    # Make sure the user is logged in before processing the order
    email = session.get('user')
    if not email:
        flash("You must be logged in to complete a purchase!")
        return redirect(url_for('signin'))

    premade_cart = session.get('premade_cart', {})
    sotd_cart = session.get('sotd_cart', {})
    custom_cart = session.get('custom_cart', [])

    # The pickup time the customer chose on the checkout page, e.g. "14:35"
    pickup_time = session.get('pickup_time_value')

    # Make sure the cart isn't empty
    if not premade_cart and not sotd_cart and not custom_cart:
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

        # Sub of the Day items use their stored discounted unit price, not the sandwich's normal price
        for item_id_str, data in sotd_cart.items():
            grand_total += data['unit_price'] * data['quantity']

        for custom in custom_cart:
            single_unit_price = calculate_custom_sandwich_price(custom)
            qty = custom.get('quantity', 1)
            grand_total += single_unit_price * qty

        # Insert order information into the ORDERS table and get the new order ID
        cursor = db.execute(
            """
            INSERT INTO ORDERS (customer_ID, order_ts, total_amount, pickup_time)
            VALUES (?, datetime('now', 'localtime'), ?, ?)
            """,
            (customer_id, grand_total, pickup_time)
        )
        # This is ORDERS.ID (shown to customers as their order number)
        new_order_id = cursor.lastrowid

        # Insert each pre-made sandwich into the ORDER_ITEMS table
        for item_id_str, quantity in premade_cart.items():
            pre_id = int(item_id_str)
            price_row = query_db("SELECT price FROM PRE_SANDWICH WHERE ID = ?", (pre_id,), one=True)
            if price_row:
                actual_price = price_row[0]
                db.execute(
                    """
                    INSERT INTO ORDER_ITEMS (order_ID, pre_sandwich_ID, cus_sandwich_ID, quantity, final_price)
                    VALUES (?, ?, NULL, ?, ?)
                    """,
                    (new_order_id, pre_id, quantity, actual_price * quantity)
                )

        # Insert each Sub of the Day sandwich into the ORDER_ITEMS table using its discounted unit price
        for item_id_str, data in sotd_cart.items():
            pre_id = int(item_id_str)
            quantity = data['quantity']
            unit_price = data['unit_price']
            db.execute(
                """
                INSERT INTO ORDER_ITEMS (order_ID, pre_sandwich_ID, cus_sandwich_ID, quantity, final_price)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (new_order_id, pre_id, quantity, unit_price * quantity)
            )

        # Insert each custom sandwich into the ORDER_ITEMS table with its sauces and toppings
        for custom in custom_cart:
            qty = custom.get('quantity', 1)
            single_unit_price = calculate_custom_sandwich_price(custom)
            total_custom_price = single_unit_price * qty
           
            # Insert the custom sandwich into the CUS_SANDWICH table and get its new ID
            cus_cursor = db.execute(
                "INSERT INTO CUS_SANDWICH (bread_ID, cheese_ID) VALUES (?, ?)",
                (custom['bread'], custom['cheese'])
            )
            new_custom_sandwich_id = cus_cursor.lastrowid
           
            # Insert the selected sauces into the CUS_SANDWICH_SAUCES table
            for sauce_id in custom.get('sauces', []):
                db.execute(
                    "INSERT INTO CUS_SANDWICH_SAUCES (cus_sandwich_ID, sauce_ID) VALUES (?, ?)",
                    (new_custom_sandwich_id, sauce_id)
                )
               
            # Insert the selected toppings into the CUS_SANDWICH_TOPPINGS table
            for topping_id in custom.get('toppings', []):
                db.execute(
                    "INSERT INTO CUS_SANDWICH_TOPPINGS (cus_sandwich_ID, topping_ID) VALUES (?, ?)",
                    (new_custom_sandwich_id, topping_id)
                )

            # Insert the custom sandwich into the ORDER_ITEMS table
            db.execute(
                """
                INSERT INTO ORDER_ITEMS (order_ID, pre_sandwich_ID, cus_sandwich_ID, quantity, final_price)
                VALUES (?, NULL, ?, ?, ?)
                """,
                (new_order_id, new_custom_sandwich_id, qty, total_custom_price)
            )

        # Commit all changes to the database
        db.commit()

        # Clear the session carts after a successful order
        session.pop('premade_cart', None)
        session.pop('sotd_cart', None)
        session.pop('custom_cart', None)
        # Clears the store/time choices too, so the next order starts fresh
        session.pop('selected_store_id', None)
        session.pop('pickup_time_value', None)
        session.pop('pickup_time_display', None)

        # Look up the customer's preferred store, this is where the order is picked up from
        store_row = query_db(
            "SELECT STORES.name FROM CUSTOMER LEFT JOIN STORES ON CUSTOMER.pref_store = STORES.ID WHERE CUSTOMER.ID = ?",
            (customer_id,),
            one=True
        )
        # Generic message if the customer has no preferred store saved
        store_name = store_row[0] if store_row and store_row[0] else "your preferred store"

    except sqlite3.Error as e:
        print(f"Database transaction failure: {e}")
        return "An internal error occurred saving your transaction.", 500

    # Show the confirmation page with the store the order will be picked up from
    return render_template("thanks.html", store_name=store_name, order_id=new_order_id)

# Starts up the website server
if __name__ == "__main__":
    migrate_passwords()
    app.run(debug=True)