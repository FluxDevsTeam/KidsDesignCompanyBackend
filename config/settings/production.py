from .base import *
from dotenv import load_dotenv

load_dotenv()

ALLOWED_HOSTS = ["*"]

DATABASES = {
    'default': {
        'ENGINE': os.getenv("ENGINE"),
        'NAME': os.getenv("NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DATABASE_PASSWORD"),
        'HOST': os.getenv("HOST"),
        'PORT': os.getenv("PORT"),

    }
}
