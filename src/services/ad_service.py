import logging
import pytz
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Union
from ldap3 import Server, Connection, ALL

from config import settings

from exceptions import AccessException

class ADConnector:
    """Class for handling Active Directory operations."""

    def __init__(self, ya360, utils):
        self.ya360 = ya360
        self.utils = utils
        self.server = Server(settings.AD_SERVER, get_info=ALL)
        self.base_dn = settings.AD_BASE_DN
        self._dc_addresses = [
            'dc-nsk2.tion.local',
            'dc-nsk3.tion.local',
            'dc-bsk2.tion.local',
            'dc-msk-um2.tion.local',
            'dc-msk.tion.local',
            'dc-msk3.tion.local'
        ]
        # Кэш для хранения результатов проверки админских прав
        self._admin_cache: Dict[str, Tuple[bool, datetime]] = {}
        # Время жизни кэша (в часах)
        self._admin_cache_ttl = 1

    def _get_connection(self, use_ssl: bool = False, for_password_change: bool = False) -> Connection:
        """Creates and returns a new AD connection."""
        if for_password_change:
            user = settings.AD_USER_FOR_PASS_CHANGE
            password = settings.AD_PASSWORD_FOR_PASS_CHANGE
            server = Server(settings.AD_SERVER, get_info=ALL, use_ssl=True)
        else:
            user = settings.AD_USER
            password = settings.AD_PASSWORD
            server = self.server if not use_ssl else Server(settings.AD_SERVER, get_info=ALL, use_ssl=True)
        logging.debug(f'Обращение к {server}')
        return Connection(server, user=user, password=password, auto_bind=True)

    def _is_cache_valid(self, cache_time: datetime) -> bool:
        """Проверяет, не истек ли срок действия кэша."""
        return datetime.now() - cache_time < timedelta(hours=self._admin_cache_ttl)

    def _get_admin_group_dn(self) -> str:
        """Возвращает DN группы администраторов."""
        return "CN=IT Техническая поддержка,OU=Security Groups,OU=MyBusiness,DC=tion,DC=local"

    def get_password_expiry_date(self, login: str) -> str:
        """Returns the password expiry date for a user."""
        try:
            with self._get_connection() as conn:
                conn.search(
                    self.base_dn,
                    f"(sAMAccountName={login})",
                    attributes=["pwdLastSet"]
                )
                logging.debug(f'Получение даты последней смены пароля {login}')
                if conn.entries:
                    pwd_last_set = conn.entries[0].pwdLastSet.value
                    if isinstance(pwd_last_set, datetime):
                        pwd_last_set = pwd_last_set.replace(tzinfo=None)
                        return pwd_last_set.strftime("%d.%m.%Y %H:%M")
                    return "Ошибка: атрибут pwdLastSet не является объектом datetime."
                
                alias = self.ya360.get_user_alias(login)
                if alias:
                    return self.get_password_expiry_date(alias)
                return f"Пользователь {login} не найден или у него отсутствует атрибут pwdLastSet."
        except Exception as e:
            return f"Ошибка подключения к AD: {e}"

    def get_account_creation_date(self, login: str) -> Union[datetime, str]:
        """Gets the account creation date from Active Directory."""
        try:
            with self._get_connection() as conn:
                logging.debug(f'Получение даты создания аккаунта {login}')
                conn.search(
                    self.base_dn,
                    f"(sAMAccountName={login})",
                    attributes=["whenCreated"]
                )
                if conn.entries:
                    when_created = conn.entries[0].whenCreated.value
                    if isinstance(when_created, datetime):
                        return when_created
                    return "Ошибка: атрибут when_created не является объектом datetime."

                alias = self.ya360.get_user_alias(login)
                if alias:
                    return self.get_account_creation_date(alias)
                return f"Пользователь {login} не найден."
        except Exception as e:
            return f"Ошибка подключения к AD: {e}"

    def get_last_logon(self, login: str) -> Optional[datetime]:
        """Gets the maximum lastLogon value for a user across all DCs."""
        max_last_logon = None
        logging.debug(f'Получение даты последнего входа {login}')
        for dc in self._dc_addresses:
            try:
                server = Server(dc, get_info=ALL)
                with Connection(
                    server,
                    user=settings.AD_USER,
                    password=settings.AD_PASSWORD,
                    auto_bind=True
                ) as conn:
                    conn.search(
                        self.base_dn,
                        f"(sAMAccountName={login})",
                        attributes=["lastLogon"]
                    )
                    
                    if conn.entries:
                        last_logon_raw = conn.entries[0].lastLogon.value
                        if isinstance(last_logon_raw, datetime):
                            last_logon_date = last_logon_raw
                        else:
                            last_logon_date = datetime(1601, 1, 1) + timedelta(microseconds=int(last_logon_raw) / 10)
                        logging.debug(f'Последний вход {login} на {dc} {last_logon_date}')
                        if not max_last_logon or last_logon_date > max_last_logon:
                            max_last_logon = last_logon_date

            except Exception as e:
                logging.error(f"Ошибка при подключении к контроллеру домена {dc}: {e}")
        
        return max_last_logon

    def get_phone_number(self, login: str) -> str:
        """Gets user's phone number from AD."""
        try:
            with self._get_connection() as conn:
                logging.debug(f'Получение номера телефона {login}')
                conn.search(
                    self.base_dn,
                    f"(sAMAccountName={login})",
                    attributes=["telephoneNumber"]
                )
                
                if conn.entries:
                    phone = conn.entries[0].telephoneNumber.value
                    return self.utils.normalize_phone_number(phone)
                
                alias = self.ya360.get_user_alias(login)
                if alias:
                    try:
                        return self.get_phone_number(alias)
                    except Exception:
                        raise TypeError
                return f"Пользователь с логином {login} не найден или не имеет телефонного номера."
        except TypeError:
            return f"Ошибка при поиске телефона в AD: {e}"
        except Exception as e:
            return f"Ошибка подключения к AD: {e}"

    def check_connection(self) -> bool:
        """Checks connection to Active Directory."""
        logging.debug(f"Проверка соединения с AD сервером: {settings.AD_SERVER}")
        try:
            with self._get_connection() as conn:
                return bool(conn.bind())
        except Exception as e:
            logging.error(f"Ошибка при подключении к AD: {e}")
            return False

    def user_in_group(self, login: str, groupname: str) -> bool:
        """Checks if a user is in a specific group."""
        try:
            with self._get_connection() as conn:
                if conn.search(
                    self.base_dn,
                    f"(sAMAccountName={login})",
                    attributes=["distinguishedName"]
                ):
                    logging.debug(f"Проверка групп в которых состоит {login}")
                    user_dn = conn.entries[0].distinguishedName.value
                    if conn.search(user_dn, "(objectClass=*)", attributes=["memberOf"]):
                        groups = (
                            conn.entries[0].memberOf.values
                            if hasattr(conn.entries[0], "memberOf")
                            else []
                        )
                        return groupname in groups
                
                logging.debug(f"Пользователь {login} не найден в базе AD")
                return False
        except Exception as e:
            logging.error(f"Ошибка при проверке пользователя в группе: {e}")
            return False

    def get_users_with_expiring_passwords(self, days: int = 7) -> List[Dict]:
        """Gets users whose passwords will expire in the specified number of days."""
        try:
            with self._get_connection() as conn:
                now = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                expiration_cutoff_date = now + timedelta(days=days)

                conn.search(
                    search_base=self.base_dn,
                    search_filter="(&(objectClass=user)(pwdLastSet=*))",
                    attributes=["sAMAccountName", "pwdLastSet", "displayName"],
                    paged_size=1000
                )

                expiring_users = []
                logging.debug(f"Поиск пользователей с паролем истекающим в близжайшие {days} дней")
                for entry in conn.entries:
                    pwd_last_set = entry.pwdLastSet.value
                    password_expiry_date = (pwd_last_set + timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
                    if now <= password_expiry_date <= expiration_cutoff_date:
                        expiring_users.append({
                            "username": entry.sAMAccountName,
                            "display_name": entry.displayName,
                            "password_expiry_date": password_expiry_date.strftime("%d.%m.%Y")
                        })

                return expiring_users

        except Exception as e:
            logging.error(f"Ошибка при поиске пользователей: {e}")
            return []

    def get_users_with_expired_passwords(self) -> List[Dict]:
        """Gets users whose passwords have expired."""
        try:
            with self._get_connection() as conn:
                now = datetime.now(timezone.utc)

                conn.search(
                    search_base=self.base_dn,
                    search_filter="(&(objectClass=user)(pwdLastSet=*))",
                    attributes=[
                        "sAMAccountName",
                        "pwdLastSet",
                        "displayName",
                        "userAccountControl",
                        "distinguishedName"
                    ],
                    paged_size=1000
                )
                logging.debug(f"Поиск пользователей с истёкшим паролем")
                expired_users = []

                for entry in conn.entries:
                    pwd_last_set = entry.pwdLastSet.value
                    password_expiry_date = pwd_last_set + timedelta(days=90)

                    if now > password_expiry_date:
                        expired_users.append({
                            "username": entry.sAMAccountName,
                            "display_name": entry.displayName,
                            "distinguished_name": entry.distinguishedName,
                            "password_expiry_date": password_expiry_date.strftime("%d.%m.%Y"),
                            "userAccountControl": entry.userAccountControl
                        })

                return expired_users

        except Exception as e:
            logging.error(f"Ошибка при поиске пользователей: {e}")
            return []

    def get_upcoming_birthdays(self, days: int = 30) -> List[Dict]:
        """Gets users with birthdays in the next specified number of days."""
        try:
            with self._get_connection() as conn:
                search_filter = "(&(objectClass=user)(extensionAttribute1=*))"
                conn.search(
                    self.base_dn,
                    search_filter,
                    attributes=["sAMAccountName", "displayName", "extensionAttribute1", "mail"]
                )
                logging.debug(f"Поиск пользователей у которых день рождения близжайшие {days} дней")
                yandex_users = self.ya360.get_yandex_users()
                today = datetime.now()
                future_date = today + timedelta(days=days)
                upcoming_birthdays = []

                for entry in conn.entries:
                    birthday_str = entry.extensionAttribute1.value
                    try:
                        birthday = datetime.strptime(birthday_str, "%d.%m.%Y")
                        birthday_this_year = birthday.replace(year=today.year)

                        if birthday_this_year < today:
                            birthday_this_year = birthday_this_year.replace(year=today.year + 1)

                        user_id = yandex_users.get(entry.mail.value)

                        if today <= birthday_this_year <= future_date:
                            upcoming_birthdays.append({
                                "username": entry.sAMAccountName.value,
                                "display_name": entry.displayName.value,
                                "email": entry.mail.value,
                                "user_id": user_id,
                                "birthday": birthday_this_year.strftime("%d.%m.%Y")
                            })

                    except ValueError:
                        logging.debug(
                            f"Неверный формат даты для пользователя {entry.sAMAccountName.value}: {birthday_str}"
                        )

                return upcoming_birthdays

        except Exception as e:
            logging.error(f"Ошибка при подключении к AD: {e}")
            return []

    def get_user_dn(self, login: str) -> str:
        """Returns the DN of a user by their UPN (login)."""
        try:
            with self._get_connection() as conn:
                logging.debug(f"Поиск DN пользователя {login}")
                search_filter = f"(userPrincipalName={login})"
                conn.search(self.base_dn, search_filter, attributes=["distinguishedName"])

                if len(conn.entries) == 1:
                    return conn.entries[0].distinguishedName.value

                alias = self.ya360.get_user_alias(login)
                if alias:
                    return self.get_user_dn(f"{alias}@tion.ru")

                raise ValueError(
                    f"Пользователь с логином {login} не найден или найдено несколько записей."
                )
        except Exception as e:
            raise ValueError(f"Ошибка при получении DN пользователя: {e}")

    def change_password(self, login: str, new_password: str) -> str:
        """Changes the password for a user in Active Directory."""
        # new_password = utils.generate_random_string()
        try:
            with self._get_connection(use_ssl=True, for_password_change=True) as conn:
                logging.debug(f"Изменение пароля пользователю {login}")
                conn.start_tls()
                conn.extend.microsoft.modify_password(
                    self.get_user_dn(login),
                    new_password=new_password
                )
                if conn.result["result"] == 0:
                    return new_password
                else:
                    logging.error(f"{conn.result['message']}")
                    return f"Ошибка смены пароля: {conn.result['message']}"
        except Exception as e:
            return f"Ошибка смены пароля: {e}"
        
    def check_admin(self, user_login: str):
        username = user_login.split("@")[0]
        # Проверяем кэш
        if username in self._admin_cache:
            is_admin, cache_time = self._admin_cache[username]
            if self._is_cache_valid(cache_time):
                if not is_admin:
                    raise AccessException()
                return
        
        # Если кэша нет или он устарел, проверяем через AD
        try:
            is_admin = self.user_in_group(username, self._get_admin_group_dn())
            # Обновляем кэш
            self._admin_cache[username] = (is_admin, datetime.now())
            
            if not is_admin:
                raise AccessException()
            
        except Exception as e:
            raise AccessException()