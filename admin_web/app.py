from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash, jsonify
import pg8000
import pg8000.native
import os
from datetime import datetime, timedelta
import requests
import csv
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import database as db
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE, BOT_TOKEN, ADMIN_IDS

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this-in-production'

def get_db_connection():
    return pg8000.connect(
        host=PG_HOST,
        port=int(PG_PORT),
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DATABASE
    )

def format_datetime(value):
    if value:
        try:
            if isinstance(value, datetime):
                return value.strftime('%d.%m.%Y %H:%M')
            dt = datetime.fromisoformat(str(value))
            return dt.strftime('%d.%m.%Y %H:%M')
        except:
            return str(value)
    return ''
app.jinja_env.filters['datetime'] = format_datetime

def format_date(value):
    if value:
        try:
            if isinstance(value, datetime):
                return value.strftime('%d.%m.%Y')
            dt = datetime.fromisoformat(str(value))
            return dt.strftime('%d.%m.%Y')
        except:
            return str(value)
    return ''
app.jinja_env.filters['date'] = format_date

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

# ---------- Календарь ----------
def get_dates_with_appointments(month, year):
    conn = get_db_connection()
    cur = conn.cursor()
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{month+1:02d}-01"
    cur.execute('''
        SELECT DISTINCT date(appointment_time)
        FROM appointments
        WHERE date(appointment_time) >= %s AND date(appointment_time) < %s
        AND status != 'cancelled'
    ''', (start, end))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [str(row[0]) for row in rows]

def generate_calendar(year, month, booked_dates):
    first_day = datetime(year, month, 1).weekday()
    if month == 12:
        days_in_month = (datetime(year+1, 1, 1) - timedelta(days=1)).day
    else:
        days_in_month = (datetime(year, month+1, 1) - timedelta(days=1)).day
    weeks = []
    week = [None] * 7
    day = 1
    for wday in range(first_day):
        week[wday] = None
    for wday in range(first_day, 7):
        date_str = f"{year}-{month:02d}-{day:02d}"
        week[wday] = {'day': day, 'booked': date_str in booked_dates, 'date': date_str}
        day += 1
    weeks.append(week)
    while day <= days_in_month:
        week = [None] * 7
        for wday in range(7):
            if day <= days_in_month:
                date_str = f"{year}-{month:02d}-{day:02d}"
                week[wday] = {'day': day, 'booked': date_str in booked_dates, 'date': date_str}
                day += 1
            else:
                week[wday] = None
        weeks.append(week)
    return weeks

def generate_simple_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT date(appointment_time), COUNT(*) as cnt
        FROM appointments
        WHERE appointment_time >= date(now() - interval '7 days')
        AND status IN ('confirmed', 'completed')
        GROUP BY date(appointment_time)
        ORDER BY date(appointment_time)
    ''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    if not data:
        return None
    dates = [row[0] for row in data]
    counts = [row[1] for row in data]
    plt.figure(figsize=(6, 2))
    plt.bar(dates, counts, color='#007bff', alpha=0.7)
    plt.title('Записи за последние 7 дней', fontsize=10)
    plt.ylabel('Кол-во', fontsize=8)
    plt.xticks(rotation=45, fontsize=8)
    plt.yticks(fontsize=8)
    plt.tight_layout()
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=80)
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    return plot_url

