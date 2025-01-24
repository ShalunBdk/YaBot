from yandex_bot import Client, Button
from datetime import datetime
import time
import pytz
import logging
from typing import Dict
from queue import Queue as Queue, Empty as QueueEmpty

class PasswordExpiryChecker:
    def __init__(self, bot, ad_connector, utilities):
        self.bot = bot
        self.ad = ad_connector
        self.utils = utilities
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        self.logger = logging.getLogger(__name__)
        self.notification_queue = Queue()
        
    def check_expiring_passwords(self):
        """Проверяет пароли пользователей и отправляет уведомления"""
        try:
            # Проверяем пароли, истекающие в ближайшие 7 дней
            expiring_users = self.ad.get_users_with_expiring_passwords(days=7)
            for user in expiring_users:
                try:
                    # Вычисляем количество дней до истечения
                    expiry_date = datetime.strptime(user['password_expiry_date'], "%d.%m.%Y")
                    now = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
                    days_remaining = (expiry_date - now).days
                    notification_data = {
                        'username': user['username'],
                        'display_name': user['display_name'],
                        'days_remaining': days_remaining,
                        'expiry_date': user['password_expiry_date']
                    }
                    self.notification_queue.put(notification_data)
                        
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке пользователя {user['username']}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка пользователей с истекающими паролями: {e}")

    def _send_notification(self, user_data: Dict):
        """Отправляет уведомление пользователю"""
        try:
            days_word = self._get_days_word(user_data['days_remaining'])
            
            message = (
                f"🔔 Уведомление о сроке действия пароля\n\n"
                f"Уважаемый(ая) {user_data['display_name']}!\n\n"
                f"Ваш пароль истекает через {user_data['days_remaining']} {days_word} "
                f"({user_data['expiry_date']}).\n\n"
            )
            
            self.bot.send_message(
                message,
                f'{user_data['username']}@tion.ru',
                inline_keyboard=[
                    Button(text="🔐 Как сменить пароль?", phrase="reset_password_instruction"),
                    Button(text="🔄 Сброс пароля", phrase="self_res_pass")
                ]
            )
            
            self.logger.info(
                f"Уведомление отправлено пользователю {user_data['username']} "
                f"(до истечения: {user_data['days_remaining']} дней)"
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомления пользователю {user_data['username']}: {e}")

    def _get_days_word(self, days: int) -> str:
        """Возвращает правильное склонение слова 'день'"""
        if days in [1]:
            return "день"
        elif days in [2, 3, 4]:
            return "дня"
        else:
            return "дней"

    def process_notification_queue(self):
        """Обрабатывает очередь уведомлений"""
        while True:
            try:
                # Получаем уведомление из очереди
                user_data = self.notification_queue.get(timeout=1)
                self._send_notification(user_data)
                self.notification_queue.task_done()
            except QueueEmpty:
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Ошибка при обработке очереди уведомлений: {e}")