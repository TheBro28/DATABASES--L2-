# Import the tools needed to build the website and handle data
from flask import Flask, g, render_template, request, redirect, session, url_for, Blueprint, flash
import sqlite3, hashlib
from datetime import datetime, timedelta

# The name of the database file
DATABASE = 'subvay.db'

# Creates the website application
app = Flask(__name__, static_folder='Static')
# A secret code Flask uses to keep login sessions safe
app.secret_key = '4a9f83b21cde567890abcdef1234567890abcdef12345678' 

# Opens a connection to the database, reusing the same one for this page load
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# Closes the database connection once the page has finished loading
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# A shortcut for running a database search and getting the results back
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# Turns a password into a scrambled code so it's never stored as plain text
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Goes through every customer and makes sure their password is scrambled (not plain text)
def migrate_passwords():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    # Gets every customer's ID and current password
    cursor.execute("SELECT ID, password FROM CUSTOMER")
    users = cursor.fetchall()
    
    # Checks each customer one at a time
    for user_id, password in users:
        # A scrambled password is always 64 characters long - if it isn't, it's still plain text
        if len(password) != 64:
            # Scrambles the plain text password
            hashed = hash_password(password)
            # Saves the scrambled password over the old plain text one
            cursor.execute("UPDATE CUSTOMER SET password = ? WHERE ID = ?", (hashed, user_id))
            
    # Saves all the changes
    db.commit()
    db.close()


# Runs automatically before every page, so every page knows if someone is logged in
@app.context_processor
def inject_user_name():
    # Sees if an email is saved for the current visitor
    email = session.get('user')
    
    # If someone is logged in, finds their first name
    if email:
        query = "SELECT firstname FROM CUSTOMER WHERE email = ?"
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        db.close()
        
        # Gives the page the customer's first name to display
        if result:
            return dict(user_name=result[0])
            
    # If nobody is logged in, gives the page nothing, so it shows "Sign In" instead
    return dict(user_name=None)


# --- PAGE LINKS (ROUTES) --- #

# Home page
@app.route('/')
def home():
    return render_template("index.html") 

# Offers page
@app.route('/offers')
def offers():
    return render_template("offers.html")

# Works out which sandwich is today's special offer, and its price
def get_todays_offer():
    # Gets today's day number: Monday is 1, all the way to Sunday which is 7
    today_number = datetime.now().isoweekday()

    # Finds the sandwich linked to today's offer, with its name, ingredients, image, and both prices
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

# Sub of the Day page - shows today's special sandwich
@app.route('/sotd')
def sotd():
    offer, today_number = get_todays_offer()

    # Turns today's day number into its name, e.g. 1 becomes "Monday"
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today_name = day_names[today_number - 1]

    return render_template("sotd.html", offer=offer, today_name=today_name)

# Adds today's special sandwich to the cart at its discounted price - the discount only applies here, not on the normal menu
@app.route('/sotd/add-to-cart')
def add_sotd_to_cart():
    offer, today_number = get_todays_offer()

    # Stops here if there's no offer set up for today
    if not offer:
        flash("No offer is available today.")
        return redirect(url_for('sotd'))

    sandwich_id, name, ingredients, image_url, normal_price, discount_amount = offer
    # The discount is an amount taken OFF the normal price, not the final price itself
    sale_price = normal_price - discount_amount
    item_id_str = str(sandwich_id)

    # Starts an empty Sub of the Day cart if the customer doesn't have one yet
    if 'sotd_cart' not in session:
        session['sotd_cart'] = {}

    cart = session['sotd_cart']
    current = cart.get(item_id_str, {'quantity': 0, 'unit_price': sale_price})

    # Stops the customer from adding more than 99 of the same sandwich
    if current['quantity'] >= 99:
        flash(f'Maximum number of {name} in cart', 'error')
        return redirect(url_for('sotd'))

    # Adds one more to the cart and saves today's sale price with it
    current['quantity'] += 1
    current['unit_price'] = sale_price
    cart[item_id_str] = current
    session['sotd_cart'] = cart

    flash(f'{name} (Sub of the Day) added to your order!')
    return redirect(url_for('sotd'))

# History page
@app.route('/history')
def history():
    return render_template("history.html")

