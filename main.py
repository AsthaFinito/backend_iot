import datetime
import os
from flask import Flask, flash, json, redirect, render_template, request, jsonify, url_for
import hashlib
import math

def distance_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance


app = Flask(__name__)
app.secret_key = 'test'
def load_users():
    with open('db/login_db.json', 'r') as file:
        return json.load(file)
def load_friends():
    with open('db/friends_db.json', 'r') as file:
        return json.load(file)
def load_data():
    with open('db/plate_db.json', 'r') as file:
        return json.load(file)
def load_latest_positions():
    if not os.path.exists('db/positions_db.json'):
        return {}
    with open('db/positions_db.json', 'r') as file:
        return json.load(file)
def save_latest_positions(data):
    os.makedirs('db', exist_ok=True)
    with open('db/positions_db.json', 'w') as file:
        json.dump(data, file, indent=4)
def save_data(data):
    with open('db/plate_db.json', 'w') as file:
        json.dump(data, file, indent=4)
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def is_plate_present(my_string):
    with open("db/usefull_plate.json", "r", encoding="utf-8") as file:
       json_data = json.load(file)
    try:
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        return any(entry.get("plate") == my_string for entry in json_data)
    except (json.JSONDecodeError, TypeError):
        return False

def add_latest_pos(id_client, lat, long):
    positions = load_latest_positions()
    positions[str(id_client)] = {
        "lat": lat,
        "long": long,
        "timestamp": datetime.datetime.now().isoformat()  # Optionnel: ajoute un timestamp
    }
    save_latest_positions(positions)


def add_entry(id_client, string, lat,long):
    data = load_data()
    new_entry = {
        "id_client": id_client,
        "plate": string,
        "lat": lat,
        "long": long
    }
    data.append(new_entry)
    add_latest_pos(id_client, lat, long)
    save_data(data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        user = next((user for user in users if user['username'] == username), None)
       
        if user and user['password_hash'] == hash_password(password):
            flash('Connexion réussie!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Identifiant ou mot de passe incorrect', 'error')


    return render_template('login.html')

@app.route('/add', methods=['POST'])
def add():
    id_client = request.json.get('id_client')
    string = request.json.get('string')
    lat = request.json.get('lat')
    long = request.json.get('long')

    if not id_client or not string:
        return jsonify({"error": "id_client et string sont obligatoires"}), 400

    add_entry(id_client, string, lat,long)
    if is_plate_present(string):
        print("USEFULL PLATE DETECT")
    else:
        print("NOT USEFULL PLATE")
    return jsonify({"message": "Entrée ajoutée avec succès"}), 201

@app.route('/')
def home():
    return "Bienvenue sur la page d'accueil!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    