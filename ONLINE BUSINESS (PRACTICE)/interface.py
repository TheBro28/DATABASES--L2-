"""This code is the front end of the database and allows the users to ask a range of queries about the information"""

# Imports SQLite3
import sqlite3

# Defines the database as a constant
DATABASE = 'Business.db'

def print_all_orders():

    with sqlite3.connect(DATABASE) as db:
        order_num = int(input("Order number?"))
        # Adds cursor
        cursor = db.cursor()
        sql = "SELECT order_number, customer_name, customer_id, product_id, price_paid FROM Orders WHERE order_number == ?;"
        # Fetches all results after using cursor
        cursor.execute(sql,(order_num,))
        results = cursor.fetchall()

        # Prints all results fetched 
        for i in results:
            print(f'Order Number: {i[0]} | Customer Name: {i[1]} | Customer ID: {i[2]} | Product ID: {i[3]} | Price Paid: ${i[4]} ') 

if __name__ == "__main__":
    print_all_orders()

# {i[0]} | Customer ID: {i[1]} | Customer Name:  | Address: {i[3]} | City: {i[4]} | Region: {i[5]} | Post Code: {i[6]} | Shipping Date: {i[7]} | Price Paid: {i[8]} | Product ID: {i[9]} | Shipping ID: {i[10]}