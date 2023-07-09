from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import sqlite3
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "ylgyghglhg"
socketio = SocketIO(app)

rooms={} # Where created rooms go

# Room Code Generator start
def generate_unique_code(length):
    while True:
        code= ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break
    return code
# Room Code Generator end

# Homepage stuff start
@app.route('/homepage')
def chatforum():
    if 'username' in session:
        username = session['username']
    else:
        username = "not logged in"
        return render_template('index.html', username=username)
    return render_template('home.html', username=username)

# Homepage stuff end

# Sign-up and login stuff start
@app.route('/')
def signup():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/tbl')
def tbl():
    con = sqlite3.connect('logindatabase.db')
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE login
    (
    username VARCHAR(20) NOT NULL PRIMARY KEY,
    password VARCHAR(20) NOT NULL
    )
    """)
    return "table created!"

@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/homepage')

@app.route('/select', methods=['POST'])
def select():
    con = sqlite3.connect('logindatabase.db')
    cur = con.cursor()
    cur.execute(""" SELECT * FROM login
                    WHERE username = ? AND password = ? """,
                    (request.form['username'], request.form['password']))
    rows = cur.fetchall()
    if len(rows) == 1:
        session['username'] = request.form['username']
        return redirect('/homepage')
    else:
        return "Login not recognised"

@app.route('/insert', methods=['POST'])
def insert():
    con = sqlite3.connect('logindatabase.db')
    cur = con.cursor()
    cur.execute("""
    INSERT INTO login (username, password)
    VALUES (?,?)""",
    (request.form['username'], request.form['password']))
    con.commit()
    return redirect('/select')

@app.route('/zia')
def zia():
    con = sqlite3.connect('logindatabase.db')
    cur = con.cursor()
    cur.execute("""
    INSERT INTO login (username, password)
    VALUES ("zia", "123")
    """)
    con.commit()
    return "zia added!"
# Sign-up and login stuff end

# Chat Stuff Start
@app.route("/LiveChat", methods=["POST", "GET"])
def live():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("live.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("live.html", error="Please enter a room code.", code=code, name=name)

        room=code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("live.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("live.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
           del rooms[room]
           send({"name": name, "message": "has deleted the room"}, to=room)

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")
# Chat Stuff End

if __name__ == "__main__":
    socketio.run(app, debug=True)
