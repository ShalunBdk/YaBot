from datetime import datetime, timedelta
import logging
from yandex_bot import Client, Button

from exceptions import AccessException

from services.ad_service import ADConnector
from services.utils import Utilities
from services.yandex_service import Yandex360

class Template:
    def __init__(
            self,
            bot: Client,
            ya360: Yandex360,
            utils: Utilities,
            ad: ADConnector
        ):
        self.bot = bot
        self.ya360 = ya360
        self.utils = utils
        self.ad = ad
        self.session = {}
        self.admin_main_menu = [
            Button(text="❔ информация", phrase="info"),
            Button(text="🔑 пароль", phrase="password"),
            Button(text="🔍 яндекс", phrase="yandex_menu"),
            Button(text="🛂 active directory", phrase="ad_menu"),
        ]

        self.yandex_menu = [
            Button(text="🚧 Кол-во заблокированных пользователей", phrase="yandex_blocked_users"),
            Button(text="❎ Сброс номера для 2FA у пользователя", phrase="disable_2fa_phone"),
            Button(text="❌ Отмена", phrase="main_menu"),
        ]

        self.ad_menu = [
            Button(text="🔐 истекающие пароли", phrase="expiring_passwords"),
            Button(text="💀 истекшие пароли", phrase="expired_passwords"),
            Button(text="❌ Отмена", phrase="main_menu"),
        ]

        self.user_main_menu = [
            Button(text="❔ информация", phrase="info"),
            Button(text="🔑 пароль", phrase="password"),
            Button(text="💡 Предложить идею / 🐞 Сообщить о баге", phrase="send_idea"),
        ]
    
    def get_session(self, user_id):
        if user_id not in self.session:
            self.session[user_id] = {}
        return self.session[user_id]

    def clear_session(self, user_id):
        if user_id in self.session:
            del self.session[user_id]

    def _send_admin_protected_message(self, user_login: str, message: str, keyboard=None) -> None:
        """
        Отправляет сообщение с проверкой на админа
        """
        try:
            self.ad.check_admin(user_login)
            self.bot.send_message(
                message,
                user_login,
                inline_keyboard=keyboard or self.admin_main_menu
            )
        except AccessException:
            self.bot.send_message(
                "Выберите действие:",
                user_login,
                inline_keyboard=self.user_main_menu
            )

    def _format_user_info(self, last_password_change: str, created_at: str, last_logon: str) -> str:
        """
        Форматирует информацию о пользователе
        """
        try:
            last_change_date = datetime.strptime(last_password_change, "%d.%m.%Y %H:%M")
            expiry_date = last_change_date + timedelta(days=90)
            days_remaining = (expiry_date - datetime.now()).days

            base_message = f"Аккаунт создан {self.utils.format_utc_to_moscow(created_at)}(MSK)\n\n"
            base_message += f"Последняя авторизация {self.utils.format_utc_to_moscow(last_logon)}(MSK)\n\n"
            base_message += f"Последняя смена пароля: {last_password_change}(UTC)."

            if days_remaining > 0:
                return f"{base_message}\nПароль действителен еще {days_remaining} дней."
            elif days_remaining == 0:
                return f"{base_message}\nПароль истекает сегодня."
            else:
                return f"{base_message}\nПароль истёк."
        except ValueError:
            return f"Ошибка: {last_password_change}"

    def _format_password_info(self, last_password_change: str) -> str:
        """
        Форматирует информацию о пароле пользователя
        """
        try:
            last_change_date = datetime.strptime(last_password_change, "%d.%m.%Y %H:%M")
            expiry_date = last_change_date + timedelta(days=90)
            days_remaining = (expiry_date - datetime.now()).days

            base_message = f"Последняя смена пароля: {last_password_change}(UTC)."

            if days_remaining > 0:
                return f"{base_message}\nПароль действителен еще {days_remaining} дней."
            elif days_remaining == 0:
                return f"{base_message}\nПароль истекает сегодня."
            else:
                return f"{base_message}\nПароль истёк."
        except ValueError:
            return f"Ошибка: {last_password_change}"

    def show_info(self, user_login: str) -> None:
        """
        Показывает общую информацию про бота
        """
        is_support = self.ad.user_in_group(
            user_login.split("@")[0],
            "CN=IT Техническая поддержка,OU=Security Groups,OU=MyBusiness,DC=tion,DC=local",
        )
        
        if is_support:
            message = ("\n\nЭто бот IT Службы, который может отвечать на некоторые команды."
                      "\n\n__Если бот вам отвечает значит вы состоите в группе IT в Active Directory__"
                      "\n\n**Команды:**"
                      "```🔑 пароль``` посмотреть и сбросить свой пароль"
                      "```Выбор человека через @``` посмотреть информацию о человека и возможность сбросить ему пароль, после чего отправить новый пароль ему в мессенджер"
                      "```🔍 яндекс``` функции связанные с яндексом(сбросить 2FA, посмотреть заблокированных в AD, но остающихся в яндексе пользователей)"
                      "```🛂 active directory``` функции связанные с AD(Посмотреть пользователей у которых закончился или скоро закончится пароль)")
            keyboard = self.admin_main_menu
        else:
            message = ("\n\nЭто бот IT Службы, который напоминает о смене пароля и может отвечать на некоторые вопросы."
                      "\n\n**Команды:**"
                      "\n\n```🔑 пароль``` - покажет срок действия вашего пароля"
                      "\n\n```💡 Предложить идею / 🐞 Сообщить о баге``` - отправить сообщение разработчику")
            keyboard = self.user_main_menu
            
        self.bot.send_message(message, user_login, inline_keyboard=keyboard)

    def show_employee_info(self, message) -> None:
        try:
            self.ad.check_admin(message.user.login)
            try:
                account_name = message.text.split("@")[1]
            except ValueError:
                account_name = message.text.split("@")[0]
            info = {
                'last_password_change': self.ad.get_password_expiry_date(account_name),
                'created_at': self.ad.get_account_creation_date(account_name),
                'last_logon': self.ad.get_last_logon(account_name)
            }
            
            formatted_message = self._format_user_info(**info)
            session = self.get_session(message.user.login)
            session['account_name'] = account_name
            self.bot.send_message(
                formatted_message,
                message.user.login,
                inline_keyboard=[
                    Button(text="🔄 Сбросить пароль", phrase="reset_password_step"),
                    Button(text="❌ Отмена", phrase="main_menu"),
                ]
            )
        except AccessException as e:
            self.bot.send_message(
                "Выберите действие:",
                message.user.login,
                inline_keyboard=self.user_main_menu
            )

    def reset_password_step(self, message):
        session = self.get_session(message.user.login)
        account_name = session.get('account_name')
        self.bot.send_message(
            f'Вы хотите сбросить пароль {account_name}?',
            message.user.login,
            inline_keyboard=[
                Button(text="✅ Да", phrase="reset_password_finally"),
                Button(text="❌ Отмена", phrase="main_menu"),
            ]
        )

    def reset_password_finally(self, message):
        session = self.get_session(message.user.login)
        account_name = session.get('account_name')
        password = self.utils.generate_random_string()
        session['password'] = password
        self.ad.change_password(account_name, password)
        self.bot.send_message(
            f'Пароль {account_name} сброшен на **{password}**\nХотите отправить новый пароль {account_name} в мессенджер?',
            message.user.login,
            inline_keyboard=[
                Button(text="📨 Отправить", phrase="reset_password_notify"),
                Button(text="❌ Нет", phrase="main_menu"),
            ]
        )
        logging.info(f'{message.user.login} сбросил пароль для {account_name}')

    def reset_password_notify(self, message):
        session = self.get_session(message.user.login)
        account_name = session.get('account_name')
        password = session.get('password')
        self.clear_session(message.user.login)
        self.bot.send_message(
            f'Ваш пароль сброшен администратором {message.user.login}\nНовый пароль **{password}**',
            f'{account_name}@tion.ru',
            inline_keyboard=self.user_main_menu
        )
        self.bot.send_message(
            'Уведомление отправлено',
            message.user.login,
            inline_keyboard=self.admin_main_menu
        )

    def show_password_info(self, message) -> None:
        info = {
            'last_password_change': self.ad.get_password_expiry_date(message.user.login.split("@")[0])
        }
        formatted_message = self._format_password_info(**info)
        self.bot.send_message(
            formatted_message,
            message.user.login,
            inline_keyboard=[
                    Button(text="🔐 Как сменить пароль?", phrase="reset_password_instruction"),
                    Button(text="🔄 Сброс пароля", phrase="self_res_pass"),
                    Button(text="❌ Отмена", phrase="main_menu"),
                ]
        )
    
    def reset_password_instruction(self, message):
        self.bot.send_message(
            'Вы сейчас работаете в офисе или на удалёнке?',
            message.user.login,
            inline_keyboard=[
                Button(text="🏢 Офис", phrase="reset_password_instruction_office"),
                Button(text="🏘️ Удалёнка", phrase="reset_password_instruction_remote"),
                Button(text="❌ Отмена", phrase="main_menu"),
            ]
        )

    def reset_password_instruction_office(self, message):
        is_support = self.ad.user_in_group(
            message.user.login.split("@")[0],
            "CN=IT Техническая поддержка,OU=Security Groups,OU=MyBusiness,DC=tion,DC=local",
        )
        if is_support:
            keyboard = self.admin_main_menu
        else:
            keyboard = self.user_main_menu
        self.bot.send_message(
            'Если вы находитесь за своим рабочим компьютером, нажмите **Ctrl + Alt + Del** и выберите **Сменить пароль**.\
                \nБолее подробную инструкцию вы можете найти в нашем [Wiki](https://wiki.yandex.ru/homepage/wiki-it-service/change-pas-rdp/)',
            message.user.login,
            inline_keyboard=keyboard
        )

    def reset_password_instruction_remote(self, message):
        is_support = self.ad.user_in_group(
            message.user.login.split("@")[0],
            "CN=IT Техническая поддержка,OU=Security Groups,OU=MyBusiness,DC=tion,DC=local",
        )
        if is_support:
            keyboard = self.admin_main_menu
        else:
            keyboard = self.user_main_menu
        self.bot.send_message(
            'Если у вас есть удаленный рабочий компьютер, подключитесь к нему и нажмите **Ctrl + Alt + End**, затем выберите "Сменить пароль".\
                \n\nЕсли у вас нет рабочего компьютера в офисе, выполните инструкцию из нашего [Wiki](https://wiki.yandex.ru/homepage/wiki-it-service/change-pas-rdp/)\
                \n\n__`Если у вас на ноутбуке нет клавиши END, вбейте в любом поисковике слова "END KEY" и модель вашего ноутбука(например, END KEY HUAWEI)`__',
            message.user.login,
            inline_keyboard=keyboard
        )

    def self_res_pass(self, message):
        self.bot.send_message(
            'Вы хотите изменить свой пароль на случайно сгенерированный?',
            message.user.login,
            inline_keyboard=[
                Button(text="✅ Да", phrase="self_reset_pass_finally"),
                Button(text="❌ Отмена", phrase="main_menu"),
            ]
        )

    def self_reset_pass_finally(self, message):
        is_support = self.ad.user_in_group(
            message.user.login.split("@")[0],
            "CN=IT Техническая поддержка,OU=Security Groups,OU=MyBusiness,DC=tion,DC=local",
        )
        if is_support:
            keyboard = self.admin_main_menu
        else:
            keyboard = self.user_main_menu
        password = self.utils.generate_random_string()
        self.ad.change_password(message.user.login.split("@")[0], password)
        self.bot.send_message(
            f'Ваш новый пароль **{password}**',
            message.user.login,
            inline_keyboard=keyboard
        )
        logging.info(f'{message.user.login} сбросил свой пароль')

    def disable_2fa_yandex(self, message):
        try:
            self.ad.check_admin(message.user.login)
            username = message.text.split("@", 1)[1]
            
            if not self.ya360.has_2fa(username):
                response = f"У аккаунта {username} отсутствует защищенный номер телефона"
            else:
                try:
                    user_id = self.ya360.get_user_by_nickname(username)
                    if user_id:
                        response = self.ya360.disable_2fa(user_id)
                    else:
                        response = f"Пользователь {username} не найден"
                except Exception as e:
                    response = f"Ошибка отключения 2FA: {e}"
            self.bot.send_message(
                response,
                message.user.login,
                inline_keyboard=self.admin_main_menu
            )
        except AccessException as e:
            self.bot.send_message(
                "Выберите действие:",
                message.user.login,
                inline_keyboard=self.user_main_menu
            )
        except IndexError as e:
            self.bot.send_message(
                f"Ошибка сброса номера 2FA: {e}",
                message.user.login,
                inline_keyboard=self.admin_main_menu
            )

    def send_idea_finally(self, message):
        self.bot.send_message(
            f'💡 Новое сообщение от {message.user.login}'
            f'\n\n{message.text}',
            chat_id='0/0/7a69ddd0-8e49-4f1a-966d-927fc89ddb89'
        )
        self.bot.send_message(
            'Сообщение отправлено',
            message.user.login,
            inline_keyboard=self.user_main_menu
        )

    def _format_expired_users_list(self, users: list) -> str:
        """
        Форматирует список пользователей с истекшими паролями
        """
        sort_users = sorted(
            users,
            key=lambda x: datetime.strptime(x["password_expiry_date"], "%d.%m.%Y"),
        )
        
        reply_text = "🔁 - срок действия пароля не ограничен\n\n"
        
        for user in sort_users:
            if ("OU=Service,OU=ya360,OU=SBSUsers,OU=Users,OU=MyBusiness,DC=tion,DC=local"
                not in str(user["distinguished_name"])):
                
                username = user['username']
                expiry_date = user['password_expiry_date']
                
                if user["userAccountControl"] == 66048:
                    reply_text += f"**{username}** истек {expiry_date} 🔁\n\n"
                else:
                    reply_text += f"**{username}** истек {expiry_date}\n\n"
                    
        return reply_text

    def _format_expiring_users_list(self, users: list) -> str:
        """
        Форматирует список пользователей с истекающими паролями
        """
        sort_users = sorted(
            users,
            key=lambda x: datetime.strptime(x["password_expiry_date"], "%d.%m.%Y"),
        )
        
        reply_text = ""
        for user in sort_users:
            username = user['username']
            expiry_date = user['password_expiry_date']
            reply_text += f"Пароль пользователя **{username}** истекает {expiry_date}\n\n"
                    
        return reply_text

    def show_users_with_expired_passwords(self, user_login: str):
        users = self.ad.get_users_with_expired_passwords()
        formatted_users = self._format_expired_users_list(users)
        self._send_admin_protected_message(user_login, formatted_users)

    def show_users_with_expiring_passwords(self, user_login: str):
        users = self.ad.get_users_with_expiring_passwords()
        formatted_users = self._format_expiring_users_list(users)
        self._send_admin_protected_message(user_login, formatted_users)

    def show_yandex_blocked_users(self, user_login: str):
        self._send_admin_protected_message(
            user_login,
            self.ya360.view_blocked_users()
        )