@app.route('/')
def index():
    now = datetime.now()
    try:
        month = int(request.args.get('month', now.month))
        year = int(request.args.get('year', now.year))
    except:
        month = now.month
        year = now.year
    booked_dates = get_dates_with_appointments(month, year)
    calendar_weeks = generate_calendar(year, month, booked_dates)
    today_str = now.strftime('%Y-%m-%d')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.id, u.user_id, u.full_name, u.username, s.name as service_name, a.appointment_time
        FROM appointments a
        LEFT JOIN users u ON a.user_id = u.user_id
        LEFT JOIN services s ON a.service_id = s.id
        WHERE date(a.appointment_time) = %s AND a.status != 'cancelled'
        ORDER BY a.appointment_time
    ''', (today_str,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    today_apps = []
    for row in rows:
        today_apps.append({
            'id': row[0],
            'user_id': row[1],
            'full_name': row[2],
            'username': row[3],
            'service_name': row[4],
            'appointment_time': row[5]
        })
    stats_plot = generate_simple_stats()
    return render_template('index.html',
                           year=year, month=month, calendar_weeks=calendar_weeks,
                           now=now,
                           month_names=['Январь','Февраль','Март','Апрель','Май','Июнь',
                                        'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'],
                           today_appointments=today_apps,
                           today_str=today_str,
                           stats_plot=stats_plot)

@app.route('/appointments_by_date/<date>')
def appointments_by_date(date):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.id, u.user_id, u.full_name, u.username, u.phone,
               s.name as service_name, a.final_price, c.vehicle_type, c.tire_diameter,
               a.appointment_time, a.status, a.master_id, a.client_problem
        FROM appointments a
        LEFT JOIN users u ON a.user_id = u.user_id
        LEFT JOIN services s ON a.service_id = s.id
        LEFT JOIN cars c ON a.car_id = c.id
        WHERE date(a.appointment_time) = %s
        ORDER BY a.appointment_time
    ''', (date,))
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
    return render_template('appointments_by_date.html', date=date, appointments=appointments)

def get_filtered_appointments(filters):
    conn = get_db_connection()
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

@app.route('/appointments')
def appointments():
    filters = {}
    filters['date_from'] = request.args.get('date_from', '')
    filters['date_to'] = request.args.get('date_to', '')
    filters['status'] = request.args.get('status', '')
    filters['service'] = request.args.get('service', '')
    filters['user'] = request.args.get('user', '')
    session['appointment_filters'] = filters
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT status FROM appointments")
    statuses = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT name FROM services")
    services = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    appointments_list = get_filtered_appointments(filters)
    return render_template('appointments.html',
                           appointments=appointments_list,
                           filters=filters,
                           statuses=statuses,
                           services=services)

