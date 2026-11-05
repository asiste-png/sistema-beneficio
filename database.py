import sqlite3
from werkzeug.security import generate_password_hash

def get_db_connection():
    conn = sqlite3.connect('beneficio.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Crear tabla de usuarios con la columna rol incorporada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'operador'
        )
    ''')

    # 2. Intentar agregar la columna 'rol' en caso de que la tabla ya existiera previamente
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'operador'")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # 3. Crear tabla de registros de beneficio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beneficio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            lote TEXT NOT NULL,
            quintales REAL NOT NULL,
            rendimiento REAL NOT NULL,
            observaciones TEXT
        )
    ''')

    # 4. Asegurar la existencia del usuario administrador por defecto
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    admin_user = cursor.fetchone()
    
    if not admin_user:
        admin_pass = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO usuarios (username, password, nombre, rol)
            VALUES (?, ?, ?, ?)
        ''', ('admin', admin_pass, 'Administrador', 'admin'))
    else:
        cursor.execute("UPDATE usuarios SET rol = 'admin' WHERE username = 'admin'")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()