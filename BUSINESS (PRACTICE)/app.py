# Imports flask
from flask import Flask, g

# Imports SQLite3
import sqlite3

DATABASE = 'Business.db'

# initialise app
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

# Creates route connects it to defined function (home)
@app.route('/')
def home():
    # Home page
    sql = """SELECT firstname, lastname, street, city, postcode, packing_time, product_type, quantity
            FROM Orders
                JOIN Customers ON Customers.customer_ID = Orders.customer_ID
                    JOIN Shipments ON Shipments.shipping_ID = Orders.shipping_ID
                         JOIN Products ON Products.product_ID = Orders.product_ID
                ORDER BY firstname ASC
            LIMIT 10;"""
    results = query_db(sql)
    return str(results)

# Returns one order's details
@app.route('/order_num/<int:id>')
def order_num(id):
    sql = """SELECT order_number, firstname, lastname, to_region, ship_date,
             price_paid, street, city, postcode, product_type
            FROM Orders
            JOIN Customers ON Customers.customer_ID = Orders.customer_ID
            JOIN Products ON Products.product_ID = Orders.product_ID
            WHERE order_number = ?
            ORDER BY firstname DESC;"""
    result = query_db(sql, (id,), one=True)  # assuming query_db supports 'one=True'
    return str(result)

# Runs the website on IP server
if __name__ == "__main__":
    app.run(debug=True)