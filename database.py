import pg8000
import pg8000.native
from datetime import datetime, timedelta
import json
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE

def get_connection():
    """Возвращает соединение с PostgreSQL через pg8000"""
    return pg8000.connect(
        host=PG_HOST,
        port=int(PG_PORT),
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DATABASE
    )

def dict_from_row(row, columns):
    """Преобразует кортеж строки в словарь с именами колонок"""
    if row is None:
        return None
    return dict(zip(columns, row))

def rows_to_dicts(rows, columns):
    """Преобразует список кортежей в список словарей"""
    return [dict_from_row(row, columns) for row in rows]

def init_db():
    """Создание всех таблиц, если их нет"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Пользователи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            registered_at TIMESTAMP,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    
    # Мастера
    cur.execute('''
        CREATE TABLE IF NOT EXISTS masters (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            specialization TEXT,
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP
        )
    ''')
    
    # Автомобили
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            brand TEXT,
            model TEXT,
            year INTEGER,
            vin TEXT,
            vehicle_type TEXT NOT NULL,
            tire_width INTEGER,
            tire_profile INTEGER,
            tire_diameter INTEGER,
            tire_season TEXT,
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    
    # Услуги
    cur.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            price_per_tire INTEGER,
            price_fixed INTEGER,
            min_price INTEGER,
            max_price INTEGER,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        )
    ''')
    
    # Записи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            service_id INTEGER REFERENCES services(id) ON DELETE SET NULL,
            car_id INTEGER REFERENCES cars(id) ON DELETE SET NULL,
            master_id INTEGER REFERENCES masters(id) ON DELETE SET NULL,
            quantity INTEGER DEFAULT 4,
            final_price INTEGER,
            appointment_time TIMESTAMP,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            notified INTEGER DEFAULT 0,
            notified_24h INTEGER DEFAULT 0,
            cancel_reason TEXT,
            transferred_from INTEGER,
            client_problem TEXT,
            status_history JSONB
        )
    ''')
    
    # Выполненные работы
    cur.execute('''
        CREATE TABLE IF NOT EXISTS completed_works (
            id SERIAL PRIMARY KEY,
            original_id INTEGER,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            service_id INTEGER,
            car_id INTEGER,
            master_id INTEGER,
            quantity INTEGER,
            final_price INTEGER,
            appointment_time TIMESTAMP,
            created_at TIMESTAMP,
            completed_at TIMESTAMP,
            cancel_reason TEXT,
            client_problem TEXT
        )
    ''')
    
    # Отзывы
    cur.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            appointment_id INTEGER NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Платежи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            appointment_id INTEGER NOT NULL,
            card_number TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )
    ''')
    
    # Администраторы
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            added_at TIMESTAMP,
            added_by BIGINT
        )
    ''')
    
    # Настройки
    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Закрытые периоды
    cur.execute('''
        CREATE TABLE IF NOT EXISTS closed_periods (
            id SERIAL PRIMARY KEY,
            period_type TEXT NOT NULL,
            day_of_week INTEGER,
            specific_date DATE,
            start_time TIME,
            end_time TIME,
            description TEXT
        )
    ''')
    
    # График работы
    cur.execute('''
        CREATE TABLE IF NOT EXISTS work_schedule (
            id SERIAL PRIMARY KEY,
            day_of_week INTEGER UNIQUE NOT NULL,
            is_working INTEGER DEFAULT 1,
            start_time TIME,
            end_time TIME,
            break_start TIME,
            break_end TIME
        )
    ''')
    
    # Карты компании
    cur.execute('''
        CREATE TABLE IF NOT EXISTS company_cards (
            id SERIAL PRIMARY KEY,
            card_number TEXT NOT NULL,
            card_holder TEXT,
            bank_name TEXT,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица для запланированных сообщений
    cur.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_messages (
            id SERIAL PRIMARY KEY,
            message TEXT NOT NULL,
            send_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Добавляем новые поля в users, если их нет (миграция)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
        print("Колонка email добавлена")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN address TEXT")
        print("Колонка address добавлена")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN birth_date DATE")
        print("Колонка birth_date добавлена")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN notes TEXT")
        print("Колонка notes добавлена")
    except Exception:
        pass
    
    # Заполнить стандартными услугами, если пусто
    cur.execute("SELECT COUNT(*) FROM services")
    count = cur.fetchone()[0]
    if count == 0:
        default_services = [
            ("Ремонт колеса", "Ремонт прокола или пореза шины", 500, None, 300, 1000, 1, 1),
            ("Сезонная замена шин", "Замена колёс с летней на зимнюю и наоборот", None, 1500, 1200, 1800, 1, 2),
            ("Сезонный шиномонтаж", "Полный шиномонтаж с балансировкой", None, 2000, 1500, 2500, 1, 3),
            ("Балансировка колес", "Балансировка одного колеса", 200, None, 150, 300, 1, 4)
        ]
        for s in default_services:
            cur.execute('''
                INSERT INTO services (name, description, price_per_tire, price_fixed, min_price, max_price, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', s)
    
    # Заполнить график работы по умолчанию
    cur.execute("SELECT COUNT(*) FROM work_schedule")
    count = cur.fetchone()[0]
    if count == 0:
        for day in range(7):
            is_working = 1 if day < 5 else 0  # Пн-Пт работаем, Сб-Вс выходные
            start_time = "09:00" if is_working else None
            end_time = "19:00" if is_working else None
            cur.execute('''
                INSERT INTO work_schedule (day_of_week, is_working, start_time, end_time)
                VALUES (%s, %s, %s, %s)
            ''', (day, is_working, start_time, end_time))
    
    conn.commit()
    cur.close()
    conn.close()
    print("База данных инициализирована")

# --- Пользователи ---
def add_user(user_id, username, full_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (user_id, username, full_name, registered_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    ''', (user_id, username, full_name, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

def update_user_phone(user_id, phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET phone=%s WHERE user_id=%s", (phone, user_id))
    conn.commit()
    cur.close()
    conn.close()

def ban_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned=1 WHERE user_id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def unban_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned=0 WHERE user_id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def is_user_banned(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_banned FROM users WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] == 1 if row else False

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, full_name, phone, registered_at, is_banned, email, address, birth_date, notes FROM users ORDER BY registered_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            'user_id': row[0],
            'username': row[1],
            'full_name': row[2],
            'phone': row[3],
            'registered_at': row[4],
            'is_banned': row[5],
            'email': row[6],
            'address': row[7],
            'birth_date': row[8],
            'notes': row[9]
        })
    return users

def get_all_users_ids():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]

def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, full_name, phone, registered_at, is_banned, email, address, birth_date, notes FROM users WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'full_name': row[2],
            'phone': row[3],
            'registered_at': row[4],
            'is_banned': row[5],
            'email': row[6],
            'address': row[7],
            'birth_date': row[8],
            'notes': row[9]
        }
    return None

# --- Администраторы ---
def add_admin(user_id, added_by):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO admins (user_id, added_at, added_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    ''', (user_id, datetime.now(), added_by))
    conn.commit()
    cur.close()
    conn.close()

def remove_admin(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM admins WHERE user_id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_all_admins():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.user_id, u.username, u.full_name, a.added_at, a.added_by
        FROM admins a
        LEFT JOIN users u ON a.user_id = u.user_id
        ORDER BY a.added_at DESC
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    admins = []
    for row in rows:
        admins.append({
            'user_id': row[0],
            'username': row[1],
            'full_name': row[2],
            'added_at': row[3],
            'added_by': row[4]
        })
    return admins

def is_admin_db(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None

# --- Мастера ---
def add_master(name, specialization=None, phone=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO masters (name, specialization, phone, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    ''', (name, specialization, phone, datetime.now()))
    master_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return master_id

def get_all_masters(active_only=True):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT id, name, specialization, phone, is_active, created_at FROM masters"
    if active_only:
        query += " WHERE is_active=1"
    query += " ORDER BY name"
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'specialization': r[2], 'phone': r[3], 'is_active': r[4], 'created_at': r[5]} for r in rows]

def get_master_by_id(master_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, specialization, phone, is_active FROM masters WHERE id=%s", (master_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'specialization': row[2], 'phone': row[3], 'is_active': row[4]}
    return None

def update_master(master_id, name=None, specialization=None, phone=None, is_active=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    params = []
    if name is not None:
        fields.append("name=%s")
        params.append(name)
    if specialization is not None:
        fields.append("specialization=%s")
        params.append(specialization)
    if phone is not None:
        fields.append("phone=%s")
        params.append(phone)
    if is_active is not None:
        fields.append("is_active=%s")
        params.append(is_active)
    if fields:
        query = f"UPDATE masters SET {', '.join(fields)} WHERE id=%s"
        params.append(master_id)
        cur.execute(query, tuple(params))
        conn.commit()
    cur.close()
    conn.close()

def delete_master(master_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM masters WHERE id=%s", (master_id,))
    conn.commit()
    cur.close()
    conn.close()

def assign_master_to_appointment(appointment_id, master_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET master_id=%s WHERE id=%s", (master_id, appointment_id))
    conn.commit()
    cur.close()
    conn.close()

def get_available_masters_for_service(service_id, appointment_time):
    masters = get_all_masters(active_only=True)
    conn = get_connection()
    cur = conn.cursor()
    date_str = appointment_time.date().isoformat() if appointment_time else None
    result = []
    for master in masters:
        if date_str:
            cur.execute('''
                SELECT COUNT(*) FROM appointments
                WHERE master_id=%s AND date(appointment_time)=%s AND status NOT IN ('cancelled', 'completed')
            ''', (master['id'], date_str))
            count = cur.fetchone()[0]
        else:
            count = 0
        result.append((master, count))
    cur.close()
    conn.close()
    result.sort(key=lambda x: x[1])
    return [r[0] for r in result]

# --- Автомобили ---
def add_car(user_id, brand, model, year, vin, vehicle_type, tire_width, tire_profile, tire_diameter, tire_season, is_default=False):
    conn = get_connection()
    cur = conn.cursor()
    if is_default:
        cur.execute("UPDATE cars SET is_default=0 WHERE user_id=%s", (user_id,))
    cur.execute('''
        INSERT INTO cars (user_id, brand, model, year, vin, vehicle_type, tire_width, tire_profile, tire_diameter, tire_season, is_default, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (user_id, brand, model, year, vin, vehicle_type, tire_width, tire_profile, tire_diameter, tire_season, int(is_default), datetime.now()))
    car_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return car_id

def get_user_cars(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, brand, model, year, vin, vehicle_type, tire_width, tire_profile, tire_diameter, tire_season, is_default
        FROM cars WHERE user_id=%s ORDER BY is_default DESC, created_at
    ''', (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cars = []
    for row in rows:
        cars.append({
            'id': row[0],
            'brand': row[1],
            'model': row[2],
            'year': row[3],
            'vin': row[4],
            'vehicle_type': row[5],
            'tire_width': row[6],
            'tire_profile': row[7],
            'tire_diameter': row[8],
            'tire_season': row[9],
            'is_default': row[10]
        })
    return cars

def get_car(car_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, user_id, brand, model, year, vin, vehicle_type, tire_width, tire_profile, tire_diameter, tire_season, is_default
        FROM cars WHERE id=%s
    ''', (car_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {
            'id': row[0],
            'user_id': row[1],
            'brand': row[2],
            'model': row[3],
            'year': row[4],
            'vin': row[5],
            'vehicle_type': row[6],
            'tire_width': row[7],
            'tire_profile': row[8],
            'tire_diameter': row[9],
            'tire_season': row[10],
            'is_default': row[11]
        }
    return None

def delete_car(car_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cars WHERE id=%s AND user_id=%s", (car_id, user_id))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    return deleted

def set_default_car(car_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cars SET is_default=0 WHERE user_id=%s", (user_id,))
    cur.execute("UPDATE cars SET is_default=1 WHERE id=%s AND user_id=%s", (car_id, user_id))
    updated = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    return updated

def update_car(car_id, brand=None, model=None, year=None, vin=None, vehicle_type=None,
               tire_width=None, tire_profile=None, tire_diameter=None, tire_season=None,
               is_default=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    params = []
    if brand is not None:
        fields.append("brand=%s")
        params.append(brand)
    if model is not None:
        fields.append("model=%s")
        params.append(model)
    if year is not None:
        fields.append("year=%s")
        params.append(year)
    if vin is not None:
        fields.append("vin=%s")
        params.append(vin)
    if vehicle_type is not None:
        fields.append("vehicle_type=%s")
        params.append(vehicle_type)
    if tire_width is not None:
        fields.append("tire_width=%s")
        params.append(tire_width)
    if tire_profile is not None:
        fields.append("tire_profile=%s")
        params.append(tire_profile)
    if tire_diameter is not None:
        fields.append("tire_diameter=%s")
        params.append(tire_diameter)
    if tire_season is not None:
        fields.append("tire_season=%s")
        params.append(tire_season)
    if is_default is not None:
        fields.append("is_default=%s")
        params.append(is_default)
    if fields:
        query = f"UPDATE cars SET {', '.join(fields)} WHERE id=%s"
        params.append(car_id)
        cur.execute(query, tuple(params))
        conn.commit()
    cur.close()
    conn.close()

# --- Услуги ---
def get_active_services():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, description, price_per_tire, price_fixed, min_price, max_price
        FROM services WHERE is_active=1 ORDER BY sort_order
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    services = []
    for row in rows:
        services.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'price_per_tire': row[3],
            'price_fixed': row[4],
            'min_price': row[5],
            'max_price': row[6]
        })
    return services

def get_service(service_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, price_per_tire, price_fixed, min_price, max_price FROM services WHERE id=%s
    ''', (service_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {
            'id': row[0],
            'name': row[1],
            'price_per_tire': row[2],
            'price_fixed': row[3],
            'min_price': row[4],
            'max_price': row[5]
        }
    return None

def get_all_services():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, price_per_tire, price_fixed, min_price, max_price, is_active, sort_order FROM services ORDER BY sort_order")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    services = []
    for row in rows:
        services.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'price_per_tire': row[3],
            'price_fixed': row[4],
            'min_price': row[5],
            'max_price': row[6],
            'is_active': row[7],
            'sort_order': row[8]
        })
    return services

def update_service(service_id, name=None, description=None, price_per_tire=None, price_fixed=None, min_price=None, max_price=None, is_active=None, sort_order=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    params = []
    if name is not None:
        fields.append("name=%s")
        params.append(name)
    if description is not None:
        fields.append("description=%s")
        params.append(description)
    if price_per_tire is not None:
        fields.append("price_per_tire=%s")
        params.append(price_per_tire)
    if price_fixed is not None:
        fields.append("price_fixed=%s")
        params.append(price_fixed)
    if min_price is not None:
        fields.append("min_price=%s")
        params.append(min_price)
    if max_price is not None:
        fields.append("max_price=%s")
        params.append(max_price)
    if is_active is not None:
        fields.append("is_active=%s")
        params.append(is_active)
    if sort_order is not None:
        fields.append("sort_order=%s")
        params.append(sort_order)
    if fields:
        query = f"UPDATE services SET {', '.join(fields)} WHERE id=%s"
        params.append(service_id)
        cur.execute(query, tuple(params))
        conn.commit()
    cur.close()
    conn.close()

def add_service(name, description, price_per_tire, price_fixed, min_price, max_price, sort_order=None):
    conn = get_connection()
    cur = conn.cursor()
    if sort_order is None:
        cur.execute("SELECT MAX(sort_order) FROM services")
        max_order = cur.fetchone()[0] or 0
        sort_order = max_order + 1
    cur.execute('''
        INSERT INTO services (name, description, price_per_tire, price_fixed, min_price, max_price, sort_order)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (name, description, price_per_tire, price_fixed, min_price, max_price, sort_order))
    service_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return service_id

def delete_service(service_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM services WHERE id=%s", (service_id,))
    conn.commit()
    cur.close()
    conn.close()

# --- Записи ---
def create_appointment(user_id, service_id, car_id, quantity, appointment_time, client_problem=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT name, price_per_tire, price_fixed FROM services WHERE id=%s', (service_id,))
    service = cur.fetchone()
    if not service:
        raise ValueError("Услуга не найдена")
    
    service_name, price_per_tire, price_fixed = service
    
    if price_fixed is not None:
        final_price = price_fixed
    elif price_per_tire is not None:
        final_price = price_per_tire * quantity
    else:
        final_price = 0  # Будет уточнена позже
    
    cur.execute('''
        INSERT INTO appointments
        (user_id, service_id, car_id, quantity, final_price, appointment_time, created_at, client_problem)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (user_id, service_id, car_id, quantity, final_price, appointment_time, datetime.now(), client_problem))
    app_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return app_id

def get_user_appointments(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.id, s.name as service_name, a.final_price, c.vehicle_type, c.tire_diameter, a.quantity,
               a.appointment_time, a.status, a.cancel_reason, a.master_id, a.client_problem, a.status_history
        FROM appointments a
        LEFT JOIN services s ON a.service_id = s.id
        LEFT JOIN cars c ON a.car_id = c.id
        WHERE a.user_id=%s ORDER BY a.appointment_time DESC
    ''', (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    appointments = []
    for row in rows:
        status_history = row[11]
        if status_history and isinstance(status_history, str):
            try:
                status_history = json.loads(status_history)
            except:
                status_history = []
        else:
            status_history = []
        appointments.append({
            'id': row[0],
            'service_name': row[1],
            'final_price': row[2],
            'vehicle_type': row[3],
            'tire_diameter': row[4],
            'quantity': row[5],
            'appointment_time': row[6],
            'status': row[7],
            'cancel_reason': row[8],
            'master_id': row[9],
            'client_problem': row[10],
            'status_history': status_history
        })
    return appointments

def get_appointment(appointment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.id, a.user_id, a.service_id, a.car_id, a.quantity, a.final_price, a.appointment_time,
               a.status, a.cancel_reason, a.master_id, a.client_problem, a.status_history
        FROM appointments a WHERE a.id=%s
    ''', (appointment_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        status_history = row[11]
        if status_history and isinstance(status_history, str):
            try:
                status_history = json.loads(status_history)
            except:
                status_history = []
        else:
            status_history = []
        return {
            'id': row[0],
            'user_id': row[1],
            'service_id': row[2],
            'car_id': row[3],
            'quantity': row[4],
            'final_price': row[5],
            'appointment_time': row[6],
            'status': row[7],
            'cancel_reason': row[8],
            'master_id': row[9],
            'client_problem': row[10],
            'status_history': status_history
        }
    return None

def get_appointments_by_date(date_str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.id, a.user_id, a.service_id, a.final_price, a.car_id, a.quantity, a.appointment_time, a.status,
               a.master_id, a.client_problem
        FROM appointments a
        WHERE date(a.appointment_time)=%s
        ORDER BY a.appointment_time
    ''', (date_str,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    appointments = []
    for row in rows:
        appointments.append({
            'id': row[0],
            'user_id': row[1],
            'service_id': row[2],
            'final_price': row[3],
            'car_id': row[4],
            'quantity': row[5],
            'appointment_time': row[6],
            'status': row[7],
            'master_id': row[8],
            'client_problem': row[9]
        })
    return appointments

def get_filtered_appointments(filters):
    conn = get_connection()
    cur = conn.cursor()
    query = '''
        SELECT a.id, u.user_id, u.full_name, u.username, u.phone,
               s.name as service_name, a.final_price, c.vehicle_type, c.tire_diameter,
               a.appointment_time, a.status, a.master_id, a.client_problem
        FROM appointments a
        LEFT JOIN users u ON a.user_id = u.user_id
        LEFT JOIN services s ON a.service_id = s.id
        LEFT JOIN cars c ON a.car_id = c.id
        WHERE 1=1
    '''
    params = []
    if filters.get('date_from'):
        query += " AND date(a.appointment_time) >= %s"
        params.append(filters['date_from'])
    if filters.get('date_to'):
        query += " AND date(a.appointment_time) <= %s"
        params.append(filters['date_to'])
    if filters.get('status'):
        query += " AND a.status = %s"
        params.append(filters['status'])
    if filters.get('service'):
        query += " AND s.name = %s"
        params.append(filters['service'])
    if filters.get('user'):
        query += " AND (u.full_name ILIKE %s OR u.username ILIKE %s OR u.phone ILIKE %s)"
        params.extend([f'%{filters["user"]}%'] * 3)
    query += " ORDER BY a.appointment_time DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    appointments = []
    for row in rows:
        appointments.append({
            'id': row[0],
            'user_id': row[1],
            'full_name': row[2],
            'username': row[3],
            'phone': row[4],
            'service_name': row[5],
            'final_price': row[6],
            'vehicle_type': row[7],
            'tire_diameter': row[8],
            'appointment_time': row[9],
            'status': row[10],
            'master_id': row[11],
            'client_problem': row[12]
        })
    return appointments

def update_appointment_status(appointment_id, status, cancel_reason=None):
    conn = get_connection()
    cur = conn.cursor()
    if cancel_reason:
        cur.execute("UPDATE appointments SET status=%s, cancel_reason=%s WHERE id=%s", (status, cancel_reason, appointment_id))
    else:
        cur.execute("UPDATE appointments SET status=%s WHERE id=%s", (status, appointment_id))
    conn.commit()
    cur.close()
    conn.close()

def update_appointment_status_with_history(appointment_id, new_status, changed_by=None, comment=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, status_history FROM appointments WHERE id=%s", (appointment_id,))
    row = cur.fetchone()
    if not row:
        return None
    old_status, history = row[0], row[1] or []
    new_entry = {
        'status': new_status,
        'changed_at': datetime.now().isoformat(),
        'changed_by': changed_by,
        'comment': comment
    }
    if history is None:
        history = [new_entry]
    else:
        if isinstance(history, str):
            try:
                history = json.loads(history)
            except:
                history = []
        history.append(new_entry)
    cur.execute("UPDATE appointments SET status=%s, status_history=%s WHERE id=%s", (new_status, json.dumps(history), appointment_id))
    conn.commit()
    cur.close()
    conn.close()
    return get_appointment(appointment_id)

def cancel_appointment(appointment_id, user_id, reason=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM appointments WHERE id=%s", (appointment_id,))
    row = cur.fetchone()
    if row and row[0] == user_id:
        cur.execute("UPDATE appointments SET status='cancelled', cancel_reason=%s WHERE id=%s", (reason, appointment_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    cur.close()
    conn.close()
    return False

def transfer_appointment(appointment_id, new_time):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET appointment_time=%s, status='pending' WHERE id=%s", (new_time, appointment_id))
    conn.commit()
    cur.close()
    conn.close()

def get_booked_slots(date_str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT to_char(appointment_time, 'HH24:MI') as time
        FROM appointments
        WHERE date(appointment_time)=%s AND status!='cancelled'
    ''', (date_str,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0] for row in rows}

def complete_appointment(appointment_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT id, user_id, service_id, car_id, master_id, quantity, final_price, appointment_time, created_at, cancel_reason, client_problem
            FROM appointments WHERE id=%s
        ''', (appointment_id,))
        app = cur.fetchone()
        if not app:
            return False
        cur.execute('''
            INSERT INTO completed_works
            (original_id, user_id, service_id, car_id, master_id, quantity, final_price, appointment_time, created_at, completed_at, cancel_reason, client_problem)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (app[0], app[1], app[2], app[3], app[4], app[5], app[6], app[7], app[8], datetime.now(), app[9], app[10]))
        cur.execute("DELETE FROM appointments WHERE id=%s", (appointment_id,))
        conn.commit()
        return True
    except Exception as e:
        print("Ошибка при завершении записи:", e)
        return False
    finally:
        cur.close()
        conn.close()

def get_completed_works():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT w.id, s.name as service_name, w.final_price, c.vehicle_type, c.tire_diameter,
               w.appointment_time, w.completed_at, u.full_name, u.username, u.phone,
               w.user_id, w.master_id
        FROM completed_works w
        LEFT JOIN users u ON w.user_id = u.user_id
        LEFT JOIN services s ON w.service_id = s.id
        LEFT JOIN cars c ON w.car_id = c.id
        ORDER BY w.completed_at DESC
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    works = []
    for row in rows:
        works.append({
            'id': row[0],
            'service_name': row[1],
            'final_price': row[2],
            'vehicle_type': row[3],
            'tire_diameter': row[4],
            'appointment_time': row[5],
            'completed_at': row[6],
            'full_name': row[7],
            'username': row[8],
            'phone': row[9],
            'user_id': row[10],
            'master_id': row[11]
        })
    return works

# --- Отзывы ---
def add_review(user_id, appointment_id, rating, comment):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO reviews (user_id, appointment_id, rating, comment, created_at)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_id, appointment_id, rating, comment, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

def get_reviews_for_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT r.id, s.name, r.rating, r.comment, r.created_at
        FROM reviews r
        JOIN appointments a ON r.appointment_id = a.id
        JOIN services s ON a.service_id = s.id
        WHERE r.user_id=%s
        ORDER BY r.created_at DESC
    ''', (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    reviews = []
    for row in rows:
        reviews.append({
            'id': row[0],
            'name': row[1],
            'rating': row[2],
            'comment': row[3],
            'created_at': row[4]
        })
    return reviews

def has_review(appointment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM reviews WHERE appointment_id=%s", (appointment_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None

# --- Платежи ---
def save_payment(user_id, appointment_id, card_number):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO payments (user_id, appointment_id, card_number, status, created_at)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_id, appointment_id, card_number, 'pending', datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

def get_pending_payments():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT p.id, u.full_name, u.username, p.appointment_id, p.card_number, p.created_at, p.user_id
        FROM payments p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.status = 'pending'
        ORDER BY p.created_at DESC
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    payments = []
    for row in rows:
        payments.append({
            'id': row[0],
            'full_name': row[1],
            'username': row[2],
            'appointment_id': row[3],
            'card_number': row[4],
            'created_at': row[5],
            'user_id': row[6]
        })
    return payments

def mark_payment_paid(payment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE payments SET status='paid' WHERE id=%s", (payment_id,))
    conn.commit()
    cur.close()
    conn.close()

# --- Уведомления ---
def get_pending_notifications():
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    hour_later = now + timedelta(hours=1)
    cur.execute('''
        SELECT id, user_id, appointment_time FROM appointments
        WHERE status='confirmed' AND notified=0 AND appointment_time BETWEEN %s AND %s
    ''', (now, hour_later))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    notifications = []
    for row in rows:
        notifications.append({
            'id': row[0],
            'user_id': row[1],
            'appointment_time': row[2]
        })
    return notifications

def mark_notified(appointment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET notified=1 WHERE id=%s", (appointment_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_notifications_24h():
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    cur.execute('''
        SELECT id, user_id, appointment_time FROM appointments
        WHERE status='confirmed' AND notified_24h=0 AND appointment_time BETWEEN %s AND %s
    ''', (now, tomorrow))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    notifications = []
    for row in rows:
        notifications.append({
            'id': row[0],
            'user_id': row[1],
            'appointment_time': row[2]
        })
    return notifications

def mark_notified_24h(appointment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET notified_24h=1 WHERE id=%s", (appointment_id,))
    conn.commit()
    cur.close()
    conn.close()

# --- Статистика ---
def _apply_period_filter(base_query, period):
    now = datetime.now()
    params = []
    if period == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = base_query + " AND appointment_time >= %s"
        params.append(start)
    elif period == 'week':
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        query = base_query + " AND appointment_time >= %s"
        params.append(start)
    elif period == 'month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query = base_query + " AND appointment_time >= %s"
        params.append(start)
    elif period == 'year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        query = base_query + " AND appointment_time >= %s"
        params.append(start)
    else:
        query = base_query
        params = []
    return query, params

def get_statistics(period='month'):
    conn = get_connection()
    cur = conn.cursor()
    base_query = '''
        SELECT 
            COUNT(*) as total_appointments,
            SUM(CASE WHEN status='confirmed' OR status='completed' THEN final_price ELSE 0 END) as total_revenue,
            COUNT(CASE WHEN status='confirmed' OR status='completed' THEN 1 END) as completed_count,
            COUNT(CASE WHEN status='cancelled' THEN 1 END) as cancelled_count
        FROM appointments
        WHERE 1=1
    '''
    query, params = _apply_period_filter(base_query, period)
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {
        'total': row[0] or 0,
        'revenue': row[1] or 0,
        'completed': row[2] or 0,
        'cancelled': row[3] or 0
    }

def get_popular_services(period='month'):
    conn = get_connection()
    cur = conn.cursor()
    base_query = '''
        SELECT s.name, COUNT(*) as cnt
        FROM appointments a
        JOIN services s ON a.service_id = s.id
        WHERE a.status IN ('confirmed', 'completed')
    '''
    query, params = _apply_period_filter(base_query, period)
    query += " GROUP BY s.name ORDER BY cnt DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'name': r[0], 'cnt': r[1]} for r in rows]

def get_weekday_distribution(period='month'):
    conn = get_connection()
    cur = conn.cursor()
    base_query = '''
        SELECT EXTRACT(DOW FROM appointment_time) as weekday, COUNT(*) as cnt
        FROM appointments
        WHERE status IN ('confirmed', 'completed')
    '''
    query, params = _apply_period_filter(base_query, period)
    query += " GROUP BY weekday ORDER BY weekday"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'weekday': int(r[0]), 'cnt': r[1]} for r in rows]

def get_hour_distribution(period='month'):
    conn = get_connection()
    cur = conn.cursor()
    base_query = '''
        SELECT EXTRACT(HOUR FROM appointment_time) as hour, COUNT(*) as cnt
        FROM appointments
        WHERE status IN ('confirmed', 'completed')
    '''
    query, params = _apply_period_filter(base_query, period)
    query += " GROUP BY hour ORDER BY hour"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'hour': int(r[0]), 'cnt': r[1]} for r in rows]

def get_average_check(period='month'):
    conn = get_connection()
    cur = conn.cursor()
    base_query = '''
        SELECT AVG(final_price) as avg_check
        FROM appointments
        WHERE status IN ('confirmed', 'completed')
    '''
    query, params = _apply_period_filter(base_query, period)
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row and row[0] else 0

# --- Настройки ---
def get_setting(key, default=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=%s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=%s",
        (key, value, value)
    )
    conn.commit()
    cur.close()
    conn.close()

# --- Закрытые периоды ---
def add_closed_period(period_type, day_of_week=None, specific_date=None, start_time=None, end_time=None, description=''):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO closed_periods (period_type, day_of_week, specific_date, start_time, end_time, description)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (period_type, day_of_week, specific_date, start_time, end_time, description))
    period_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return period_id

def get_all_closed_periods():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, period_type, day_of_week, specific_date, start_time, end_time, description FROM closed_periods ORDER BY id')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    periods = []
    for row in rows:
        periods.append({
            'id': row[0],
            'period_type': row[1],
            'day_of_week': row[2],
            'specific_date': row[3],
            'start_time': str(row[4]) if row[4] else None,
            'end_time': str(row[5]) if row[5] else None,
            'description': row[6]
        })
    return periods

def delete_closed_period(period_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM closed_periods WHERE id=%s", (period_id,))
    conn.commit()
    cur.close()
    conn.close()

def is_time_slot_available(date_str, time_str):
    from datetime import datetime
    if len(time_str) == 2:
        time_str += ":00"
    try:
        slot_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return False
    weekday = slot_datetime.weekday()
    slot_time = slot_datetime.time()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT start_time, end_time FROM closed_periods
        WHERE period_type='once' AND specific_date=%s
    ''', (date_str,))
    rows = cur.fetchall()
    for row in rows:
        if row[0] is None and row[1] is None:
            cur.close()
            conn.close()
            return False
        if row[0] and row[1]:
            if row[0] <= slot_time <= row[1]:
                cur.close()
                conn.close()
                return False
    cur.execute('''
        SELECT start_time, end_time FROM closed_periods
        WHERE period_type='weekly' AND day_of_week=%s
    ''', (weekday,))
    rows = cur.fetchall()
    for row in rows:
        if row[0] is None and row[1] is None:
            cur.close()
            conn.close()
            return False
        if row[0] and row[1]:
            if row[0] <= slot_time <= row[1]:
                cur.close()
                conn.close()
                return False
    cur.close()
    conn.close()
    return True

# --- График работы ---
def get_work_schedule():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, day_of_week, is_working, start_time, end_time, break_start, break_end
        FROM work_schedule ORDER BY day_of_week
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    schedule = []
    for row in rows:
        schedule.append({
            'id': row[0],
            'day_of_week': row[1],
            'is_working': row[2],
            'start_time': str(row[3]) if row[3] else None,
            'end_time': str(row[4]) if row[4] else None,
            'break_start': str(row[5]) if row[5] else None,
            'break_end': str(row[6]) if row[6] else None
        })
    return schedule

def update_work_schedule(day_of_week, is_working, start_time=None, end_time=None, break_start=None, break_end=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM work_schedule WHERE day_of_week=%s", (day_of_week,))
    existing = cur.fetchone()
    if existing:
        cur.execute('''
            UPDATE work_schedule SET
                is_working=%s,
                start_time=%s,
                end_time=%s,
                break_start=%s,
                break_end=%s
            WHERE day_of_week=%s
        ''', (is_working, start_time, end_time, break_start, break_end, day_of_week))
    else:
        cur.execute('''
            INSERT INTO work_schedule (day_of_week, is_working, start_time, end_time, break_start, break_end)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (day_of_week, is_working, start_time, end_time, break_start, break_end))
    conn.commit()
    cur.close()
    conn.close()

# --- Карты компании ---
def get_active_cards():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, card_number, card_holder, bank_name, is_active, sort_order
        FROM company_cards WHERE is_active=1 ORDER BY sort_order
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cards = []
    for row in rows:
        cards.append({
            'id': row[0],
            'card_number': row[1],
            'card_holder': row[2],
            'bank_name': row[3],
            'is_active': row[4],
            'sort_order': row[5]
        })
    return cards

def add_card(card_number, card_holder, bank_name, sort_order=None):
    conn = get_connection()
    cur = conn.cursor()
    if sort_order is None:
        cur.execute("SELECT MAX(sort_order) FROM company_cards")
        max_order = cur.fetchone()[0] or 0
        sort_order = max_order + 1
    cur.execute('''
        INSERT INTO company_cards (card_number, card_holder, bank_name, sort_order)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    ''', (card_number, card_holder, bank_name, sort_order))
    card_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return card_id

def delete_card(card_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM company_cards WHERE id=%s", (card_id,))
    conn.commit()
    cur.close()
    conn.close()

def update_card(card_id, card_number=None, card_holder=None, bank_name=None, is_active=None, sort_order=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    params = []
    if card_number is not None:
        fields.append("card_number=%s")
        params.append(card_number)
    if card_holder is not None:
        fields.append("card_holder=%s")
        params.append(card_holder)
    if bank_name is not None:
        fields.append("bank_name=%s")
        params.append(bank_name)
    if is_active is not None:
        fields.append("is_active=%s")
        params.append(is_active)
    if sort_order is not None:
        fields.append("sort_order=%s")
        params.append(sort_order)
    if fields:
        query = f"UPDATE company_cards SET {', '.join(fields)} WHERE id=%s"
        params.append(card_id)
        cur.execute(query, tuple(params))
        conn.commit()
    cur.close()
    conn.close()

# --- Функции для временных слотов ---
def get_all_time_slots_for_date(date_str):
    """Возвращает список всех возможных временных слотов для указанной даты на основе графика работы."""
    from datetime import datetime, time, timedelta
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []
    weekday = date_obj.weekday()
    schedule = get_work_schedule()
    day_schedule = None
    for day in schedule:
        if day['day_of_week'] == weekday:
            day_schedule = day
            break
    if not day_schedule or day_schedule['is_working'] == 0:
        return []
    try:
        start = datetime.strptime(day_schedule['start_time'], "%H:%M").time()
        end = datetime.strptime(day_schedule['end_time'], "%H:%M").time()
    except (TypeError, ValueError):
        start = time(9, 0)
        end = time(19, 0)
    all_times = []
    current = datetime.combine(date_obj, start)
    end_dt = datetime.combine(date_obj, end)
    while current <= end_dt:
        all_times.append(current.strftime("%H:%M"))
        current += timedelta(minutes=30)
    return all_times

def get_available_time_slots(date_str):
    """Возвращает список доступных слотов (не занятых, не прошедших) для указанной даты."""
    from datetime import datetime, time, timedelta
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []
    today = datetime.now().date()
    now_time = datetime.now().time()
    all_times = get_all_time_slots_for_date(date_str)
    if not all_times:
        return []
    booked = get_booked_slots(date_str)
    available = []
    for t in all_times:
        slot_time = datetime.strptime(t, "%H:%M").time()
        if date_obj.date() == today and slot_time <= now_time:
            continue
        if t not in booked and is_time_slot_available(date_str, t):
            available.append(t)
    return available

# --- Дополнительные данные пользователя ---
def update_user(user_id, email=None, address=None, birth_date=None, notes=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    params = []
    if email is not None:
        fields.append("email=%s")
        params.append(email)
    if address is not None:
        fields.append("address=%s")
        params.append(address)
    if birth_date is not None:
        fields.append("birth_date=%s")
        params.append(birth_date)
    if notes is not None:
        fields.append("notes=%s")
        params.append(notes)
    if fields:
        query = f"UPDATE users SET {', '.join(fields)} WHERE user_id=%s"
        params.append(user_id)
        cur.execute(query, tuple(params))
        conn.commit()
    cur.close()
    conn.close()

# --- Запланированные сообщения ---
def schedule_message(message, send_at):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO scheduled_messages (message, send_at, created_at)
        VALUES (%s, %s, %s)
        RETURNING id
    ''', (message, send_at, datetime.now()))
    msg_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return msg_id

def get_pending_scheduled_messages():
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    cur.execute('''
        SELECT id, message FROM scheduled_messages
        WHERE status='pending' AND send_at <= %s
    ''', (now,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def mark_scheduled_message_sent(msg_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE scheduled_messages SET status='sent' WHERE id=%s", (msg_id,))
    conn.commit()
    cur.close()
    conn.close()