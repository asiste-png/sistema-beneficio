from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db
import sqlite3
import pandas as pd
from io import BytesIO

# Inicializar Flask y la Base de Datos
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Inicializar la estructura de las tablas
init_db()

class User(UserMixin):
    def __init__(self, id, username, nombre, rol):
        self.id = id
        self.username = username
        self.nombre = nombre
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        user_data = cursor.execute("SELECT id, username, nombre, rol FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.OperationalError:
        # Si la columna 'rol' falla por algún motivo raro, consulta básica
        user_data = cursor.execute("SELECT id, username, nombre FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()

    if user_data:
        # Intentar leer rol, o asignar 'admin' por defecto
        rol = user_data['rol'] if 'rol' in user_data.keys() and user_data['rol'] else 'admin'
        return User(id=user_data['id'], username=user_data['username'], nombre=user_data['nombre'], rol=rol)
    return None

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
            # Asignación segura del rol
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

@app.route('/')
@login_required
def index():
    f_partida = request.args.get('f_partida', '').strip()
    f_finca = request.args.get('f_finca', '').strip()
    f_fecha_inicio = request.args.get('f_fecha_inicio', '').strip()
    f_fecha_fin = request.args.get('f_fecha_fin', '').strip()
    f_alerta = request.args.get('f_alerta', '').strip()

    conn = sqlite3.connect('beneficio.db')
    cursor = conn.cursor()

    query = "SELECT * FROM beneficio WHERE 1=1"
    params = []

    if f_partida:
        query += " AND no_partida LIKE ?"
        params.append(f'%{f_partida}%')
    if f_finca:
        query += " AND finca_beneficio LIKE ?"
        params.append(f'%{f_finca}%')
    if f_fecha_inicio:
        query += " AND fecha >= ?"
        params.append(f_fecha_inicio)
    if f_fecha_fin:
        query += " AND fecha <= ?"
        params.append(f_fecha_fin)
    if f_alerta:
        query += " AND estado_alerta = ?"
        params.append(f_alerta)

    query += " ORDER BY fecha DESC, id DESC"
    cursor.execute(query, params)
    registros = cursor.fetchall()

    total_maduro_ingresado = sum(r[4] for r in registros)
    total_maduro_beneficio = sum(r[5] for r in registros)
    total_diferencia = sum(r[6] for r in registros)
    total_pergamino = sum(r[7] for r in registros)
    rendimiento_promedio = round(total_maduro_beneficio / total_pergamino, 2) if total_pergamino > 0 else 0.0

    conn.close()

    return render_template(
        'beneficio.html',
        registros=registros,
        total_maduro_ingresado=round(total_maduro_ingresado, 2),
        total_maduro_beneficio=round(total_maduro_beneficio, 2),
        total_diferencia=round(total_diferencia, 2),
        total_pergamino=round(total_pergamino, 2),
        rendimiento_promedio=rendimiento_promedio,
        f_partida=f_partida,
        f_finca=f_finca,
        f_fecha_inicio=f_fecha_inicio,
        f_fecha_fin=f_fecha_fin,
        f_alerta=f_alerta
    )

@app.route('/beneficio', methods=['POST'])
@login_required
def guardar_beneficio():
    fecha = request.form['fecha']
    no_partida = request.form['no_partida']
    finca_beneficio = request.form['finca_beneficio']
    maduro_total = float(request.form['maduro_total'])
    maduro_beneficio = float(request.form['maduro_beneficio'])
    pergamino_partida = float(request.form['pergamino_partida'])
    qq_bodega = float(request.form.get('qq_bodega') or 0)
    envio = request.form.get('envio', '')

    diferencia = round(maduro_total - maduro_beneficio, 2)
    rendimiento = round(maduro_beneficio / pergamino_partida, 2) if pergamino_partida > 0 else 0

    if rendimiento < 4.0:
        alerta = "BAJO"
    elif rendimiento > 5.0:
        alerta = "ALTO"
    else:
        alerta = "OPTIMO"

    conn = sqlite3.connect('beneficio.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO beneficio (
            fecha, no_partida, finca_beneficio, maduro_total, maduro_beneficio, 
            diferencia, pergamino_partida, rendimiento, qq_bodega, envio, estado_alerta
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, no_partida, finca_beneficio, maduro_total, maduro_beneficio, 
          diferencia, pergamino_partida, rendimiento, qq_bodega, envio, alerta))
    conn.commit()
    conn.close()
    flash('Registro guardado correctamente', 'success')
    return redirect(url_for('index'))

@app.route('/exportar_excel')
@login_required
def exportar_excel():
    conn = sqlite3.connect('beneficio.db')
    df = pd.read_sql_query('''
        SELECT fecha AS Fecha, no_partida AS "No. Partida", finca_beneficio AS "Finca Beneficio",
               maduro_total AS "Total Maduro Ingresado", maduro_beneficio AS "Maduro Beneficio",
               diferencia AS Diferencia, pergamino_partida AS "qq Pergamino",
               rendimiento AS Rendimiento, qq_bodega AS "qq Bodega", envio AS "No. Envio",
               estado_alerta AS Alerta
        FROM beneficio ORDER BY id DESC
    ''', conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Beneficios')
    output.seek(0)

    return send_file(output, download_name="Reporte_Beneficio_Cafe.xlsx", as_attachment=True)

@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def gestion_usuarios():
    if current_user.rol != 'admin':
        flash('No tienes permisos para acceder a esta sección.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        nombre = request.form['nombre']
        rol = request.form.get('rol', 'operador')

        try:
            cursor.execute("INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, ?)",
                           (username, password, nombre, rol))
            conn.commit()
            flash('Usuario registrado exitosamente', 'success')
        except sqlite3.IntegrityError:
            flash('El nombre de usuario ya existe', 'danger')

    # Obtener la lista de usuarios para pasarla a la plantilla
    usuarios = cursor.execute("SELECT id, username, nombre, rol FROM usuarios").fetchall()
    conn.close()

    return render_template('usuarios.html', usuarios=usuarios)
class User(UserMixin):
    def __init__(self, id, username, nombre, rol):
        self.id = id
        self.username = username
        self.nombre = nombre
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    user_data = cursor.execute("SELECT id, username, nombre, rol FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], nombre=user_data['nombre'], rol=user_data['rol'])
    return None