# Sign in / Register page
@app.route('/signin')
def signin():
    return render_template("signin.html", warning=None, register_warning=None, show_register=False)

# --- SINGLE SANDWICH PAGE --- #

# Shows the details of one sandwich when it's clicked on
@app.route('/sandwich/<int:id>')
def sandwich(id):
    # Looks up the sandwich that matches the clicked ID
    query = "SELECT ID, name, description, image_url, price FROM PRE_SANDWICH WHERE ID = ?"
    sandwich = query_db(query, (id,), one=True)
    
    # Shows an error if that sandwich doesn't exist
    if sandwich is None:
        return "Sandwich not found", 404
        
    # Shows the sandwich's details
    return render_template("sandwich.html", sandwich=sandwich)

# --- MENU PAGE --- #

# Shows every sandwich on the menu
@app.route('/menu', methods=['GET'])
def menu():
    # Checks if someone is logged in
    user = session.get('user')
    
    # Opens the database
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    # Gets every sandwich's details
    query = "SELECT ID, name, description, image_url, price FROM PRE_SANDWICH"
    cursor.execute(query)
    all_sandwiches = cursor.fetchall()

    # Finds the cheapest bread and cheese, to show a starting price for building your own sandwich
    cheapest_bread = cursor.execute("SELECT MIN(price) FROM BREAD").fetchone()[0]
    cheapest_cheese = cursor.execute("SELECT MIN(price) FROM CHEESE").fetchone()[0]
    custom_starting_price = cheapest_bread + cheapest_cheese

    db.close()
        
    # Shows the menu page with all the sandwiches
    return render_template(
        'menu.html', 
        all_sandwiches=all_sandwiches, 
        user=user,
        custom_starting_price=custom_starting_price
    )

# --- BUILD YOUR OWN SANDWICH --- #

# Adds up the price of whatever the customer has picked so far
def calculate_custom_sandwich_price(selection):
    total = 0.0

    # Adds the bread's price, if one has been picked
    if selection.get('bread'):
        bread_row = query_db("SELECT price FROM BREAD WHERE ID = ?", (selection['bread'],), one=True)
        if bread_row:
            total += bread_row[0]

    # Adds the cheese's price, if one has been picked
    if selection.get('cheese'):
        cheese_row = query_db("SELECT price FROM CHEESE WHERE ID = ?", (selection['cheese'],), one=True)
        if cheese_row:
            total += cheese_row[0]

    # Adds the price of every sauce picked
    for sauce_id in selection.get('sauces', []):
        sauce_row = query_db("SELECT price FROM SAUCE WHERE ID = ?", (sauce_id,), one=True)
        if sauce_row:
            total += sauce_row[0]

    # Adds the price of every topping picked
    for topping_id in selection.get('toppings', []):
        topping_row = query_db("SELECT price FROM TOPPINGS WHERE ID = ?", (topping_id,), one=True)
        if topping_row:
            total += topping_row[0]

    return total

# The "Build Your Own Sandwich" page
@app.route('/custom-sandwich')
def custom_sandwich():
    # Gets every bread and cheese option, with their descriptions
    breads = query_db("SELECT ID, name, description, price FROM BREAD")
    cheeses = query_db("SELECT ID, name, description, price FROM CHEESE")
    # Gets every sauce and topping option
    sauces = query_db("SELECT ID, name, price FROM SAUCE")
    toppings = query_db("SELECT ID, name, price FROM TOPPINGS")

    # Simple lookup lists, matching each option's ID to its price, for the price calculator on the page
    bread_prices = {row[0]: row[3] for row in breads}
    cheese_prices = {row[0]: row[3] for row in cheeses}
    sauce_prices = {row[0]: row[2] for row in sauces}
    topping_prices = {row[0]: row[2] for row in toppings}

    # Remembers whatever the customer has already picked this visit
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

# Remembers the customer's choices as they build their sandwich
@app.post('/custom-sandwich/update')
def update_custom_sandwich():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    # Saves what's picked so far - nothing is stored permanently until the sandwich is added to the cart
    session['custom_sandwich'] = {
        'bread': bread_id,
        'cheese': cheese_id,
        'sauces': sauce_ids,
        'toppings': topping_ids
    }

    # Lets the page update instantly without reloading
    return {'status': 'saved'}

