"""This code is the front end of the database and allows the users to ask a range of queries about the information"""
import sqlite3

DATABASE = 'Business.db'

def print_all_orders():
    order = input('Order number: ')
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        sql = "SELECT * FROM Orders WHERE order_number == ?;"
        cursor.execute(sql,(order,))
        results = cursor.fetchall()
        # Prints them nicely

        for o in results:
            print(f"Order Number: {o[0]} | Customer ID: {o[1]} | Region: {o[2]} | Ship Date: {o[3]} | Price Paid: {o[4]} | Product ID: {o[5]} | Shipping ID {o[6]}")

if __name__ == "__main__":
    print_all_orders()