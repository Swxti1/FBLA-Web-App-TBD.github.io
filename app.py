from markupsafe import escape
import sqlite3
from flask import Flask, abort, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'Jeff-is-the-best-girrafe_o_algo'

ALLOWED_ROLES = ['organizer', 'volunteer']
ROLE_HOME = {'organizer': '/organizer', 'volunteer': '/volunteer'}

def db():

#  CREATE TABLE FOR USERS
    conn = sqlite3.connect('users.db')
    conn.execute(
        'CREATE TABLE IF NOT EXISTS users ('
        'id INTEGER PRIMARY KEY, '
        'username TEXT UNIQUE NOT NULL, '
        'password_hash TEXT NOT NULL, '
        'email TEXT UNIQUE NOT NULL, '
        'role TEXT NOT NULL)'
    )

#  CREATE TABLE FOR VARIABLES FOR ORGANIZING EVENT
    conn.execute(
        'CREATE TABLE IF NOT EXISTS events ('        
        'id INTEGER PRIMARY KEY, '                   #  auto-filled id for each event
        'organizer TEXT NOT NULL,'
        'title TEXT NOT NULL, '
        'event_date TEXT NOT NULL, '
        'start_time TEXT NOT NULL, '
        'end_time TEXT NOT NULL, '
        'location TEXT NOT NULL, '
        'capacity INTEGER NOT NULL, '                #  num of volunteers
        'description TEXT, '
        'status TEXT NOT NULL)'                      #  "draft" or "published"
    )

#  SAVED EVENTS FOR VOL
    conn.execute(                                    
        'CREATE TABLE IF NOT EXISTS saved_events ('
        'id INTEGER PRIMARY KEY, ' 
        'event_id INTEGER NOT NULL, '
        'volunteer TEXT NOT NULL, '
        'UNIQUE (event_id, volunteer))'
    )

#  CREATE TABLE FOR SIGNUPS
    conn.execute(
        'CREATE TABLE IF NOT EXISTS signups ('
        'id INTEGER PRIMARY KEY, '
        'event_id INTEGER NOT NULL, '                #  event joined
        'volunteer TEXT NOT NULL, '                  #  username of the volunteer who signed up
        'UNIQUE (event_id, volunteer))'              #  blocks the same volunteer from signing up for the same event twice
    ) 
    return conn


#  INITIAL PAGE
@app.route('/')
def home():
    session.clear()
    return render_template('index.html')

#  CREATE ACCOUNT
@app.route('/register', methods=['POST'])
def register_user():

#  CREATES CREDENTIALS FOR ACCOUNT
    username = request.form['IGN or smthn'].strip()
    password = request.form['passywassy']
    password2 = request.form['passywassy2'] 
    email = request.form['email']
    role = request.form['role']

#  EXCEPTIONS
    if not username or not email or len(password) < 8:
        return render_template('signup.html', error='Username, email, and password are required or password must be at least 8 characters long')
    if password != password2:
        return render_template('signup.html', error='Passwords do not match')
    if role not in ALLOWED_ROLES:
        return render_template('signup.html', error='Invalid role selected')


#  PLACES INFO INTO USERS TABLE
    try: 
        with db() as conn:
            conn.execute(
            'INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(password), email, role)
        )
        return render_template('signup.html', message='User registered successfully')

#  MORE EXCEPTIONS
    except sqlite3.IntegrityError:
        return render_template('signup.html', error='Username or email already exists')


#  LOGIN FORM
@app.route('/login', methods=['POST'])
def login_user():

#  GETS USER INFO
    username = request.form['IGN or smthn'].strip()
    password = request.form['passywassy']

    with db() as conn:
        row = conn.execute(
            'SELECT password_hash, role FROM users WHERE username = ?',          #  LOCATE USER
            (username,)                                                          # FILLS ?
        ).fetchone()
    if row and check_password_hash(row[0], password):
        session['username'] = username
        session['role'] = row[1]
        return redirect(ROLE_HOME[row[1]])
    return render_template('index.html', error='Invalid username or password')


#  LOGOUT ROUTE
@app.route('/logout')
def logout():
    session.clear()                                  # FORGETS EVERYTHING
    return redirect('/')  


#  SIGN UP ROUTE
@app.route('/signup')
def signup():
    return render_template('signup.html')


#  ORGANIZER PAGE
@app.route('/organizer')
def organizer():
    if session.get('role') != 'organizer':
        return redirect('/')
    return render_template('Organizer Pages/organizer.html', username=escape(session['username']))

#  VOLUNTEER PAGE
@app.route('/volunteer')
def volunteer():  
    if session.get('role') != 'volunteer':
        return redirect('/')
    return render_template('Volunteer Pages/volunteer.html', username=escape(session['username'])) 



#                                          <----   EVENTS PAGES   ---->