# Clears the sandwich being built and sends the customer back to the menu
@app.post('/custom-sandwich/cancel')
def cancel_custom_sandwich():
    session.pop('custom_sandwich', None)
    return redirect(url_for('menu'))

# --- SAVING THE SHOPPING CART --- #

# Keeps saving the sandwich being built in the background, so nothing is lost
@app.post('/custom-sandwich/save-progress')
def save_custom_progress():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    # Saves what's picked so far
    session['custom_sandwich'] = {
        'bread': bread_id,
        'cheese': cheese_id,
        'sauces': sauce_ids,
        'toppings': topping_ids
    }
    return {'status': 'saved'}


# Adds a ready-made sandwich to the cart, or adds one more if it's already in there
@app.route('/add-premade-to-session/<int:item_id>')
def add_premade_to_session(item_id):
    # Starts an empty cart if the customer doesn't have one yet
    if 'premade_cart' not in session:
        session['premade_cart'] = {}
        
    item_id_str = str(item_id)
    # Finds the sandwich's name, so it can be shown in the confirmation message
    sandwich = query_db("SELECT name FROM PRE_SANDWICH WHERE ID = ?", (item_id,), one=True)
    if not sandwich:
        return "Sandwich not found", 404

    cart = session['premade_cart']
    current_qty = cart.get(item_id_str, 0)

    # Stops the customer adding more than 99 of the same sandwich
    if current_qty >= 99:
        flash(f'Maximum number of {sandwich[0]} in cart', 'error')
        return redirect(request.referrer or '/menu')

    # Adds one more to the cart
    cart[item_id_str] = current_qty + 1
    session['premade_cart'] = cart
    
    # Shows a confirmation message and sends the customer back to the page they came from
    flash(f'{sandwich[0]} added to your order!')
    return redirect(request.referrer or '/menu')


# Adds the sandwich just built to the cart - combines it with a matching one already there
@app.post('/add-custom-to-session')
def add_custom_to_session():
    bread_id = request.form.get('bread', type=int)
    cheese_id = request.form.get('cheese', type=int)
    sauce_ids = request.form.getlist('sauces', type=int)
    topping_ids = request.form.getlist('toppings', type=int)

    # A bread and a cheese must be picked before the sandwich can be added
    if not bread_id or not cheese_id:
        flash("Please select both a bread and a cheese first!")
        return redirect(url_for('custom_sandwich'))

    # Starts an empty custom sandwich cart if the customer doesn't have one yet
    if 'custom_cart' not in session:
        session['custom_cart'] = []

    # Sorts the sauces/toppings so two sandwiches with the same ingredients always match up, no matter the order they were picked in
    new_sub_blueprint = {
        'bread': bread_id,
        'cheese': cheese_id,
        'sauces': sorted(sauce_ids),
        'toppings': sorted(topping_ids)
    }

    cart = session['custom_cart']
    
    # Checks if this exact sandwich is already in the cart
    match_found = False
    for item in cart:
        # Compares everything except the quantity
        item_blueprint = {k: item[k] for k in item if k != 'quantity'}
        if item_blueprint == new_sub_blueprint:
            item['quantity'] = item.get('quantity', 1) + 1
            match_found = True
            break

    if not match_found:
        # Adds it as a brand new item in the cart
        new_sub_blueprint['quantity'] = 1
        cart.append(new_sub_blueprint)

    session['custom_cart'] = cart
    # Clears the sandwich builder now that it's safely in the cart
    session.pop('custom_sandwich', None)

    flash("Your custom sandwich has been added to the cart!")
    return redirect(url_for('menu'))


# --- CHECKOUT PAGE --- #

