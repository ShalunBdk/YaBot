import logging
import os
from pathlib import Path
import sys
import threading
import time
import requests
import schedule
from yandex_bot import Client, Message
from services.ad_service import ADConnector
from services.utils import Utilities
from services.yandex_service import Yandex360
from services.password_checker import PasswordExpiryChecker

sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from src.templates.messages import Template
from src.templates.menu import MenuTemplate

bot = Client(settings.YANDEX_BOT_TOKEN)
ya360 = Yandex360()
utils = Utilities()
ad = ADConnector(ya360, utils)

template = Template(bot, ya360, utils, ad)
menu = MenuTemplate(bot, ya360, utils, ad)

passchecker = PasswordExpiryChecker(bot, ad, utils)

@bot.unhandled_message()
def unhandled(message: Message):
    menu.show_main_menu(message.user.login)

@bot.on_message(phrase="info")
def command_start(message):
    template.show_info(message.user.login)

@bot.on_message(phrase="main_menu")
def command_start(message):
    menu.show_main_menu(message.user.login)

@bot.on_message(phrase="yandex_menu")
def command_start(message):
    menu.show_yandex_menu(message.user.login)

@bot.on_message(phrase="ad_menu")
def command_start(message):
    menu.show_ad_menu(message.user.login)

@bot.on_message(phrase="disable_2fa_phone")
def command_start(message):
    bot.send_message("Отправьте человека через @", message.user.login)
    bot.register_next_step_handler(message.user.login, disable_2fa_phone_yandex)

@bot.on_message(phrase="@")
def command_start(message):
    template.show_employee_info(message)

@bot.on_message(phrase="reset_password_step")
def command_start(message):
    template.reset_password_step(message)

@bot.on_message(phrase="reset_password_finally")
def command_start(message):
    template.reset_password_finally(message)

@bot.on_message(phrase="reset_password_notify")
def command_start(message):
    template.reset_password_notify(message)

@bot.on_message(phrase="expired_passwords")
def command_start(message):
    template.show_users_with_expired_passwords(message.user.login)

@bot.on_message(phrase="expiring_passwords")
def command_start(message):
    template.show_users_with_expiring_passwords(message.user.login)

@bot.on_message(phrase="reset_password_instruction_office")
def command_start(message):
    template.reset_password_instruction_office(message)

@bot.on_message(phrase="reset_password_instruction_remote")
def command_start(message):
    template.reset_password_instruction_remote(message)

@bot.on_message(phrase="reset_password_instruction")
def command_start(message):
    template.reset_password_instruction(message)

@bot.on_message(phrase="self_res_pass")
def command_start(message):
    template.self_res_pass(message)

@bot.on_message(phrase="self_reset_pass_finally")
def command_start(message):
    template.self_reset_pass_finally(message)

@bot.on_message(phrase="password")
def command_start(message):
    template.show_password_info(message)

@bot.on_message(phrase="yandex_blocked_users")
def command_start(message):
    template.show_yandex_blocked_users(message.user.login)

@bot.on_message(phrase="send_idea")
def command_start(message):
    bot.send_message("Распишите вашу идею или опишите баг с которым столкнулись", message.user.login)
    bot.register_next_step_handler(message.user.login, send_idea_finally)

def disable_2fa_phone_yandex(message):
    template.disable_2fa_yandex(message)

def send_idea_finally(message):
    template.send_idea_finally(message)

def run_password_checker(bot, ad_connector, utilities):
    """Запускает проверку паролей в отдельном потоке"""
    checker = PasswordExpiryChecker(bot, ad_connector, utilities)
    
    # Поток для обработки очереди уведомлений
    notification_thread = threading.Thread(
        target=checker.process_notification_queue,
        daemon=True
    )
    notification_thread.start()
    
    # Планировщик проверки паролей
    schedule.every().day.at("09:00").do(checker.check_expiring_passwords)
    
    # Поток для планировщика
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    return checker, notification_thread, scheduler_thread

def run_test_check(checker):
    """Запускает тестовую проверку паролей"""
    print("Запуск тестовой проверки паролей...")
    checker.check_expiring_passwords()
    
    # Ждем обработки всех уведомлений
    checker.notification_queue.join()
    print("Тестовая проверка завершена")

def watchdog(main_thread):
    while True:
        if not main_thread.is_alive():
            logging.error("Main thread died, restarting application")
            os._exit(1)  # Принудительный перезапуск
        time.sleep(60)  # Проверка каждую минуту

def main():
    try:
        bot.run()
    except requests.exceptions as e:
        logging.error(f"Ошибка сети: {e}")
        time.sleep(10)  # Ждем перед повторной попыткой

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    checker, notif_thread, sched_thread = run_password_checker(bot, ad, utils)
    # run_test_check(checker)
    main_thread = threading.Thread(target=main)
    main_thread.start()
    
    watchdog_thread = threading.Thread(target=watchdog, args=(main_thread,))
    watchdog_thread.daemon = True
    watchdog_thread.start()
    
