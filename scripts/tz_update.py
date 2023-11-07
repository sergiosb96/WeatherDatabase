import requests
import pymysql
from dotenv import  load_dotenv
import os


load_dotenv()

conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
cursor = conn.cursor()

cursor.execute("SELECT city_id, lat, lon FROM cities")
cities = cursor.fetchall()

for city in cities:
    city_id, lat, lon = city

    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m&timezone=auto&forecast_days=1"
    response = requests.get(api_url)
    data = response.json()

    utc_offset_in_seconds = data['utc_offset_seconds']
    print(utc_offset_in_seconds)

    cursor.execute(
        "UPDATE cities SET tz = %s WHERE city_id = %s",
        (utc_offset_in_seconds, city_id)
    )
    conn.commit()

cursor.close()
conn.close()