# Builds the full shopping cart list (ready-made, Sub of the Day, and custom sandwiches), ready to show on the checkout page
@app.route('/checkout')
def checkout():
    checkout_items = []
    grand_total = 0.0

    # Adds every ready-made sandwich in the cart, and works out its price
    premade_cart = session.get('premade_cart', {})
    for item_id_str, quantity in premade_cart.items():
        # Gets the sandwich's name, ingredients, and price
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

    # Adds every Sub of the Day sandwich in the cart, using the discounted price it was added at
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

    # Adds every custom sandwich in the cart, and works out its price
    custom_cart = session.get('custom_cart', [])
    for index, custom in enumerate(custom_cart):
        single_unit_price = calculate_custom_sandwich_price(custom)
        qty = custom.get('quantity', 1)

        subtotal = single_unit_price * qty
        grand_total += subtotal

        # Finds the names of the bread, cheese, sauces, and toppings, to show a simple ingredients list
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

        # Joins everything into one simple list, like "White Bread, Cheddar, Lettuce, Mayo"
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

    # Gets every store, to fill the pickup-location dropdown
    all_stores = query_db("SELECT ID, name FROM STORES")

    # The first time the checkout page is opened, picks the customer's saved favourite store automatically
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

    # The first time the checkout page is opened, sets a default pickup time of 15 minutes from now
    # This is remembered so it's still there if the customer leaves and comes back
    if 'pickup_time_value' not in session:
        default_dt = datetime.now() + timedelta(minutes=15)
        session['pickup_time_value'] = default_dt.strftime('%H:%M')
        session['pickup_time_display'] = default_dt.strftime('%I:%M%p').lstrip('0').lower()

    # Works out which sandwich IDs are already in the cart
    cart_ids_in_use = set()
    for item_id_str in premade_cart.keys():
        cart_ids_in_use.add(int(item_id_str))

    # Picks a few sandwiches the customer hasn't already added, for the "Hungry for more?" suggestions
    all_premade = query_db("SELECT ID, name, ingredients, price FROM PRE_SANDWICH")
    hungry_for_more = []
    for s in all_premade:
        # Skips anything already in the cart
        if s[0] in cart_ids_in_use:
            continue
        # This particular sandwich is never suggested here, it's too much to add alongside other items
        if s[1] == 'Megatronus Heart Disease':
            continue
        hungry_for_more.append(s)
        # Stops once 5 suggestions have been picked
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

# Saves which store the customer picked for collecting their order
@app.post('/checkout/set-store')
def set_checkout_store():
    store_id = request.form.get('store_id', type=int)
    if store_id:
        session['selected_store_id'] = store_id
    return redirect(url_for('checkout'))

# Saves the pickup time the customer picked, only if it's at least 10 minutes from now
@app.post('/checkout/set-time')
def set_checkout_time():
    time_str = request.form.get('pickup_time')

    try:
        hour, minute = map(int, time_str.split(':'))
        chosen_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, AttributeError, TypeError):
        flash("Please choose a valid time.")
        return redirect(url_for('checkout'))

    # Rejects a time that's too soon
    if chosen_dt < datetime.now() + timedelta(minutes=10):
        flash("Please choose a pickup time at least 10 minutes from now.")
        return redirect(url_for('checkout'))

    # Saves the time in two forms: one the time box understands, one for showing the customer nicely
    session['pickup_time_value'] = f"{hour:02d}:{minute:02d}"
    session['pickup_time_display'] = chosen_dt.strftime('%I:%M%p').lstrip('0').lower()
    return redirect(url_for('checkout'))

# --- LOGGING IN --- #

# Checks the customer's email and password when they click "Login"
@app.post('/get_login_data')
def handle_login_data():
    # Reads what was typed into the login form
    email = str(request.form['email'])
    password = str(request.form['password'])
    
    # Checks if the email and password are correct
    verify = verification(email, password)
    if verify:
        # Logs the customer in and sends them to the home page
        session['user'] = email
        return redirect('/')
    else:
        # Reloads the login page with a red error message
        return render_template('signin.html', warning=True, register_warning=None, show_register=False)

# Compares a typed-in password against the saved one
def verification(email, password):
    # Finds the saved password for this email
    query = "SELECT password FROM CUSTOMER WHERE email = ?"
    actual_password = query_db(query, (email,), one=True)
    
    # Checks if they match
    if actual_password:
        return hash_password(password) == actual_password[0]
    return False

# --- CREATING A NEW ACCOUNT --- #

# Finds a store's ID number from its name
def get_store_id(store_name):
    query = "SELECT ID FROM STORES WHERE name = ?"
    result = query_db(query, (store_name,), one=True)
    return result[0] if result else None

# Finds a gender's ID number from its name
def get_gender_id(gender_name):
    query = "SELECT ID FROM GENDER WHERE name = ?"
    result = query_db(query, (gender_name,), one=True)
    return result[0] if result else None

