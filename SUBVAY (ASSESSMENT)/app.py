from flask import Flask, g, render_template
import sqlite3

DATABASE = 'subvay(3).db'

#initialise app
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
    return(rv[0] if rv else None) if one else rv

@app.route('/')
def home():
  sql = ""
  results = query_db(sql)
  return render_template("index.php")
if __name__ == "__main__":
    app.run(debug=True)


    #DATABASE LOGIN HANDLING (TO BE MODIFIED)
    #Log In data handling
@app.route('/log-in')
def login():
    return render_template('login.html',warning=None)

@app.post('/get_login_data')
def handle_login_data():
    username = str(request.form['username'])
    password = str(request.form['password'])

    verify = verification(username,password)
    if verify:
        session['user'] = username
        return redirect('/')
    else: 
        return render_template('login.html',warning=True)
    
def verification(username, password):
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    query = f"select password from user where name = '{username}';"
    cursor.execute(query)
    actual_password = cursor.fetchone()
    db.close()
    actual_password = actual_password[0] if actual_password else False
    return password == actual_password 
