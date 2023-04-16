from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

main = Flask(__name__)
main.config["SECRET_KEY"] = "ylgyghglhg"
socketio = SocketIO(main)

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
@main.route('/homepage')
def chatforum():
    return render_template('Home.html')
# Homepage stuff end

# Sign-up and login stuff start
@main.route('/')
def home():
    return render_template('index.html')

@main.route('/signup', methods=['POST'])
def signup():
    f = open("user.txt", "w")
    f.write(request.form['username'] + ',' + request.form['password'])
    f.close()
    return render_template('login.html')

@main.route('/login')
def login():
     return render_template('login.html')

@main.route('/verify', methods=['POST'])
def verify():
    f = open("user.txt", "r")
    file = f.read()
    split = file.split(',')
    if request.form['username'] != split[0] and request.form['password'] == split[1]:
        return 'Username or Password Incorrect'
    elif request.form['username'] == split[0] and request.form['password'] == split[1]:
        return render_template('Home.html')
# Sign-up and login stuff end

# Chat Stuff Start
@main.route("/LiveChat", methods=["POST", "GET"])
def live():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("Live.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("Live.html", error="Please enter a room code.", code=code, name=name)

        room=code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("Live.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("Live.html")

@main.route("/room")
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

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")
# Chat Stuff End

if __name__ == "__main__":
    socketio.run(main, debug=True)
