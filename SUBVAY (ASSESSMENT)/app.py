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
    return render_template("Website Pages/Misc Pages/home.html")

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

