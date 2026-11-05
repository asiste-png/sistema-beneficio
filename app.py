from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db
from io import BytesIO
import sqlite3
import pandas as pd

app = Flask(__name__)
app.secret_key = 'clave_secreta_beneficio_plataforma'

# Manejador seguro para evitar fallas por nombres de funciones faltantes en url_for
def handle_url_build_error(error, endpoint, values):
    return url_for('dashboard', **values)

app.url_build_error_handlers.append(handle_url_build_error)

# Inicialización de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Inicialización de la base de datos
init_db()

# Clase de Usuario para Flask-Login
class User(UserMixin):
    def __init__(self, id, username, nombre, rol='operador'):
        self.id = id
        self.username = username
        self.nombre = nombre
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        user_data = cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    except Exception:
        user_data = None
    finally:
        conn.close()

    if user_data:
        rol = user_data['rol'] if 'rol' in user_data.keys() and user_data['rol'] else 'operador'
        return User(id=user_data['id'], username=user_data['username'], nombre=user_data['nombre'], rol=rol)
    return None

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
@app.route('/beneficio')
@app.route('/index')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    registros = cursor.execute("SELECT * FROM beneficio ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('beneficio.html', registros=registros)

# Alias por si las plantillas usan url_for('beneficio') o url_for('index')
beneficio = dashboard
index = dashboard

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        user_data = cursor.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user_data and check_password_hash(user_data['password'], password):
            rol = user_data['rol'] if 'rol' in user_data.keys() and user_data['rol'] else 'operador'
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                nombre=user_data['nombre'],
                rol=rol
            )
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/usuarios')
@login_required
def usuarios():
    if current_user.rol != 'admin':
        flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    lista_usuarios = cursor.execute("SELECT id, username, nombre, rol FROM usuarios").fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=lista_usuarios)

@app.route('/crear_usuario', methods=['POST'])
@login_required
def crear_usuario():
    if current_user.rol != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    nombre = request.form.get('nombre', '').strip()
    rol = request.form.get('rol', 'operador')

    if username and password and nombre:
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO usuarios (username, password, nombre, rol)
                VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, nombre, rol))
            conn.commit()
            flash('Usuario creado exitosamente', 'success')
        except sqlite3.IntegrityError:
            flash('El nombre de usuario ya existe', 'warning')
        finally:
            conn.close()
    else:
        flash('Por favor completa todos los campos', 'warning')

    return redirect(url_for('usuarios'))

if __name__ == '__main__':
    app.run(debug=True)