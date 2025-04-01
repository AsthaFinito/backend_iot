from datetime import datetime, timedelta, timezone
import os
from flask import Flask, flash, json, redirect, render_template, request, jsonify, session, url_for
import hashlib
import math
from dateutil.parser import parse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, current_user
from datetime import datetime

db = SQLAlchemy()

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Notification {self.message}>'


MAX_DISTANCE_KM = 30
MAX_AGE_MINUTES = 30

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

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all() 
    @app.template_filter('time_since')
    def time_since_filter(timestamp_str):
        if not timestamp_str:
            return "Jamais connecté"
        
        try:
            timestamp = parse(timestamp_str)
            print(datetime.now())
            delta = datetime.now() - timestamp
            print(delta)
            seconds = delta.total_seconds()
            if seconds < 60:
                return "À l'instant"
            elif seconds < 3600:  # < 1h
                return f"{int(seconds/60)} min"
            elif seconds < 86400:  # < 1j
                return f"{int(seconds/3600)}h"
            else:
                return f"{int(seconds/86400)}j"
                
        except Exception as e:
            app.logger.error(f"Erreur parsing timestamp {timestamp_str}: {str(e)}")
            return "Hors ligne"

    return app


def configure_and_send_mail(mail_addr,detected_plate,detection_time,lat,long):
    sender_email = "projet.iot.backend@gmail.com"
    password = "ixub prrf kmbt mygd" 
    subject = "Dection automatique d'une plaque que vous recherchez"
    body = f"""
Bonjour,

Nous vous informons que l'appareil de détection a détecté une plaque correspondante à vos critères de recherche.

Détails de la détection :
- Plaque détectée : {detected_plate}
- Heure de la détection : {detection_time}
- Localisation : {lat}, {long}

Nous vous invitons à vérifier ces informations et à prendre les mesures nécessaires.

Cordialement,
L'équipe de surveillance
"""
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = sender_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, sender_email, text)
        print(f"E-mail envoyé avec succès à {mail_addr}.")
    except Exception as e:
        print(f"Une erreur est survenue : {e}")
    finally:
        server.quit()
    
app = create_app()
app.secret_key = 'test'
def load_users():
    with open('db/login_db.json', 'r') as file:
        return json.load(file)
def load_friends():
    with open('db/friend_db.json', 'r') as file:
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
        "timestamp": datetime.now().isoformat()  
    }
    save_latest_positions(positions)

def get_friends(client_id):
    if client_id in (None, ""):
        raise ValueError("L'ID client ne peut pas être vide")
    friends_data = load_friends() if callable(load_friends) else {}
    return list(friends_data.get(str(client_id), []))

def transform_username_to_clientid(username):
    with open('db/login_db.json') as f:
       user_db = json.load(f)
    for user in user_db:
        if user["username"] == username:
            return user["id_client"]
    return None

def get_nearby_friends(client_id):
    #print("client_id",client_id)
    friends_list = get_friends(client_id)  # Liste des IDs d'amis
    client_pos = get_latest_pos(client_id)  # Position du client
    # print("friends_list",friends_list)
    # print("client_pos",client_pos)
    if not client_pos:
        return []

    current_time = datetime.now()
    nearby_friends = []
    for friend_id in friends_list:
        #print(transform_username_to_clientid(friend_id))
        friend_pos = get_latest_pos(transform_username_to_clientid(friend_id))
        #print("friend_pos",friend_pos)
        if not friend_pos:
            continue
        try:
            last_update = datetime.fromisoformat(friend_pos['timestamp'])
            if (current_time - last_update) > timedelta(minutes=MAX_AGE_MINUTES):
                #print("Erreur timedelta")
                continue
        except (KeyError, ValueError):
            #print("Dans le excetp")
            continue
        distance = distance_haversine(
            client_pos['lat'], client_pos['long'],
            friend_pos['lat'], friend_pos['long']
        )
        #print("distance",distance)
        if distance <= MAX_DISTANCE_KM:
            nearby_friends.append({
                "friend_id": str(friend_id),
                "distance_km": round(distance, 2),
            })
    nearby_friends.sort(key=lambda x: x['distance_km'])
    
    return nearby_friends


