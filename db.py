import psycopg2
import os
from dotenv import load_dotenv
import urllib.parse as urlparse

load_dotenv()

def get_connection():
    result = urlparse.urlparse(os.getenv("DATABASE_URL"))
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port

    return psycopg2.connect(
        database=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )
