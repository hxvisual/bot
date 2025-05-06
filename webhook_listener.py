import subprocess
import os
import logging
import sys
import hmac
import hashlib
from flask import Flask, request, abort
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Путь к вашему репозиторию на VPS
REPO_PATH = "/root/bot" # ЗАМЕНИТЕ НА ВАШ ПУТЬ

# Имя systemd сервиса вашего бота
BOT_SERVICE_NAME = "my_telegram_bot.service"

# Ветка, которую нужно обновлять (обычно main или master)
GIT_BRANCH = "main"
# --- Конец Конфигурации ---

if not WEBHOOK_SECRET or WEBHOOK_SECRET == "ВАШ_ОЧЕНЬ_СЛОЖНЫЙ_СЕКРЕТ_ЗДЕСЬ":
    logging.critical("WEBHOOK_SECRET не установлен или используется значение по умолчанию! Установите надежный секрет.")
    sys.exit(1)

app = Flask(__name__)

def run_command(command, cwd=None):
    """Вспомогательная функция для выполнения shell-команд."""
    logging.info(f"Выполнение команды: {' '.join(command)} в {cwd or os.getcwd()}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=cwd)
        logging.info(f"Stdout:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"Stderr:\n{result.stderr}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка выполнения команды: {e}")
        logging.error(f"Stderr:\n{e.stderr}")
        logging.error(f"Stdout:\n{e.stdout}")
        return False, e.stderr
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при выполнении команды: {e}")
        return False, str(e)

def verify_signature(payload_body, secret_token, signature_header):
    """Проверка подписи запроса от GitHub."""
    if not signature_header:
        logging.warning("Заголовок X-Hub-Signature-256 отсутствует.")
        return False
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        logging.warning(f"Подписи не совпадают! Ожидалось: {expected_signature}, Получено: {signature_header}")
        return False
    return True

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    logging.info("Получен запрос на /webhook")

    # 1. Проверка подписи
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, WEBHOOK_SECRET, signature):
        logging.error("Неверная подпись webhook!")
        abort(403) # Forbidden

    # 2. Проверка события (push) и ветки
    event = request.headers.get('X-GitHub-Event')
    if event != 'push':
        logging.info(f"Проигнорировано событие: {event}")
        return 'Ignoring non-push event', 200

    try:
        payload = request.get_json()
        ref = payload.get('ref', '')
        expected_ref = f'refs/heads/{GIT_BRANCH}'
        if ref != expected_ref:
            logging.info(f"Push не в отслеживаемую ветку ({GIT_BRANCH}). Получено: {ref}")
            return f'Ignoring push to {ref}', 200
    except Exception as e:
        logging.error(f"Ошибка парсинга JSON payload: {e}")
        abort(400) # Bad Request

    logging.info(f"Получен push в ветку {GIT_BRANCH}. Запуск обновления...")

    # 3. Выполнение git pull
    success, output = run_command(['git', 'pull', 'origin', GIT_BRANCH], cwd=REPO_PATH)
    if not success:
        logging.error("Ошибка выполнения git pull.")
        return 'Git pull failed', 500

    # Проверяем, были ли изменения (опционально, но полезно)
    if "Already up to date." in output:
        logging.info("Нет новых изменений. Перезапуск не требуется.")
        return 'Already up to date', 200

    # 4. Установка/обновление зависимостей (если requirements.txt изменился)
    # Можно добавить проверку изменения requirements.txt через git diff
    logging.info("Обновление зависимостей...")
    pip_executable = os.path.join(REPO_PATH, 'venv', 'bin', 'pip')
    req_file = os.path.join(REPO_PATH, 'requirements.txt')
    success, _ = run_command([pip_executable, 'install', '-r', req_file], cwd=REPO_PATH)
    if not success:
         logging.warning("Не удалось обновить зависимости, но перезапуск все равно будет выполнен.")
         # Можно решить не перезапускать, если зависимости критичны: return 'Failed to install requirements', 500

    # 5. Перезапуск systemd сервиса бота
    logging.info(f"Перезапуск сервиса {BOT_SERVICE_NAME}...")
    # Важно: веб-сервер должен иметь права на перезапуск сервиса.
    # Самый простой способ - запускать веб-сервер от root (не рекомендуется)
    # или настроить sudoers, чтобы пользователь мог перезапускать конкретный сервис без пароля.
    success, _ = run_command(['sudo', 'systemctl', 'restart', BOT_SERVICE_NAME])
    if not success:
        logging.error(f"Не удалось перезапустить сервис {BOT_SERVICE_NAME}.")
        return f'Failed to restart service {BOT_SERVICE_NAME}', 500

    logging.info("Обновление и перезапуск успешно завершены.")
    return 'Webhook processed successfully', 200

# Запуск Flask-приложения (для теста)
# В продакшене используется gunicorn
# if __name__ == '__main__':
#    app.run(host='0.0.0.0', port=5000, debug=True) # Порт можно изменить