#  VOLUNTEER EVENTS
@app.route('/Vevents')
def Vevents():
    if session.get('role') != 'volunteer' or 'username' not in session:
        return redirect('/')
    today = datetime.now().strftime('%Y-%m-%d')
    with db() as conn:
        conn.row_factory = sqlite3.Row

#  GETS EVENTS THAT ARE SIGNED UP FOR
    mine = conn.execute(
            'SELECT events.* FROM events JOIN signups ON signups.event_id = events.id '
            'WHERE signups.volunteer = ? AND events.event_date >= ? '
            'ORDER BY events.event_date, events.start_time',
            (session['username'], today)
        ).fetchall()

#  GETS ORGANIZER EVENTS
    available = conn.execute(
            "SELECT * FROM events WHERE status = 'published' AND event_date >= ? "
            'AND id NOT IN (SELECT event_id FROM signups WHERE volunteer = ?) '
            'ORDER BY event_date, start_time',
            (today, session['username'])
        ).fetchall()
    return render_template('Volunteer Pages/Vevents.html', username=escape(session['username']),
                           my_events=[],
                           nearby_events=[event_card(r) for r in available])

@app.route('/Vdetails/<int:event_id>')
def Vdetails(event_id):
    if session.get('role') != 'volunteer':
        return redirect('/')
    with db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM events WHERE id = ? AND status = 'published'",
            (event_id,)
        ).fetchone()
        if row is None:
            return redirect('/Vevents')
        taken = conn.execute('SELECT COUNT(*) FROM signups WHERE event_id = ?', (event_id,)).fetchone()[0]  # how many spots are used
        signed_up = conn.execute('SELECT 1 FROM signups WHERE event_id = ? AND volunteer = ?', (event_id, session['username'])).fetchone() is not None  # did THIS volunteer sign up?
        saved = conn.execute('SELECT 1 FROM saved_events WHERE event_id = ? AND volunteer = ?', (event_id, session['username'])).fetchone() is not None  # did THIS volunteer save it?
    return render_template('Volunteer Pages/Vdetails.html', username=escape(session['username']),  # the details page
                           event=event_card(row),                  # title, organizer, date, time, location, capacity
                           description=row['description'],         # the organizer's description text
                           spots_left=row['capacity'] - taken,     # spots still open
                           signed_up=signed_up, saved=saved)       # so the page can show their status

@app.route('/Vdetails/<int:event_id>/signup', methods=['POST'])
def Vsignups(event_id):
    if session.get('role') != 'volunteer':
        return redirect('/')
    with db() as conn:
        row = conn.execute("SELECT capacity FROM events WHERE id = ? AND status = 'published'", (event_id,)).fetchone()
        taken = conn.execute('SELECT COUNT(*) FROM signups WHERE event_id = ?', (event_id,)).fetchone()[0]
        if row and taken < row[0]:
            conn.execute('INSERT OR IGNORE INTO signups (event_id, volunteer) VALUES (?, ?)', (event_id, session['username']))
    return redirect('/Vdetails/' + str(event_id))

@app.route('/Vdetails/<int:event_id>/cancel', methods=['POST'])
def Vcancel(event_id):
    if session.get('role') != 'volunteer':
        return redirect('/')
    with db() as conn:
        conn.execute('DELETE FROM signups WHERE event_id = ? AND volunteer = ?', (event_id, session['username']))
    return redirect('/Vdetails/' + str(event_id))

@app.route('/Vdetails/<int:event_id>/save', methods=['POST'])
def Vsave(event_id):
    if session.get('role') != 'volunteer':
        return redirect('/')
    with db() as conn:
        conn.execute('INSERT OR IGNORE INTO saved_events (event_id, volunteer) VALUES (?, ?)', (event_id, session['username']))
    return redirect('/Vdetails/' + str(event_id))


#  ORGANIZER EVENTS
@app.route('/Oevents')
def Oevents():
    if session.get('role') != 'organizer' or 'username' not in session:
        return redirect('/')
    today = datetime.now().strftime('%Y-%m-%d')
    with db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT * FROM events WHERE organizer = ? ORDER BY event_date, start_time',
            (session['username'],)
        ).fetchall()
        others = conn.execute(
            "SELECT * FROM events WHERE organizer != ? AND status = 'published' AND event_date >= ? "
            'ORDER BY event_date, start_time',
            (session['username'], today)
        ).fetchall()
    return render_template('Organizer Pages/Oevents.html', username=escape(session['username']),
                           my_events=[event_card(r) for r in rows],
                           nearby_events=[event_card(r) for r in others])

#  CREATE NEW EVENT ROUTE
@app.route('/Oevents/new', methods=['GET', 'POST'])                               #     GET - shows the form   |   POST - receives form
def create_event():
    if session.get('role') != 'organizer':
        return redirect('/')
    if request.method == 'GET':
        return render_template('Organizer Pages/CREATE_EVENT.html', form={}, error=None)  # SHOWS EMPTY FORM

