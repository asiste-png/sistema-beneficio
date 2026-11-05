import os
import time
import io
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# ---------------------------------------------------------
# Configuración de Flask-Login
# ---------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    user_data = cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user_data:
        u_dict = dict(user_data)
        username = u_dict.get('username') or u_dict.get('nombre') or 'Usuario'
        return User(id=u_dict['id'], username=username)
    return None

# ---------------------------------------------------------
# Configuración de Subida de Archivos y Base de Datos
# ---------------------------------------------------------
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Crear tabla beneficio
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS beneficio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            partida TEXT,
            finca TEXT,
            maduro_total REAL DEFAULT 0.0,
            maduro_beneficio REAL DEFAULT 0.0,
            diferencia REAL DEFAULT 0.0,
            pergamino REAL DEFAULT 0.0,
            rendimiento REAL DEFAULT 0.0,
            imagen TEXT
        )
    """)

    # 2. Asegurar columna imagen si la tabla ya existía
    try:
        cursor.execute("ALTER TABLE beneficio ADD COLUMN imagen TEXT")
    except sqlite3.OperationalError:
        pass

    # 3. Crear tabla usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT,
            rol TEXT DEFAULT 'Usuario'
        )
    """)

    # 4. Insertar usuario administrador por defecto
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, ?)",
                       ('admin', 'admin123', 'Administrador', 'Admin'))

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# Rutas de Autenticación
# ---------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        user_data = cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()

        if user_data:
            user = User(id=user_data['id'], username=user_data['username'])
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Credenciales incorrectas', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))

# ---------------------------------------------------------
# Ruta Principal / Dashboard
# ---------------------------------------------------------
@app.route('/')
@app.route('/beneficio')
@app.route('/index')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    registros = cursor.execute("SELECT * FROM beneficio ORDER BY id DESC").fetchall()
    usuarios = cursor.execute("SELECT id, username, nombre, rol FROM usuarios ORDER BY id DESC").fetchall()
    conn.close()
    
    maduro_total = 0.0
    maduro_beneficio = 0.0
    pergamino_total = 0.0
    rendimientos = []

    for r in registros:
        row = dict(r)
        
        m_ing = float(row.get('maduro_total') or 0.0)
        maduro_total += m_ing

        m_ben = float(row.get('maduro_beneficio') or 0.0)
        maduro_beneficio += m_ben

        rend = float(row.get('rendimiento') or 0.0)
        if rend > 0:
            rendimientos.append(rend)

        p_fila = float(row.get('pergamino') or 0.0)
        if p_fila == 0.0 and m_ben > 0 and rend > 0:
            p_fila = m_ben / rend

        pergamino_total += p_fila

    rendimiento_promedio = (sum(rendimientos) / len(rendimientos)) if rendimientos else 0.0

    return render_template(
        'beneficio.html', 
        registros=registros, 
        usuarios=usuarios,
        maduro_total=round(maduro_total, 2),
        maduro_beneficio=round(maduro_beneficio, 2),
        total_pergamino=round(pergamino_total, 2),
        rendimiento_promedio=round(rendimiento_promedio, 2)
    )

# ---------------------------------------------------------
# Operaciones CRUD - Beneficio (Partidas)
# ---------------------------------------------------------
@app.route('/beneficio/nuevo', methods=['POST'])
@login_required
def nuevo_beneficio():
    fecha = request.form.get('fecha')
    partida = request.form.get('partida')
    finca = request.form.get('finca')
    maduro_total = float(request.form.get('maduro_total') or 0.0)
    maduro_beneficio = float(request.form.get('maduro_beneficio') or 0.0)
    diferencia = round(maduro_total - maduro_beneficio, 2)
    pergamino = float(request.form.get('pergamino') or 0.0)
    rendimiento = round(maduro_beneficio / pergamino, 2) if pergamino > 0 else 0.0

    file = request.files.get('imagen')
    filename = None
    if file and file.filename != '' and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"img_{int(time.time())}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO beneficio (fecha, partida, finca, maduro_total, maduro_beneficio, diferencia, pergamino, rendimiento, imagen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fecha, partida, finca, maduro_total, maduro_beneficio, diferencia, pergamino, rendimiento, filename))
    
    conn.commit()
    conn.close()
    
    flash('Partida registrada correctamente', 'success')
    return redirect(url_for('dashboard'))

@app.route('/beneficio/editar/<int:id>', methods=['POST'])
@login_required
def editar_beneficio(id):
    fecha = request.form.get('fecha')
    partida = request.form.get('partida')
    finca = request.form.get('finca')
    maduro_total = float(request.form.get('maduro_total') or 0.0)
    maduro_beneficio = float(request.form.get('maduro_beneficio') or 0.0)
    diferencia = round(maduro_total - maduro_beneficio, 2)
    pergamino = float(request.form.get('pergamino') or 0.0)
    rendimiento = round(maduro_beneficio / pergamino, 2) if pergamino > 0 else 0.0

    file = request.files.get('imagen')
    filename = None
    if file and file.filename != '' and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"img_{id}_{int(time.time())}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    if filename:
        cursor.execute("""
            UPDATE beneficio 
            SET fecha = ?, partida = ?, finca = ?, maduro_total = ?, maduro_beneficio = ?, 
                diferencia = ?, pergamino = ?, rendimiento = ?, imagen = ?
            WHERE id = ?
        """, (fecha, partida, finca, maduro_total, maduro_beneficio, diferencia, pergamino, rendimiento, filename, id))
    else:
        cursor.execute("""
            UPDATE beneficio 
            SET fecha = ?, partida = ?, finca = ?, maduro_total = ?, maduro_beneficio = ?, 
                diferencia = ?, pergamino = ?, rendimiento = ?
            WHERE id = ?
        """, (fecha, partida, finca, maduro_total, maduro_beneficio, diferencia, pergamino, rendimiento, id))
        
    conn.commit()
    conn.close()
    
    flash('Registro actualizado correctamente', 'success')
    return redirect(url_for('dashboard'))

@app.route('/beneficio/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_beneficio(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM beneficio WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    flash('Registro eliminado correctamente', 'danger')
    return redirect(url_for('dashboard'))

# ---------------------------------------------------------
# Operaciones CRUD - Gestión de Usuarios
# ---------------------------------------------------------
@app.route('/usuarios/crear', methods=['POST'])
@login_required
def crear_usuario():
    username = request.form.get('username')
    password = request.form.get('password')
    nombre = request.form.get('nombre')
    rol = request.form.get('rol') or 'Usuario'

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, ?)",
            (username, password, nombre, rol)
        )
        conn.commit()
        flash('Usuario creado exitosamente', 'success')
    except sqlite3.IntegrityError:
        flash('El nombre de usuario ya existe. Elige otro.', 'danger')
    finally:
        conn.close()

    return redirect(url_for('dashboard'))

@app.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_usuario(id):
    if hasattr(current_user, 'id') and current_user.id == id:
        flash('No puedes eliminar tu propia cuenta activa.', 'warning')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    flash('Usuario eliminado correctamente.', 'danger')
    return redirect(url_for('dashboard'))

# ---------------------------------------------------------
# Exportación a Excel
# ---------------------------------------------------------
@app.route('/exportar_excel')
@login_required
def exportar_excel():
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT fecha, partida, finca, maduro_total, maduro_beneficio, diferencia, pergamino, rendimiento 
        FROM beneficio 
        ORDER BY id DESC
    """, conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Beneficio')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='Registro_Beneficio_Cafe.xlsx'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)