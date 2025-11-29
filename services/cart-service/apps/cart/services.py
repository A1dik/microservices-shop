import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Any

class ProductService:
    """Сервис для взаимодействия с product-service"""

    @staticmethod
    def get_product(product_id: int)-> Optional[Dict[str, Any]]:
        """Получение информации о продукте по ID"""
        try:
            response = requests.get(
                f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching product {product_id}: {e}")
            return None

    @staticmethod
    def check_availability(product_id: int, quantity: int) -> bool:
        """Проверка доступности продукта"""
        try:
            response = requests.get(
                f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/check-availability/",
                params={'quantity': quantity},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('available', False)
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking availability for product {product_id}: {e}")
            return False


class UserService:
    """Сервис для взаимодействия с user-service"""

    @staticmethod
    def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе по JWT токену"""
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{settings.USER_SERVICE_URL}/api/auth/user-info/",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching user info from token: {e}")
            return None
