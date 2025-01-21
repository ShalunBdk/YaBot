import logging
from typing import Dict, Optional
import requests

from config import settings
from exceptions import Has2FAException


class Yandex360:
    """Class for handling various utility operations."""

    def __init__(self):
        self.headers = {
            "Authorization": f"OAuth {settings.API_TOKEN}",
            "Content-Type": "application/json",
        }
        self.headers_360 = {"Authorization": f"OAuth {settings.API_TOKEN_360}"}

    def _make_yandex_request(self, endpoint: str, method: str = 'get', data: Dict = None) -> Dict:
        """Make a request to Yandex API."""
        url = f"https://api360.yandex.net/directory/v1/org/{settings.ORG_ID}/{endpoint}"
        try:
            if method.lower() == 'get':
                response = requests.get(url, headers=self.headers_360)
            elif method.lower() == 'delete':
                response = requests.delete(url, headers=self.headers_360)
            elif method.lower() == 'post':
                response = requests.post(url, headers=self.headers_360, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error making Yandex API request: {e}")
            return {}

    def get_user_by_surname(self, surname: str) -> Optional[str]:
        """Get user ID by surname."""
        users_data = self._make_yandex_request('users?page=1&perPage=337')
        for user in users_data.get('users', []):
            if user['name']['last'] == surname:
                return user['id']
        return None

    def get_user_by_nickname(self, nickname: str) -> Optional[str]:
        """Get user ID by nickname."""
        users_data = self._make_yandex_request('users?page=1&perPage=337')
        for user in users_data.get('users', []):
            if user['nickname'] == nickname:
                return user['id']
        return None

    def get_nickname_by_id(self, user_id: str) -> Optional[str]:
        """Get nickname by user ID."""
        users_data = self._make_yandex_request('users?page=1&perPage=500')
        for user in users_data.get('users', []):
            if user['id'] == user_id:
                return str(user['nickname'])
        return None

    def get_fio_by_id(self, user_id: str) -> Optional[str]:
        """Get full name by user ID."""
        users_data = self._make_yandex_request('users?page=1&perPage=337')
        for user in users_data.get('users', []):
            if user['id'] == user_id:
                return f"{user['name']['last']} {user['name']['first']} {user['name']['middle']}"
        return None

    def disable_2fa(self, user_id: str) -> str:
        """Disable 2FA for a user."""
        response = self._make_yandex_request(f'users/{user_id}/2fa', method='delete')
        nickname = self.get_nickname_by_id(user_id)
        logging.info(f"Запрос удаление номера 2FA у {nickname}. Ответ: {str(response)}")
        if '400 Client Error: Bad Request for url' not in str(response):
            return f"2FA для {nickname} выключен"
        return f"У аккаунта {nickname} отсутствует защищенный номер телефона"

    def view_blocked_users(self) -> str:
        """View all blocked users."""
        users_data = self._make_yandex_request('users?page=1&perPage=337')
        
        if not users_data or 'users' not in users_data:
            return "Неверные настройки подключения к Yandex API"
            
        blocked_users = []
        count = 0
        for user in users_data['users']:
            if not user['isEnabled'] and not user['isRobot']:
                blocked_users.append(f"EMAIL: {user['email']} | ID: {user['id']}")
                count += 1
                
        return "\n".join(blocked_users) + f"\n\n{count} заблокированных учётных записей"

    def get_yandex_users(self) -> Dict[str, str]:
        """Get Yandex users with their IDs."""
        users_data = self._make_yandex_request('users?perPage=500')
        return {
            user['email'].lower(): user['id']
            for user in users_data.get('users', [])
            if user.get('email') and user.get('id')
        }

    def get_avatar_id(self, user_id: str) -> Optional[str]:
        """Get user's avatar ID."""
        user_data = self._make_yandex_request(f'users/{user_id}')
        return user_data.get('avatarId')

    def get_user_alias(self, login: str) -> Optional[str]:
        """Get Yandex user alias."""
        users_data = self._make_yandex_request('users?perPage=500')
        login_prefix = login.split("@")[0]
        
        for user in users_data.get('users', []):
            if login_prefix == user['nickname'] and user.get('aliases'):
                return user['aliases'][0]
        return None

    def has_2fa(self, login: str) -> Optional[bool]:
        """Check if user has 2FA enabled."""
        user_id = self.get_user_by_nickname(login)
        if not user_id:
            return None
            
        response = self._make_yandex_request(f'users/{user_id}/2fa')
        return response.get('hasSecurityPhone')
    
    def check_2fa(self, login: str):
        """Check if user has 2FA enabled."""
        user_id = self.get_user_by_nickname(login)
        if not user_id:
            return None
            
        response = self._make_yandex_request(f'users/{user_id}/2fa')
        if not response.get('hasSecurityPhone'):
            Has2FAException