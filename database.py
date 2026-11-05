import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('beneficio.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL
        )
    ''')

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

    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        pass_hash = generate_password_hash('admin123')
        cursor.execute("INSERT INTO usuarios (username, password, nombre) VALUES (?, ?, ?)", 
                       ('admin', pass_hash, 'Administrador'))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Base de datos e inicialización completada.")