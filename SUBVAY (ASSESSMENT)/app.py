from flask import Flask, g, render_template
import sqlite3

DATABASE = 'subvay.db'
    
# Initialise App
app = Flask(__name__)

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

@app.route('/')
def home():
    # home page
    sql = """SELECT 
    Customer.acc_number, -- Customer account number
    Bread.name AS bread_name, -- Name of the bread used
    Cheese.name AS cheese_name, -- Name of the cheese used
    GROUP_CONCAT(DISTINCT Toppings.name) AS toppings_filtered, -- List of all chosen topping names
    GROUP_CONCAT(DISTINCT Sauce.name) AS sauces_filtered, -- List of all chosen sauce names
    Orders.quantity, -- Quantity of the order
    (
        -- Calculate total price:
        -- Sum of bread price
        (SELECT price FROM Bread WHERE ID = Bread.ID) +
        -- Sum of cheese price
        (SELECT price FROM Cheese WHERE ID = Cheese.ID) +
        -- Sum of selected toppings prices
        (
            SELECT SUM(Toppings.price)
            FROM Toppings
            WHERE Toppings.ID IN (14, 12, 6, 3, 1, 8)
        ) +
        -- Sum of selected sauces prices
        (
            SELECT SUM(Sauce.price)
            FROM Sauce
            WHERE Sauce.ID IN (3, 7, 8, 1)
        )
    ) * Orders.quantity AS total_price -- Multiply by order quantity for total cost
FROM Orders

LEFT JOIN Cus_Sandwich ON Orders.cus_sandwich_ID = Cus_Sandwich.ID -- Link to specific sandwich (CUSTOM SANDWICH TABLE)
LEFT JOIN Bread ON Cus_Sandwich.bread_ID = Bread.ID -- Link to bread details (BREAD TABLE)
LEFT JOIN Cheese ON Cus_Sandwich.cheese_ID = Cheese.ID -- Link to cheese details (CHEESE TABLE)
LEFT JOIN Toppings ON Toppings.ID IN (2, 12, 6, 3, 1, 8) -- Filter toppings by specific IDs (TOPPINGS TABLE)
LEFT JOIN Sauce ON Sauce.ID IN (14, 12, 6, 3, 1, 8) -- Filter sauces by specific IDs (SAUCE TABLE)
LEFT JOIN Customer ON Orders.customer_ID = Customer.ID -- Link to customer details (CUSTOMER TABLE)
WHERE Customer.ID = 1 -- Filter for customer with ID '?'
GROUP BY 
    Customer.acc_number, -- Grouping by customer account
    Bread.name, -- Grouping by bread name
    Cheese.name, -- Grouping by cheese name
    Orders.quantity;
"""
    results = query_db(sql)
    return render_template("Website Pages/Sandwich Related Pages/SoTD.html")

@app.route('/sandwich/<int:ID>')
def sandwich(ID):
    # Just one sandwich based on the ID
    sql =  """SELECT """



@app.route('/menu')
def menu():
    return "menu.html"

@app.route('/premade_sandwich')
def pre_sandwich():
    return ""

@app.route('/basket')
def basket():
    return ""

@app.route('/checkout')
def checkout():
    return ""

if __name__ == "__main__":
    app.run(debug=True)

