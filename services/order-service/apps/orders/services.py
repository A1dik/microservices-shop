from http.client import responses

import requests
import redis
import json
import logging
from django.conf import settings
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class EventBus:

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_response=True
        )

    def publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Публикация события в шину событий."""
        try:
            event_data: {
                'type': event_type,
                'data': data,
                'timestamp': json.dumps({}, default=str)
            }
            self.redis_client.publish('events', json.dumps(event_data))
            logger.info(f"Published event {event_type}")

        except Exception as e:
            logger.error(f"Error publishing event {event_type}: {e}")

event_bus = EventBus()


class CartService:
    """Сервис для взаимодействия с cart-service"""

    @staticmethod
    def get_user_cart(user_id: int, token: str)-> Optional[Dict[str,Any]]:
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{settings.CART_SERVICE_URL}/api/cart/",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching cart for user {user_id}: {e}")
            return None


class ProductService:
    """Сервис для взаимодействия с product-service"""

    @staticmethod
    def reserve_products(items: List[Dict[str,Any]])-> bool:
        """Резервирование продуктов"""
        try:
            for item in items:
                response = requests.post(
                    f"{settings.PRODUCT_SERVICE_URL}/api/products/{item['product_id']}/reserve/",
                    json={'quantity': item['quantity']},
                    timeout=5
                )
                if response != 200:
                    logger.error(f"Failed to reserve product {item['product_id']}")
                    return False
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error reserving products: {e}")
            return False


    @staticmethod
    def release_products(items: List[Dict]):
        """Отмена резерва продуктов"""
        try:
            for item in items:
                requests.post(
                    f"{settings.PRODUCT_SERVICE_URL}/api/products/{item['product_id']}/release/",
                    json={'quantity': item['quantity']},
                    timeout=5
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error releasing products: {e}")


class UserService:

    @staticmethod
    def get_user_from_token(token: str)-> Optional[Dict[str,Any]]:
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
            logger.error(f"Error fetching user info from token: {e}")
            return None