# Creates a new customer account from the registration form
@app.post('/handle_register_data')
def handle_register_data():
    # Reads everything typed into the registration form
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    email = request.form['email']
    phonenumber = request.form['phonenumber']
    password = request.form['password']
    confirm_password = request.form['conpassword']
    prefstore_name = request.form['prefstore']
    gender_name = request.form['gender']

    # Both passwords must match
    if password != confirm_password:
        return render_template('signin.html', warning=None, register_warning="Passwords do not match.", show_register=True)

    # Checks this email hasn't been used already
    existing = query_db("SELECT ID FROM CUSTOMER WHERE email = ?", (email,), one=True)
    if existing:
        return render_template('signin.html', warning=None, register_warning="An account with that email already exists.", show_register=True)

    # Turns the chosen store's name into its ID number
    store_id = get_store_id(prefstore_name)
    if store_id is None:
        return render_template('signin.html', warning=None, register_warning="Please select a valid store.", show_register=True)

    # Turns the chosen gender's name into its ID number
    gender_id = get_gender_id(gender_name)
    if gender_id is None:
        return render_template('signin.html', warning=None, register_warning="Please select a valid gender.", show_register=True)

    # Scrambles the password before saving it
    hashed = hash_password(password)

    # Saves the new customer in the database
    db = get_db()
    db.execute(
        "INSERT INTO CUSTOMER (firstname, lastname, email, ph_number, password, pref_store, gender) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (firstname, lastname, email, phonenumber, hashed, store_id, gender_id)
    )
    db.commit()

    # Logs the new customer in straight away and sends them home
    session['user'] = email
    return redirect('/')

# The account details page - only visible if someone is logged in
@app.route('/account')
def account_details():
    if 'user' not in session:
        return redirect('/signin')
    email = session['user']
    # Gets the customer's details, along with their store and gender's names
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

# Turns a 24-hour time like "14:35" into a friendly 12-hour time like "2:35pm"
def format_pickup_time(pickup_time):
    if not pickup_time:
        return None
    try:
        return datetime.strptime(pickup_time, '%H:%M').strftime('%I:%M%p').lstrip('0').lower()
    except ValueError:
        # If something odd was saved, just show it as-is rather than break the page
        return pickup_time

# Finds the customer's most recent order
def get_last_order(email):
    return query_db(
        """
        SELECT ORDERS.ID, ORDERS.total_amount, ORDERS.pickup_time, STORES.name
        FROM ORDERS
        JOIN CUSTOMER ON ORDERS.customer_ID = CUSTOMER.ID
        LEFT JOIN STORES ON CUSTOMER.pref_store = STORES.ID
        WHERE CUSTOMER.email = ?
        ORDER BY ORDERS.ID DESC
        LIMIT 1
        """,
        (email,), one=True
    )

# Shows the thank you page again for the customer's last order, linked from their account page
@app.route('/account/last-order')
def last_order():
    # Only works if the customer is logged in
    if 'user' not in session:
        return redirect('/signin')

    order = get_last_order(session['user'])

    # Lets the customer know if they've never placed an order
    if not order:
        flash("You haven't placed an order yet.")
        return redirect(url_for('account_details'))

    order_id, total_amount, pickup_time, store_name = order

    return render_template(
        "thanks.html",
        store_name=store_name if store_name else "your preferred store",
        order_id=order_id,
        pickup_display=format_pickup_time(pickup_time),
        total_amount=total_amount
    )

# Logs the customer out and sends them to the home page
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# Shows a friendly error page if someone visits a page that doesn't exist
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# --- CHANGING WHAT'S IN THE CART --- #

# Changes how many of a ready-made sandwich are in the cart, or removes it if set to 0
@app.post('/cart/update-quantity/<string:item_id>')
def update_cart_quantity(item_id):
    # Reads the new quantity typed in or set with the +/- buttons
    quantity = request.form.get('quantity', type=int)

    # Keeps the number between 1 and 99
    if quantity is not None:
        quantity = max(1, min(quantity, 99))

    if 'premade_cart' in session:
        cart = session['premade_cart']
        # Updates the quantity, or removes the item if it's been set to 0
        if quantity and quantity > 0:
            cart[item_id] = quantity
        else:
            cart.pop(item_id, None)
        session['premade_cart'] = cart
        
    return redirect(url_for('checkout'))

