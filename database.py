import sqlite3
from werkzeug.security import generate_password_hash

def get_db_connection():
    conn = sqlite3.connect('beneficio.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear tabla usuarios si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'operador'
        )
    ''')

    # Forzar la inclusión de la columna 'rol' si la base de datos previa no la tenía
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'operador'")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Crear la tabla beneficio
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

    # Crear usuario admin por defecto si no existe
    admin_pass = generate_password_hash('admin123')
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (username, password, nombre, rol)
        VALUES (?, ?, ?, ?)
    ''', ('admin', admin_pass, 'Administrador', 'admin'))

    # Asegurar que el usuario admin tenga el rol 'admin'
    cursor.execute("UPDATE usuarios SET rol = 'admin' WHERE username = 'admin'")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()