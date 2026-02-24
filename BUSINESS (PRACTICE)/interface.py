"""This code is the front end of the database and allows the users to ask a range of queries about the information"""
import sqlite3

DATABASE = 'Business.db'

def print_all_orders():
    order = input("Order number: ")
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        sql = "SELECT order_number, product_ID, firstname, lastname, ph_num FROM Orders LEFT JOIN Orders = Orders.order_number ON Customer.order_number"
        cursor.execute(sql,(order,))
        results = cursor.fetchall()
        # Prints results

        for o in results:
            print(f'Order Number: {order_number[0]} | Product ID: {product_ID[1]} | First Name: {firstname[2]} | Last Name: {lastname[3]}')

if __name__ == "__main__":
    print_all_orders()