# Changes how many of a Sub of the Day sandwich are in the cart, keeping its discounted price
@app.post('/cart/update-sotd-quantity/<string:item_id>')
def update_sotd_quantity(item_id):
    # Reads the new quantity typed in or set with the +/- buttons
    quantity = request.form.get('quantity', type=int)

    # Keeps the number between 1 and 99
    if quantity is not None:
        quantity = max(1, min(quantity, 99))

    if 'sotd_cart' in session:
        cart = session['sotd_cart']
        if item_id in cart:
            # Updates the quantity, or removes the item if it's been set to 0
            if quantity and quantity > 0:
                cart[item_id]['quantity'] = quantity
            else:
                cart.pop(item_id, None)
            session['sotd_cart'] = cart

    return redirect(url_for('checkout'))

# Changes how many of a custom sandwich are in the cart, or removes it if set to 0
@app.post('/cart/update-custom-quantity/<int:index>')
def update_custom_quantity(index):
    # Reads the new quantity typed in or set with the +/- buttons
    quantity = request.form.get('quantity', type=int)

    # Keeps the number between 1 and 99
    if quantity is not None:
        quantity = max(1, min(quantity, 99))

    if 'custom_cart' in session:
        cart = session['custom_cart']
        # Makes sure this item actually exists before changing it
        if 0 <= index < len(cart):
            # Updates the quantity, or removes the item if it's been set to 0
            if quantity and quantity > 0:
                cart[index]['quantity'] = quantity
            else:
                cart.pop(index)
            session['custom_cart'] = cart
            
    return redirect(url_for('checkout'))

# Removes a ready-made sandwich from the cart
@app.route('/cart/delete-premade/<string:item_id>')
def delete_premade_item(item_id):
    if 'premade_cart' in session:
        cart = session['premade_cart']
        cart.pop(item_id, None)
        session['premade_cart'] = cart
        flash("Pre-made sub removed.")
        
    return redirect(url_for('checkout'))

# Removes a Sub of the Day sandwich from the cart
@app.route('/cart/delete-sotd/<string:item_id>')
def delete_sotd_item(item_id):
    if 'sotd_cart' in session:
        cart = session['sotd_cart']
        cart.pop(item_id, None)
        session['sotd_cart'] = cart
        flash("Sub of the Day item removed.")

    return redirect(url_for('checkout'))

# Removes a custom sandwich from the cart
@app.route('/cart/delete-custom/<int:index>')
def delete_custom_item(index):
    if 'custom_cart' in session:
        cart = session['custom_cart']
        # Stops the website crashing if this item doesn't exist anymore
        idx = int(index)
        if 0 <= idx < len(cart):
            cart.pop(idx)
            session['custom_cart'] = cart
            flash("Custom sub removed.")
            
    return redirect(url_for('checkout'))

# --- PLACING THE ORDER --- #