@app.route('/appointments/export')
def export_appointments():
    filters = session.get('appointment_filters', {})
    appointments = get_filtered_appointments(filters)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Клиент', 'Телефон', 'Услуга', 'Цена', 'Авто', 'Радиус', 'Дата и время', 'Статус', 'Мастер', 'Проблема'])
    for app in appointments:
        writer.writerow([
            app['id'],
            app['full_name'] or app['username'] or '',
            app['phone'] or '',
            app['service_name'],
            app['final_price'],
            app['vehicle_type'] or '',
            app['tire_diameter'] or '',
            app['appointment_time'].strftime('%d.%m.%Y %H:%M') if app['appointment_time'] else '',
            app['status'],
            app['master_id'],
            app['client_problem'] or ''
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'appointments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/appointments/status/<int:appointment_id>/<new_status>')
def change_status(appointment_id, new_status):
    if new_status == 'completed':
        if db.complete_appointment(appointment_id):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                SELECT u.user_id, s.name, c.vehicle_type, c.tire_diameter, w.appointment_time
                FROM completed_works w
                LEFT JOIN users u ON w.user_id = u.user_id
                LEFT JOIN services s ON w.service_id = s.id
                LEFT JOIN cars c ON w.car_id = c.id
                WHERE w.original_id = %s
            ''', (appointment_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row[0]:
                dt = row[4]
                dt_formatted = dt.strftime('%d.%m.%Y %H:%M') if dt else 'неизвестно'
                message = (
                    f"✅ Ваша услуга выполнена!\n"
                    f"Услуга: {row[1]}\n"
                    f"Авто: {row[2]}, R{row[3]}\n"
                    f"Время: {dt_formatted}\n\n"
                    f"Для оплаты нажмите кнопку ниже."
                )
                reply_markup = {"inline_keyboard": [[{"text": "💳 Оплатить", "callback_data": f"pay:{appointment_id}"}]]}
                send_telegram_message(row[0], message, reply_markup)
    else:
        db.update_appointment_status(appointment_id, new_status)
        if new_status == 'confirmed':
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                SELECT u.user_id, a.appointment_time, s.name, c.vehicle_type, c.tire_diameter
                FROM appointments a
                LEFT JOIN users u ON a.user_id = u.user_id
                LEFT JOIN services s ON a.service_id = s.id
                LEFT JOIN cars c ON a.car_id = c.id
                WHERE a.id = %s
            ''', (appointment_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row[0]:
                dt = row[1]
                dt_formatted = dt.strftime('%d.%m.%Y %H:%M') if dt else 'неизвестно'
                message = (
                    f"✅ Ваша запись подтверждена!\n"
                    f"Услуга: {row[2]}\n"
                    f"Авто: {row[3]}, R{row[4]}\n"
                    f"Время: {dt_formatted}\n\n"
                    f"Ждём вас!"
                )
                send_telegram_message(row[0], message)
    return redirect(url_for('appointments', **request.args))

@app.route('/appointments/delete/<int:appointment_id>')
def delete_appointment(appointment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id=%s", (appointment_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('appointments', **request.args))

@app.route('/completed')
def completed_works():
    works = db.get_completed_works()
    return render_template('completed_works.html', works=works)

@app.route('/statistics')
def statistics():
    period = request.args.get('period', 'month')
    stats = db.get_statistics(period)
    popular = db.get_popular_services(period)
    weekday_dist = db.get_weekday_distribution(period)
    hour_dist = db.get_hour_distribution(period)
    avg_check = db.get_average_check(period)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT date(appointment_time), SUM(final_price)
        FROM appointments
        WHERE status IN ('confirmed', 'completed')
        AND appointment_time >= date(now() - interval '30 days')
        GROUP BY date(appointment_time)
        ORDER BY date(appointment_time)
    ''')
    revenue_data = cur.fetchall()
    dates = [row[0] for row in revenue_data]
    revenues = [row[1] for row in revenue_data]
    cur.execute('''
        SELECT s.name, COUNT(*) as cnt
        FROM appointments a
        JOIN services s ON a.service_id = s.id
        WHERE a.status IN ('confirmed', 'completed')
        GROUP BY s.name
        ORDER BY cnt DESC
        LIMIT 5
    ''')
    popular_chart = cur.fetchall()
    cur.close()
    conn.close()
    plt.figure(figsize=(10, 4))
    plt.plot(dates, revenues, marker='o')
    plt.title('Выручка по дням (последние 30 дней)')
    plt.xlabel('Дата')
    plt.ylabel('Выручка, руб')
    plt.xticks(rotation=45)
    plt.tight_layout()
    img_revenue = io.BytesIO()
    plt.savefig(img_revenue, format='png')
    img_revenue.seek(0)
    revenue_plot = base64.b64encode(img_revenue.getvalue()).decode()
    plt.close()
    if popular_chart:
        labels = [row[0] for row in popular_chart]
        sizes = [row[1] for row in popular_chart]
        plt.figure(figsize=(8, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title('Популярность услуг')
        img_popular = io.BytesIO()
        plt.savefig(img_popular, format='png')
        img_popular.seek(0)
        popular_plot = base64.b64encode(img_popular.getvalue()).decode()
        plt.close()
    else:
        popular_plot = None
    return render_template('statistics.html',
                           stats=stats,
                           period=period,
                           popular=popular,
                           weekday_dist=weekday_dist,
                           hour_dist=hour_dist,
                           avg_check=avg_check,
                           revenue_plot=revenue_plot,
                           popular_plot=popular_plot)

@app.route('/broadcast', methods=['GET', 'POST'])
def broadcast():
    if request.method == 'POST':
        message = request.form['message']
        send_date = request.form['send_date']
        send_time = request.form['send_time']
        send_datetime_str = f"{send_date} {send_time}"
        try:
            send_at = datetime.strptime(send_datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Неверный формат даты/времени', 'error')
            return redirect(url_for('broadcast'))
        db.schedule_message(message, send_at)
        flash(f'Сообщение запланировано на {send_datetime_str}', 'success')
        return redirect(url_for('index'))
    return render_template('broadcast.html', now=datetime.now())

@app.route('/prices')
def prices():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price_per_tire, price_fixed, min_price, max_price FROM services WHERE is_active=1 ORDER BY sort_order")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    services_list = []
    for row in rows:
        services_list.append({
            'name': row[0],
            'price_per_tire': row[1],
            'price_fixed': row[2],
            'min_price': row[3],
            'max_price': row[4]
        })
    return render_template('prices.html', services=services_list)

@app.route('/services')
def services_list():
    services = db.get_all_services()
    return render_template('services.html', services=services)

@app.route('/services/add', methods=['GET', 'POST'])
def service_add():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price_per_tire = request.form.get('price_per_tire')
        price_fixed = request.form.get('price_fixed')
        min_price = request.form.get('min_price')
        max_price = request.form.get('max_price')
        sort_order = request.form.get('sort_order')
        db.add_service(name, description,
                      int(price_per_tire) if price_per_tire else None,
                      int(price_fixed) if price_fixed else None,
                      int(min_price) if min_price else None,
                      int(max_price) if max_price else None,
                      int(sort_order) if sort_order else None)
        flash('Услуга добавлена', 'success')
        return redirect(url_for('services_list'))
    return render_template('service_edit.html', service=None)

@app.route('/services/edit/<int:service_id>', methods=['GET', 'POST'])
def service_edit(service_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price_per_tire = request.form.get('price_per_tire')
        price_fixed = request.form.get('price_fixed')
        min_price = request.form.get('min_price')
        max_price = request.form.get('max_price')
        is_active = 1 if request.form.get('is_active') else 0
        sort_order = request.form.get('sort_order')
        db.update_service(service_id, name, description,
                         int(price_per_tire) if price_per_tire else None,
                         int(price_fixed) if price_fixed else None,
                         int(min_price) if min_price else None,
                         int(max_price) if max_price else None,
                         is_active, int(sort_order) if sort_order else None)
        flash('Услуга обновлена', 'success')
        return redirect(url_for('services_list'))
    else:
        services = db.get_all_services()
        service = next((s for s in services if s['id'] == service_id), None)
        return render_template('service_edit.html', service=service)

@app.route('/services/delete/<int:service_id>')
def service_delete(service_id):
    db.delete_service(service_id)
    flash('Услуга удалена', 'success')
    return redirect(url_for('services_list'))

# ---------- Мастера ----------
@app.route('/masters')
def masters_list():
    masters = db.get_all_masters(active_only=False)
    return render_template('masters.html', masters=masters)

@app.route('/master/add', methods=['GET', 'POST'])
def master_add():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form.get('specialization')
        phone = request.form.get('phone')
        db.add_master(name, specialization, phone)
        flash('Мастер добавлен', 'success')
        return redirect(url_for('masters_list'))
    return render_template('master_edit.html', master=None)

@app.route('/master/edit/<int:master_id>', methods=['GET', 'POST'])
def master_edit(master_id):
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form.get('specialization')
        phone = request.form.get('phone')
        is_active = 1 if request.form.get('is_active') else 0
        db.update_master(master_id, name, specialization, phone, is_active)
        flash('Данные мастера обновлены', 'success')
        return redirect(url_for('masters_list'))
    else:
        master = db.get_master_by_id(master_id)
        return render_template('master_edit.html', master=master)

@app.route('/master/delete/<int:master_id>')
def master_delete(master_id):
    db.delete_master(master_id)
    flash('Мастер удалён', 'success')
    return redirect(url_for('masters_list'))

# ---------- Автомобили ----------
@app.route('/car/edit/<int:car_id>', methods=['GET', 'POST'])
def car_edit(car_id):
    car = db.get_car(car_id)
    if not car:
        flash('Автомобиль не найден', 'error')
        return redirect(url_for('users_list'))
    
    if request.method == 'POST':
        brand = request.form['brand']
        model = request.form['model']
        year = request.form.get('year')
        vin = request.form.get('vin')
        vehicle_type = request.form['vehicle_type']
        tire_width = request.form.get('tire_width')
        tire_profile = request.form.get('tire_profile')
        tire_diameter = request.form.get('tire_diameter')
        tire_season = request.form.get('tire_season')
        is_default = 1 if request.form.get('is_default') else 0
        
        db.update_car(car_id, brand, model, int(year) if year else None,
                      vin, vehicle_type,
                      int(tire_width) if tire_width else None,
                      int(tire_profile) if tire_profile else None,
                      int(tire_diameter) if tire_diameter else None,
                      tire_season, is_default)
        flash('Автомобиль обновлён', 'success')
        return redirect(url_for('user_detail', user_id=car['user_id']))
    
    return render_template('car_edit.html', car=car)

# ---------- Пользователи ----------
@app.route('/users')
def users_list():
    users = db.get_all_users()
    return render_template('users.html', users=users)

@app.route('/user/<int:user_id>')
def user_detail(user_id):
    user = db.get_user_by_id(user_id)
    if not user:
        return "Пользователь не найден", 404
    cars = db.get_user_cars(user_id)
    appointments = db.get_user_appointments(user_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(final_price) FROM appointments
        WHERE user_id=%s AND status IN ('confirmed', 'completed')
    ''', (user_id,))
    total_sum = cur.fetchone()[0] or 0
    cur.close()
    conn.close()
    return render_template('user_detail.html', user=user, cars=cars,
                          appointments=appointments, total_sum=total_sum)

@app.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
def user_edit(user_id):
    user = db.get_user_by_id(user_id)
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users_list'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        address = request.form.get('address')
        birth_date = request.form.get('birth_date')
        notes = request.form.get('notes')
        db.update_user(user_id, email, address, birth_date, notes)
        flash('Данные пользователя обновлены', 'success')
        return redirect(url_for('user_detail', user_id=user_id))
    
    return render_template('user_edit.html', user=user)

@app.route('/users/ban/<int:user_id>')
def ban_user_route(user_id):
    db.ban_user(user_id)
    flash('Пользователь забанен', 'success')
    return redirect(url_for('users_list'))

@app.route('/users/unban/<int:user_id>')
def unban_user_route(user_id):
    db.unban_user(user_id)
    flash('Пользователь разбанен', 'success')
    return redirect(url_for('users_list'))

# ---------- Настройки ----------
@app.route('/settings')
def settings():
    admins_from_config = [{'user_id': uid, 'full_name': 'Из config', 'username': '', 'added_at': None} for uid in ADMIN_IDS]
    admins_from_db = db.get_all_admins()
    admins = admins_from_db + admins_from_config
    current_user_id = request.args.get('current_user_id', 0)
    schedule = db.get_work_schedule()
    cards = db.get_active_cards()
    services = db.get_all_services()
    masters = db.get_all_masters(active_only=False)
    return render_template('settings.html',
                          admins=admins,
                          current_user_id=int(current_user_id),
                          schedule=schedule,
                          cards=cards,
                          services=services,
                          masters=masters)

@app.route('/add_admin', methods=['POST'])
def add_admin():
    user_id = request.form.get('user_id')
    if not user_id:
        flash('Не указан ID пользователя', 'error')
        return redirect(url_for('settings'))
    try:
        user_id = int(user_id)
    except ValueError:
        flash('ID должен быть числом', 'error')
        return redirect(url_for('settings'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        flash('Пользователь с таким ID не найден в базе данных', 'error')
        return redirect(url_for('settings'))
    db.add_admin(user_id, 0)
    flash(f'Администратор с ID {user_id} добавлен', 'success')
    return redirect(url_for('settings'))

@app.route('/remove_admin/<int:user_id>')
def remove_admin(user_id):
    if user_id in ADMIN_IDS:
        flash('Нельзя удалить администратора из config', 'error')
    else:
        db.remove_admin(user_id)
        flash(f'Администратор с ID {user_id} удален', 'success')
    return redirect(url_for('settings'))

@app.route('/api/save_schedule', methods=['POST'])
def save_schedule():
    schedule = request.json
    for day in schedule:
        db.update_work_schedule(
            day['day_of_week'],
            day['is_working'],
            day['start_time'],
            day['end_time'],
            day['break_start'],
            day['break_end']
        )
    return jsonify({'success': True})

@app.route('/api/add_card', methods=['POST'])
def add_card():
    card_number = request.form.get('card_number')
    card_holder = request.form.get('card_holder')
    bank_name = request.form.get('bank_name')
    if not card_number:
        return jsonify({'success': False, 'error': 'Номер карты обязателен'})
    card_id = db.add_card(card_number, card_holder, bank_name)
    return jsonify({'success': True, 'id': card_id})

@app.route('/api/delete_card/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    db.delete_card(card_id)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=333)