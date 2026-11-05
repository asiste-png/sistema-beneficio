import sqlite3
from werkzeug.security import generate_password_hash

def get_db_connection():
    conn = sqlite3.connect('beneficio.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear tabla de usuarios si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'operador'
        )
    ''')
    
    # Intentar agregar columna 'rol' si la base de datos ya existía de antes
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'operador'")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Asegurar que el usuario admin tenga el rol de admin
    try:
        cursor.execute("UPDATE usuarios SET rol = 'admin' WHERE username = 'admin'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

# Ejecutar la inicialización siempre que se importe o inicie el módulo
init_db()