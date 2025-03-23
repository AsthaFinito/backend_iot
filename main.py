from flask import Flask, flash, json, redirect, render_template, request, jsonify, url_for
import hashlib

app = Flask(__name__)
app.secret_key = 'test'
def load_users():
    with open('db/login_db.json', 'r') as file:
        return json.load(file)
def load_data():
    with open('db/plate_db.json', 'r') as file:
        return json.load(file)
def save_data(data):
    with open('db/plate_db.json', 'w') as file:
        json.dump(data, file, indent=4)
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def add_entry(id_client, string, localisation=None):
    data = load_data()
    new_entry = {
        "id_client": id_client,
        "string": string,
        "localisation": localisation
    }
    data.append(new_entry)
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
    localisation = request.json.get('localisation')

    if not id_client or not string:
        return jsonify({"error": "id_client et string sont obligatoires"}), 400

    add_entry(id_client, string, localisation)
    return jsonify({"message": "Entrée ajoutée avec succès"}), 201

@app.route('/')
def home():
    return "Bienvenue sur la page d'accueil!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)