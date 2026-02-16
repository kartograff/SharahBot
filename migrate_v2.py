import pg8000
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE

def add_column_if_not_exists(cur, table, column, definition):
    cur.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='{table}' AND column_name='{column}'
    """)
    if not cur.fetchone():
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"✅ Колонка {table}.{column} добавлена")
    else:
        print(f"⏩ Колонка {table}.{column} уже существует")

def main():
    conn = pg8000.connect(
        host=PG_HOST,
        port=int(PG_PORT),
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DATABASE
    )
    cur = conn.cursor()
    
    # Дополнительные поля пользователя
    add_column_if_not_exists(cur, 'users', 'email', 'TEXT')
    add_column_if_not_exists(cur, 'users', 'address', 'TEXT')
    add_column_if_not_exists(cur, 'users', 'birth_date', 'DATE')
    add_column_if_not_exists(cur, 'users', 'notes', 'TEXT')
    
    # Таблица для запланированных сообщений
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_messages (
            id SERIAL PRIMARY KEY,
            message TEXT NOT NULL,
            send_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )
    """)
    print("✅ Таблица scheduled_messages создана")
    
    conn.commit()
    cur.close()
    conn.close()
    print("🎉 Миграция завершена")

if __name__ == "__main__":
    main()