shinomantag_bot/
├── .env                              # Файл с секретными данными (не в git)
├── .env.example                      # Пример файла с переменными
├── .gitignore                        # Исключаемые файлы
├── requirements.txt                   # Зависимости Python
├── config.py                          # Загрузка конфигурации
├── database.py                        # Все функции работы с PostgreSQL
├── keyboards.py                        # Генерация клавиатур
├── utils.py                            # Вспомогательные функции
├── bot.py                              # Точка входа для бота
├── start.py                            # Скрипт одновременного запуска
│
├── handlers/                           # Обработчики Telegram бота
│   ├── __init__.py
│   ├── middlewares.py                   # Middleware для проверки бана
│   ├── user.py                          # Логика пользователей
│   └── admin.py                         # Команды администратора
│
├── admin_web/                          # Веб-интерфейс администратора
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css
│   │   │   ├── calendar.css
│   │   │   ├── appointments.css
│   │   │   └── settings.css
│   │   └── js/
│   │       └── main.js
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── appointments.html
│   │   ├── appointments_by_date.html
│   │   ├── statistics.html
│   │   ├── payments.html
│   │   ├── broadcast.html
│   │   ├── broadcast_result.html
│   │   ├── prices.html
│   │   ├── services.html
│   │   ├── service_edit.html
│   │   ├── users.html
│   │   ├── user_detail.html
│   │   ├── completed_works.html
│   │   └── settings.html
│   └── app.py                          # Flask приложение
│
└── create_tables.sql                    # SQL скрипт для создания таблиц