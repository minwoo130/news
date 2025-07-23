import sys
import os

from dotenv import load_dotenv

sys.path.insert(0, "/var/www/html/news")

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from app import app as application

