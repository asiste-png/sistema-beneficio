import sqlite3

conn = sqlite3.connect('beneficio.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'operador'")
    cursor.execute("UPDATE usuarios SET rol = 'admin' WHERE username = 'admin'")
    conn.commit()
    print("✅ Columna 'rol' agregada exitosamente.")
except sqlite3.OperationalError as e:
    print(f"ℹ️ {e} (La columna ya existía)")
finally:
    conn.close()