@app.route('/checkout/thanks')
def purchase_thanks():
    # The customer must be logged in to place an order
    email = session.get('user')
    if not email:
        flash("You must be logged in to complete a purchase!")
        return redirect(url_for('signin'))

    premade_cart = session.get('premade_cart', {})
    sotd_cart = session.get('sotd_cart', {})
    custom_cart = session.get('custom_cart', [])

    # The pickup time the customer chose, e.g. "14:35"
    pickup_time = session.get('pickup_time_value')

    # Stops here if there's nothing in the cart
    if not premade_cart and not sotd_cart and not custom_cart:
        flash("Your cart is empty.")
        return redirect(url_for('menu'))

    db = get_db()
   
    try:
        # Finds the customer's ID from their email
        customer_row = query_db("SELECT ID FROM CUSTOMER WHERE email = ?", (email,), one=True)
        if not customer_row:
            flash("User account not found.")
            return redirect(url_for('signin'))
        customer_id = customer_row[0]

        # Works out the full price of the order
        grand_total = 0.0
       
        for item_id_str, quantity in premade_cart.items():
            price_row = query_db("SELECT price FROM PRE_SANDWICH WHERE ID = ?", (int(item_id_str),), one=True)
            if price_row:
                grand_total += price_row[0] * quantity

        # Sub of the Day items use the discounted price they were added at, not today's normal price
        for item_id_str, data in sotd_cart.items():
            grand_total += data['unit_price'] * data['quantity']

        for custom in custom_cart:
            single_unit_price = calculate_custom_sandwich_price(custom)
            qty = custom.get('quantity', 1)
            grand_total += single_unit_price * qty

        # Rounds the total to 2 decimal places, so tiny rounding errors never get saved
        grand_total = round(grand_total, 2)

        # Creates the order in the database
        cursor = db.execute(
            """
            INSERT INTO ORDERS (customer_ID, order_ts, total_amount, pickup_time)
            VALUES (?, datetime('now', 'localtime'), ?, ?)
            """,
            (customer_id, grand_total, pickup_time)
        )
        # This is the new order's own ID number, shown to the customer
        new_order_id = cursor.lastrowid

        # Saves each ready-made sandwich as part of the order
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
                    (new_order_id, pre_id, quantity, round(actual_price * quantity, 2))
                )

        # Saves each Sub of the Day sandwich as part of the order, at its discounted price
        for item_id_str, data in sotd_cart.items():
            pre_id = int(item_id_str)
            quantity = data['quantity']
            unit_price = data['unit_price']
            db.execute(
                """
                INSERT INTO ORDER_ITEMS (order_ID, pre_sandwich_ID, cus_sandwich_ID, quantity, final_price)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (new_order_id, pre_id, quantity, round(unit_price * quantity, 2))
            )

        # Saves each custom sandwich as part of the order, along with its sauces and toppings
        for custom in custom_cart:
            qty = custom.get('quantity', 1)
            single_unit_price = calculate_custom_sandwich_price(custom)
            total_custom_price = round(single_unit_price * qty, 2)
           
            # Saves the sandwich's bread and cheese combination
            cus_cursor = db.execute(
                "INSERT INTO CUS_SANDWICH (bread_ID, cheese_ID) VALUES (?, ?)",
                (custom['bread'], custom['cheese'])
            )
            new_custom_sandwich_id = cus_cursor.lastrowid
           
            # Saves each sauce that was picked
            for sauce_id in custom.get('sauces', []):
                db.execute(
                    "INSERT INTO CUS_SANDWICH_SAUCES (cus_sandwich_ID, sauce_ID) VALUES (?, ?)",
                    (new_custom_sandwich_id, sauce_id)
                )
               
            # Saves each topping that was picked
            for topping_id in custom.get('toppings', []):
                db.execute(
                    "INSERT INTO CUS_SANDWICH_TOPPINGS (cus_sandwich_ID, topping_ID) VALUES (?, ?)",
                    (new_custom_sandwich_id, topping_id)
                )

            # Saves this custom sandwich as part of the order
            db.execute(
                """
                INSERT INTO ORDER_ITEMS (order_ID, pre_sandwich_ID, cus_sandwich_ID, quantity, final_price)
                VALUES (?, NULL, ?, ?, ?)
                """,
                (new_order_id, new_custom_sandwich_id, qty, total_custom_price)
            )

        # Saves everything permanently
        db.commit()

        # Empties the shopping cart now the order has gone through
        session.pop('premade_cart', None)
        session.pop('sotd_cart', None)
        session.pop('custom_cart', None)
        # Clears the chosen store and time too, ready for the customer's next order
        session.pop('selected_store_id', None)
        session.pop('pickup_time_value', None)
        session.pop('pickup_time_display', None)

        # Finds the customer's favourite store, since that's where they're picking up from
        store_row = query_db(
            "SELECT STORES.name FROM CUSTOMER LEFT JOIN STORES ON CUSTOMER.pref_store = STORES.ID WHERE CUSTOMER.ID = ?",
            (customer_id,),
            one=True
        )
        # Shows a general message if the customer hasn't saved a favourite store
        store_name = store_row[0] if store_row and store_row[0] else "your preferred store"

    except sqlite3.Error as e:
        print(f"Database transaction failure: {e}")
        return "An internal error occurred saving your transaction.", 500

    # Shows the thank you page, with the store, order number, pickup time, and total price
    return render_template(
        "thanks.html",
        store_name=store_name,
        order_id=new_order_id,
        pickup_display=format_pickup_time(pickup_time),
        total_amount=grand_total
    )

# Starts the website running
if __name__ == "__main__":
    migrate_passwords()
    app.run(debug=True)