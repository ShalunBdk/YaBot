import logging
from pathlib import Path
import sys
from yandex_bot import Client, Message
from services.ad_service import ADConnector
from services.utils import Utilities
from services.yandex_service import Yandex360

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

def disable_2fa_phone_yandex(message):
    template.disable_2fa_yandex(message)


logging.basicConfig(level=logging.INFO)
bot.run()
