import subprocess
import sys
import os
import signal
import time

def run_bot():
    print("🚀 Запуск бота...")
    return subprocess.Popen([sys.executable, "bot.py"])

def run_web():
    print("🌐 Запуск веб-интерфейса...")
    web_dir = os.path.join(os.path.dirname(__file__), "admin_web")
    os.chdir(web_dir)
    proc = subprocess.Popen([sys.executable, "app.py"])
    os.chdir("..")
    return proc

def main():
    bot_proc = run_bot()
    web_proc = run_web()

    def signal_handler(sig, frame):
        print("\n🛑 Завершение работы...")
        bot_proc.terminate()
        web_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while True:
            if bot_proc.poll() is not None:
                print("❌ Бот завершил работу.")
                web_proc.terminate()
                break
            if web_proc.poll() is not None:
                print("❌ Веб-интерфейс завершил работу.")
                bot_proc.terminate()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()