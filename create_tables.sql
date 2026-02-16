-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    registered_at TIMESTAMP,
    is_banned INTEGER DEFAULT 0
);

-- Автомобили
CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    brand TEXT,
    model TEXT,
    year INTEGER,
    vehicle_type TEXT NOT NULL,
    tire_width INTEGER,
    tire_profile INTEGER,
    tire_diameter INTEGER,
    tire_season TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP
);

-- Услуги
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    price_per_tire INTEGER,
    price_fixed INTEGER,
    is_active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);

-- Записи
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES services(id) ON DELETE SET NULL,
    car_id INTEGER REFERENCES cars(id) ON DELETE SET NULL,
    quantity INTEGER DEFAULT 4,
    final_price INTEGER,
    appointment_time TIMESTAMP,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP,
    notified INTEGER DEFAULT 0,
    notified_24h INTEGER DEFAULT 0,
    cancel_reason TEXT,
    transferred_from INTEGER
);

-- Выполненные работы
CREATE TABLE IF NOT EXISTS completed_works (
    id SERIAL PRIMARY KEY,
    original_id INTEGER,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    service_id INTEGER,
    car_id INTEGER,
    quantity INTEGER,
    final_price INTEGER,
    appointment_time TIMESTAMP,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancel_reason TEXT
);

-- Отзывы
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    appointment_id INTEGER NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP
);

-- Платежи
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    appointment_id INTEGER NOT NULL,
    card_number TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP
);

-- Администраторы (дополнительная таблица для хранения админов)
CREATE TABLE IF NOT EXISTS admins (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    added_at TIMESTAMP,
    added_by BIGINT
);

-- Настройки
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Закрытые периоды
CREATE TABLE IF NOT EXISTS closed_periods (
    id SERIAL PRIMARY KEY,
    period_type TEXT NOT NULL,
    day_of_week INTEGER,
    specific_date DATE,
    start_time TIME,
    end_time TIME,
    description TEXT
);

-- Типоразмеры шин (опционально)
CREATE TABLE IF NOT EXISTS tire_sizes (
    id SERIAL PRIMARY KEY,
    width INTEGER,
    profile INTEGER,
    diameter INTEGER,
    season TEXT,
    common_name TEXT
);