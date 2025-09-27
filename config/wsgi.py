import os
from dotenv import load_dotenv
from whitenoise import WhiteNoise
from django.core.wsgi import get_wsgi_application
load_dotenv()

# Get DJANGO_ENV from .env file (defaults to 'development' if not set)
django_env = os.getenv("DJANGO_ENV", "development").lower()

# Map DJANGO_ENV to the corresponding settings module
settings_module = f"config.settings.{django_env}"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

application = get_wsgi_application()
application = WhiteNoise(application)