#  FORM DATA
    form = request.form
    title = form.get('title', '').strip()
    event_date = form.get('date', '') 
    start = form.get('start', '')
    end = form.get('end', '')
    location = form.get('location', '').strip() 
    capacity = form.get('capacity', '').strip()
    description = form.get('description', '').strip() 
    action = form.get('action', '')                                               #   DETERMINES IF PUBLISH OR DRAFT

    error = None
    if not title or not event_date or not start or not end or not location:       #  REQUIRED FIELDS
        error = 'Please fill in every required field.'
    elif not capacity.isdigit() or int(capacity) < 1:
        error = 'Volunteers needed must be a whole number of at least 1.'
    elif action not in ('draft', 'publish'):
        error = 'Something went wrong. Please try again.'
    else:

#  CHECKS VALIDITY
        try:
            datetime.strptime(event_date, '%Y-%m-%d')
            datetime.strptime(start, '%H:%M')
            datetime.strptime(end, '%H:%M')
        except ValueError:
            error = 'That date or time is not valid.'
        else:
            if end <= start:
                error = 'The end time must be after the start time.'
    if error:
        return render_template('Organizer Pages/CREATE_EVENT.html', form=form, error=error)

    status = 'published' if action == 'publish' else 'draft'
    with db() as conn:
        conn.execute(                                #  SAVE EVENT
            'INSERT INTO events (organizer, title, event_date, start_time, end_time, location, capacity, description, status) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (session['username'], title, event_date, start, end, location, int(capacity), description, status)
        )
    return redirect('/Oevents')



#                                       <----   ORGANIZATIONS PAGES   --->

#  ORGANIZATION ORGS ROUTE
@app.route('/Oorganizations')
def Oorganizations():
    if 'username' not in session:
        return redirect('/')
    return render_template('Organizer Pages/Oorganizations.html', username=escape(session['username']))

#  VOLUNTEER ORGS ROUTE
@app.route('/Vorganizations')
def Vorganizations():   
    if 'username' not in session:
        return redirect('/')
    return render_template('Volunteer Pages/Vorganizations.html', username=escape(session['username']))



#                                           <----   STATS PAGES   --->

# VOLUNTEER STATS ROUTE
@app.route('/Vstats')
def Vstats():
    if 'username' not in session:
        return redirect('/')
    return render_template('Volunteer pages/Vstats.html', username=escape(session['username']))

# ORGANIZER STATS ROUTE
@app.route('/Ostats')
def Ostats():
    if 'username' not in session: 
        return redirect('/') 
    return render_template('Organizer Pages/Ostats.html', username=escape(session['username']))



#  TOGGLE THEME BASED ON SYSTEM PREF
@app.route('/toggle-theme')
def toggle_theme():
    new_theme = 'light' if request.cookies.get('theme') == 'dark' else 'dark'
    response = redirect(request.referrer or '/')
    response.set_cookie('theme', new_theme, max_age=60 * 60 * 24 * 365)        # USES COOKIE TO REMEMBER CHOICE FOR A YEAR
    return response                                                            # COICE BASED OFF COOKIE



#                                         <----   SETTINGS PAGES   --->

#  VOLUNTEER SETTINGS ROUTE
@app.route('/Vsettings')
def Vsettings():
    if 'username' not in session:
        return redirect('/')
    return render_template('Volunteer Pages/Vsettings.html', username=escape(session['username']))

#  ORGANIZER SETTINGS ROUTE
@app.route('/Osettings')
def Osettings():
    if 'username' not in session:
        return redirect('/')
    return render_template('Organizer Pages/Osettings.html', username=escape(session['username']))



#  CARD FOR CREATING EVENT
def event_card(r):
    day = datetime.strptime(r['event_date'], '%Y-%m-%d')
    return {
        'id': r['id'],
        'title': r['title'], 
        'month': day.strftime('%b').upper(),
        'day': day.day, 
        'when': day.strftime('%A') + ' · ' + timeGrabber(r['start_time']) + ' – ' + timeGrabber(r['end_time']),
        'location': r['location'],
        'capacity': r['capacity'],
        'filled': filled_count(r['id']),             #  real number of volunteers signed up
        'description': r['description'],             #  the details text, used on the details page
        'date_long': day.strftime('%A, %B ') + str(day.day) + ', ' + str(day.year),
        'time_range': timeGrabber(r['start_time']) + ' – ' + timeGrabber(r['end_time']),
        'status': r['status'], 
        'organizer': r['organizer'],
    }



#  HOW MANY VOL FOR ONE EVENT
def filled_count(event_id):
    with db() as conn:
        return conn.execute('SELECT COUNT(*) FROM signups WHERE event_id = ?', (event_id,)).fetchone()[0]  # count rows


#  GETS CURRENT TIME
def timeGrabber(value):
    return datetime.strptime(value, '%H:%M').strftime('%I:%M %p').lstrip('0')



#  END PAGE AND RUN ALL
if __name__ == '__main__':
    app.run(debug=True)