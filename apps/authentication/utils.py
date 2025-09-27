import threading
import time
from functools import wraps

from django.core.mail import send_mail
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema


def swagger_helper(tag, operation_id=None):
    def decorator(func):
        @wraps(func)
        @swagger_auto_schema(
            tags=[tag],
            operation_id=operation_id
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


class EmailThread(threading.Thread):
    def __init__(self, subject, message, recipient_list):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        super().__init__()

    def run(self):
        send_mail(
            self.subject,
            self.message,
            settings.EMAIL_HOST_USER,
            self.recipient_list,
        )