def get_latest_pos(client_id):
    positions = load_latest_positions()
    client_pos = positions.get(str(client_id))
    
    if client_pos:
        return {
            'lat': client_pos['lat'],
            'long': client_pos['long'],
            'timestamp': client_pos.get('timestamp')
        }
    return None

def send_notification(user_id, message):
    print("SENDING")
    print(user_id)
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()

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
    # print(get_latest_pos(id_client)) 
    # print(get_friends(id_client))
    save_data(data)
    return get_nearby_friends(id_client)


def is_clientid_present(client_id):
    users = load_users()  
    return any(user["id_client"] == int(client_id) for user in users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        user = next((user for user in users if user['username'] == username), None)
       
        if user and user['password_hash'] == hash_password(password):
            flash('Connexion réussie!', 'success')
            session['user_id'] = user['id_client']
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiant ou mot de passe incorrect', 'error')


    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    username = session['username']
    friends_db = load_friends()
    friend_ids = friends_db.get(str(user_id), [])
    print(user_id)
    users_db = load_users()
    notifications = Notification.query.all()
    print("BEFORE NOTIF 1: ")
    for notification in notifications:
        print(f"ID: {notification.id}, User ID: {notification.user_id}, Message: {notification.message}, Timestamp: {notification.timestamp}")
    
    notifications = Notification.query.filter_by(user_id=user_id).all()
    print("BEFORE NOTIF 2: ")
    for notification in notifications:
        print(f"ID: {notification.id}, User ID: {notification.user_id}, Message: {notification.message}, Timestamp: {notification.timestamp}")
    
    friends = []
    for friend_id in friend_ids:
        latest_pos=get_latest_pos(transform_username_to_clientid(friend_id))
        print(latest_pos)
        friend = next((u for u in users_db if u['id_client'] == transform_username_to_clientid(friend_id)), None)
        if friend:
             friends.append({
                'username': friend['username'],
                'last_seen': latest_pos.get('timestamp') if latest_pos else None,
            })
    
    return render_template('dashboard.html', username=username,friends=friends,notifications=notifications)



@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
def add():
    id_client = request.json.get('id_client')
    string = request.json.get('string')
    lat = request.json.get('lat')
    long = request.json.get('long')

    if not id_client or not string:
        return jsonify({"error": "id_client et string sont obligatoires"}), 400

    if not is_clientid_present(id_client):
        return jsonify({"error": f"Client ID {id_client} non trouvé"}), 404
    nearby_friends = add_entry(id_client, string, lat, long)

    if not nearby_friends:
        print("NO FRIEND NEAR")
    else:
        print("A FRIEND IS NEAR")
        for friend in nearby_friends:
            send_notification(id_client, f"Votre ami {friend['friend_id']} est à {friend['distance_km']} km de vous.")
    #         notifications = Notification.query.all()

    # # Afficher les notifications dans la console
    #         for notification in notifications:
    #             print(f"ID: {notification.id}, User ID: {notification.user_id}, Message: {notification.message}, Timestamp: {notification.timestamp}")
    
    if is_plate_present(string):
        print("USEFULL PLATE DETECT")
        configure_and_send_mail("test",string,None,lat,long)
    else:
        print("NOT USEFULL PLATE")
    return jsonify({"message": "Entrée ajoutée avec succès"}), 201

@app.route('/')
def home():
    return "Bienvenue sur la page d'accueil!"

@app.route('/notifications', methods=['GET'])
def get_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Utilisateur non connecté'}), 401

    user_id = session['user_id']
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).order_by(Notification.timestamp.desc()).all()

    return jsonify([
        {'id': n.id, 'message': n.message, 'timestamp': n.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        for n in notifications
    ])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    