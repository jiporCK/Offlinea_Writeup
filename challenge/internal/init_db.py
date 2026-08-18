import sqlite3

def read_flag():
    with open ("../../flag.txt",'r') as f:
        content = f.read()
    return content

def create_database_from_sql(db_filename):
    try:
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        sql_script = '''
        CREATE table IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            secret TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        '''
        cursor.executescript(sql_script)
        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
create_database_from_sql('history.db')
conn = sqlite3.connect('history.db')
query ="INSERT INTO secrets (name, secret) VALUES (?, ?)"
values = ('oldest_user_of_bartender', read_flag())
conn.execute(query, values)
conn.commit()
conn.close()