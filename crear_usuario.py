import sqlite3
from werkzeug.security import generate_password_hash

def crear_usuario(username, password, nombre):
    conn = sqlite3.connect('beneficio.db')
    cursor = conn.cursor()
    pass_hash = generate_password_hash(password)
    
    try:
        cursor.execute("INSERT INTO usuarios (username, password, nombre) VALUES (?, ?, ?)", 
                       (username, pass_hash, nombre))
        conn.commit()
        print(f"✅ Usuario '{username}' creado exitosamente.")
    except sqlite3.IntegrityError:
        print(f"❌ El nombre de usuario '{username}' ya existe.")
    finally:
        conn.close()

if __name__ == '__main__':
    # Modifica los datos que desees agregar aquí:
    crear_usuario('operador1', 'clave123', 'Operador de Beneficio')