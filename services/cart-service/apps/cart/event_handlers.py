import json
import redis
import threading
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def start_event_listener():
    """Запуск слушателя событий из Redis"""
    try:
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                   db=settings.REDIS_DB, decode_responses=True)
        pubsub = redis_client.pubsub()
        pubsub.subscribe('events')

        logger.info("Cart service event listener started, waiting for events...")

        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    event_data = json.loads(message['data'])
                    handle_event(event_data)
                except Exception as e:
                    logger.error(f"Error processing event message: {e}")

    except Exception as e:
        logger.error(f"Error starting event listener: {e}")


def handle_event(event_data):
    """Обработка полученного события"""
    event_type = event_data.get('type')
    data = event_data.get('data', {})

    if event_type == 'order.created':
        from .models import Cart

        user_id = data.get('user_id')
        if user_id:
            try:
                cart = Cart.objects.get(user_id=user_id)
                cart.clear()
                logger.info(f"Cleared cart for user_id {user_id} after order creation.")
            except Cart.DoesNotExist:
                logger.warning(f"No cart found for user_id {user_id} to clear after order creation.")


if settings.DEBUG:
    thread = threading.Thread(target=start_event_listener, daemon=True)
    thread.start()

