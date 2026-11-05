import sqlite3

def init_db():
    conn = sqlite3.connect('beneficio.db')
    cursor = conn.cursor()
    
    # Crear tabla de usuarios con columna de rol
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'operador'
        )
    ''')
    conn.commit()
    conn.close()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beneficio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            no_partida TEXT NOT NULL,
            finca_beneficio TEXT NOT NULL,
            maduro_total REAL NOT NULL,
            maduro_beneficio REAL NOT NULL,
            diferencia REAL NOT NULL,
            pergamino_partida REAL NOT NULL,
            rendimiento REAL NOT NULL,
            qq_bodega REAL,
            envio TEXT,
            estado_alerta TEXT NOT NULL
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_partida ON beneficio(no_partida)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_finca ON beneficio(finca_beneficio)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fecha ON beneficio(fecha)')

from werkzeug.security import generate_password_hash
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('beneficio.db')
    conn.row_factory = sqlite3.Row
    return conn

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Base de datos e inicialización completada.")