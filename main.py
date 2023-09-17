from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import sqlite3
import os

main = Flask(__name__)
main.config["SECRET_KEY"] = os.urandom(16)
socketio = SocketIO(main)

rooms={} # Where created rooms go
chat_rooms={"General", "Sports", "Music", "Gaming"} # Where preset forums go

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
@main.route('/homepage')
def chatforum():
    if 'username' in session:
        username = session['username']
    else:
        username = "No User"
    return render_template('Home.html', username=username)
# Homepage stuff end

# About page stuff start
@main.route('/about')
def about():
    if 'username' in session:
        username = session['username']
    else:
        username = "No User"
    return render_template('about.html', username=username)
# About page stuff end

# Contact Us page stuff start
@main.route('/contactus')
def contactus():
    if 'username' in session:
        username = session['username']
    else:
        username = "No User"
    return render_template('contact_us.html', username=username)
# Contact Us page stuff end

# Sign-up and login stuff start
@main.route('/')
def home():
    if 'username' in session:
        username = session['username']
    else:
        username = "No User"
    return render_template('index.html', username=username)

@main.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')

@main.route('/login')
def login():
    return render_template('login.html')

@main.route('/signup')
def signup():
    return render_template('signup.html')

@main.route('/select', methods=['POST'])
def select():
    con = sqlite3.connect('database.db')
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

@main.route('/insert', methods=['POST'])
def insert():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("""
    INSERT INTO login (username, password)
    VALUES (?,?)""",
    (request.form['username'], request.form['password']))
    con.commit()
    return redirect('/login')

@main.route('/zia')
def zia():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("""
    INSERT INTO login (username, password)
    VALUES ("zia", "123")
    """)
    con.commit()
    return "zia added!"

@main.route('/tbl')
def tbl():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE login
    (
    username VARCHAR(20) NOT NULL PRIMARY KEY,
    password VARCHAR(20) NOT NULL
    )
    """)
    return "table created!"
# Sign-up and login stuff end

# Chat Stuff Start________________________________________________________________________________________________________________________________
# Route for live chat
@main.route("/LiveChat", methods=["POST", "GET"])
def live():
    # Clear the session
    session.clear()

    # If the method is POST
    if request.method == "POST":
        # Get the name and code from the form
        name = request.form.get("name")
        code = request.form.get("code")

        # Get the join and create flags from the form
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # If no name is provided, return an error
        if not name:
            return render_template("Live.html", error="Please enter a name.", code=code, name=name)

        # If joining a room and no code is provided, return an error
        if join != False and not code:
            return render_template("Live.html", error="Please enter a room code.", code=code, name=name)

        # Set the room to the provided code
        room=code

        # If creating a room, generate a unique code and create the room
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}

        # If joining a room and the room does not exist, return an error
        elif code not in rooms:
            return render_template("Live.html", error="Room does not exist.", code=code, name=name)

        # Set the session variables
        session["room"] = room
        session["name"] = name

        # Redirect to the room
        return redirect(url_for("room"))

    # If the method is GET, render the live chat template
    return render_template("Live.html")

# Route for the chat room
@main.route("/room")
def room():
    # Get the room from the session
    room = session.get("room")

    # If no room or name is set in the session, or if the room does not exist, redirect to home
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    # Render the room template with the room code and messages
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

# SocketIO event for receiving a message
@socketio.on("message")
def message(data):
    # Get the room from the session
    room = session.get("room")

    # If the room does not exist, return
    if room not in rooms:
        return

    # Create the message content
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }

    # Send the message to the room
    send(content, to=room)

    # Append the message to the room's messages
    rooms[room]["messages"].append(content)

    # Print the message
    print(f"{session.get('name')} said: {data['data']}")

# SocketIO event for a client connecting
@socketio.on("connect")
def connect(auth):
    # Get the room and name from the session
    room = session.get("room")
    name = session.get("name")

    # If no room or name is set in the session, return
    if not room or not name:
        return

    # If the room does not exist, leave the room and return
    if room not in rooms:
        leave_room(room)
        return

    # Join the room
    join_room(room)

    # Send a message to the room indicating that the client has entered the room
    send({"name": name, "message": "has entered the room"}, to=room)

    # Increment the number of members in the room
    rooms[room]["members"] += 1

    # Print that the client has joined the room
    print(f"{name} joined room {room}")

# SocketIO event for a client disconnecting
@socketio.on("disconnect")
def disconnect():
    # Get the room and name from the session
    room = session.get("room")
    name = session.get("name")

    # Leave the room
    leave_room(room)

    # If the room exists
    if room in rooms:
        # Decrement the number of members in the room
        rooms[room]["members"] -= 1

        # If there are no members left in the room, delete the room
        if rooms[room]["members"] <= 0:
            del rooms[room]

    # Send a message to the room indicating that the client has left the room
    send({"name": name, "message": "has left the room"}, to=room)

    # Print that the client has left the room
    print(f"{name} has left the room {room}")
# Chat Stuff End________________________________________________________________________________________________________________________________

# Forum Stuff Start__________________________________________________________



# Forum Stuff End_____________________________________________________________

if __name__ == "__main__":
    socketio.run(main, debug=True)
