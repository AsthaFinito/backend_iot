from flask import Flask, flash, json, redirect, render_template, request, jsonify, url_for
import hashlib

app = Flask(__name__)
app.secret_key = 'test'
def load_users():
    with open('db/login_db.json', 'r') as file:
        return json.load(file)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

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

@app.route('/')
def home():
    return "Bienvenue sur la page d'accueil!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)