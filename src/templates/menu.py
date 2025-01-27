from yandex_bot import Client
from exceptions import AccessException, Has2FAException
from services.ad_service import ADConnector
from services.utils import Utilities
from services.yandex_service import Yandex360

from templates.messages import Template

class MenuTemplate(Template):

    def _show_menu(self, user_login: str, menu_keyboard) -> None:
        """
        Базовый метод для отображения меню с проверками доступа
        
        Args:
            user_login: Логин пользователя
            menu_keyboard: Клавиатура для отображения
        """
        try:
            self.ad.check_admin(user_login)
            self.ya360.check_2fa(user_login)
            self.bot.send_message(
                "Выберите действие:",
                user_login,
                inline_keyboard=menu_keyboard
            )
        except AccessException as e:
            self.bot.send_message(
                "Выберите действие:",
                user_login,
                inline_keyboard=self.user_main_menu
            )
        except Has2FAException as e:
            self.bot.send_message(
                "Для использования бота у вас должны быть включена двухфакторная аутентификация в Яндекс.\
                \n\n**1.** Перейдите по ссылке: https://id.yandex.ru/security/enter-methods\
                \n**2.** Выберите способ входа SSO + смс",
                user_login
            )

    def show_main_menu(self, user_login: str) -> None:
        """
        Показывает главное меню
        """
        self.clear_session(user_login)
        self._show_menu(user_login, self.admin_main_menu)

    def show_yandex_menu(self, user_login: str) -> None:
        """
        Показывает яндекс меню
        """
        self._show_menu(user_login, self.yandex_menu)

    def show_ad_menu(self, user_login: str) -> None:
        """
        Показывает меню Active Directory
        """
        self._show_menu(user_login, self.ad_menu)
