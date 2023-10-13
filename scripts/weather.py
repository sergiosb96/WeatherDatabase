import pymysql
import requests
import os 
import re
import datetime
import time
import logging
from dotenv import  load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Start timer
start_time = time.time()

# Load environment variables
load_dotenv()

# Set logging file and format
def log_to_file(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f'{timestamp} - {message}\n'
    
    with open('logfile.log', 'a') as file:
        file.write(log_message)

# InfluxDB variables
influx_bucket = str(os.getenv('INFLUXDB_BUCKET'))
influx_org = str(os.getenv('INFLUXDB_ORG'))
influx_token = str(os.getenv('INFLUX_TOKEN'))
influx_url = str(os.getenv('INFLUXDB_HOST'))

# Retrieve city data from MariaDB
def retrieve_city_data():
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )

    cur = conn.cursor()
    # Query the database for city data
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, comment FROM cities")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data

# Retrieve query urls from MariaDB
def retrieve_query_urls():
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )

    cur = conn.cursor()
    # Query the database for city data
    cur.execute("SELECT query_urls_id, city_id, daily, hourly , icon, icon_15, gfs, meteofrance FROM query_urls")

    query_urls = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return query_urls

# Retrieve timezones from MariaDB
def retrieve_tz_data():
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cur = conn.cursor()

    # Query the database for city data
    cur.execute("SELECT city_id, lat, lon FROM cities WHERE tz IS NULL OR tz = ''")

    tz_data = cur.fetchall()

    cur.close()
    conn.close()

    return tz_data

def is_it_23_local(utc_offset_seconds_str):

    """Returns True if it's 23:00 local time based on the stored UTC offset in seconds"""
    try:
        utc_offset_seconds = int(utc_offset_seconds_str)
    except ValueError:
        return False

    utc_now = datetime.datetime.utcnow()
    local_time = utc_now + datetime.timedelta(seconds=utc_offset_seconds)
    return local_time.hour == 23

def get_timezone(lat, lon):
    # call open-meteo to get the timezone offset
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m&timezone=auto&forecast_days=1"
    response = requests.get(url)
    response_data = response.json()
    return response_data['utc_offset_seconds']

def local_offset():
    """Get the local timezone offset in hours from UTC."""
    offset_seconds = -time.altzone if time.localtime().tm_isdst else -time.timezone
    return offset_seconds / 3600

def date_to_unixtime(date_string):
    # Specify the input date string
    date_format = "%Y-%m-%d"
    
    # Convert the date string to a datetime object
    date_object = datetime.datetime.strptime(date_string, date_format)

    # Adjust the datetime object by the local timezone offset
    date_object += datetime.timedelta(hours=local_offset())

    # Convert the adjusted datetime object to Unix time
    unix_time = int(date_object.timestamp())
    return unix_time


def time_to_unixtime(date_string):
    # Specify the input date string format
    date_format = "%Y-%m-%dT%H:%M"
    
    # Convert the date string to a datetime object
    datetime_object = datetime.datetime.strptime(date_string, date_format)

    # Adjust the datetime object by the local timezone offset
    datetime_object += datetime.timedelta(hours=local_offset())

    # Convert the adjusted datetime object to Unix time
    unix_time = int(datetime_object.timestamp())
    return unix_time

def validate_and_normalize_coord(d: float) -> float:
    # Convert input to a string if it's not already
    if not isinstance(d, str):
        d = str(d)
    
    # Check if input matches valid format
    match = re.match(r"^(-?\d{1,3}\.\d{1,10})$", d)
    if match:
        # Strip extra decimal places and keep only 3 decimal places
        normalized = f"{float(match.group(1)):.3f}"
        return float(normalized)
    else:
        raise ValueError("Invalid input format. Must be in the format X.X to XXX.XXXXXXXX or -X.X to -XXX.XXXXXXX.")


# Fetch weather data from open-meteo
def fetch_weather_data(url):
    response = requests.get(url)
    data = response.json()
    return data

# Fetch daily weather data from open-meteo
def fetch_daily_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,windspeed_10m_max,winddirection_10m_dominant,shortwave_radiation_sum&timezone=auto"
    return fetch_weather_data(url)
# Fetch hourly weather data from open-meteo
def fetch_hourly_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,windspeed_120m,windspeed_180m,winddirection_10m,winddirection_80m,winddirection_120m,winddirection_180m,windgusts_10m,temperature_80m,temperature_120m,temperature_180m,shortwave_radiation,direct_radiation,diffuse_radiation&forecast_days=2&timezone=auto"
    return fetch_weather_data(url)
# Fetch icon hourly weather data from open-meteo
def fetch_icon_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/dwd-icon?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,windspeed_120m,windspeed_180m,winddirection_10m,winddirection_80m,winddirection_120m,winddirection_180m,windgusts_10m,temperature_80m,temperature_120m,temperature_180m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&timezone=auto"
    return fetch_weather_data(url)
# Fetch icon minutely_15 weather data from open-meteo
def fetch_icon_15_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/dwd-icon?latitude={lat}&longitude={lon}&minutely_15=shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&timezone=auto"
    return fetch_weather_data(url)
# Fetch gfs hourly weather data from open-meteo
def fetch_gfs_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/gfs?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,winddirection_10m,winddirection_80m,windgusts_10m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&forecast_days=2&timezone=auto"
    return fetch_weather_data(url)
# Fetch meteofrance hourly weather data from open-meteo
def fetch_meteofrance_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/meteofrance?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m,windgusts_10m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&forecast_days=2&timezone=auto"
    return fetch_weather_data(url)


# Store daily data in InfluxDB
def store_daily_data_in_influxdb(data, lat, lon, write_api): # daily data from open-meteo
    #get data
    dt = data['daily']['time'][1]
    temp_min = data['daily']['temperature_2m_min'][1]
    temp_max = data['daily']['temperature_2m_max'][1]
    wind_max = data['daily']['windspeed_10m_max'][1]
    wind_dir = data['daily']['winddirection_10m_dominant'][1]
    radiation = data['daily']['shortwave_radiation_sum'][1]
    #add coordinates
    coordinates = lat,lon
    #convert time to unix 
    unix_time = date_to_unixtime(dt)
    write_api.write(influx_bucket, influx_org, [
        Point("daily_forecast")
        .tag("coordinates", coordinates)
        .field("temparature_min_C", temp_min)
        .field("temparature_max_C", temp_max)
        .field("shortwave_radiation_sum", radiation)
        .field("wind_speed", wind_max)
        .field("wind_direction", wind_dir)
        .time(unix_time, write_precision='s')
    ])

# Store hourly data in InfluxDB
def store_hourly_data_in_influxdb(data2, lat, lon, write_api): # hourly data from open-meteo

    coordinates = lat,lon

    timestamps = data2["hourly"]["time"][24:]

    temperatures = data2["hourly"]["temperature_2m"][24:]
    humidities = data2["hourly"]["relativehumidity_2m"][24:]
    windspeed_10m_s = data2["hourly"]["windspeed_10m"][24:]
    windspeed_80m_s = data2["hourly"]["windspeed_80m"][24:]
    windspeed_120m_s = data2["hourly"]["windspeed_120m"][24:]
    windspeed_180m_s = data2["hourly"]["windspeed_180m"][24:]
    winddirection_10m_s = data2["hourly"]["winddirection_10m"][24:]
    winddirection_80m_s = data2["hourly"]["winddirection_80m"][24:]
    winddirection_120m_s = data2["hourly"]["winddirection_120m"][24:]
    winddirection_180m_s = data2["hourly"]["winddirection_180m"][24:]
    temperature_80m_s = data2["hourly"]["temperature_80m"][24:]
    temperature_120m_s = data2["hourly"]["temperature_120m"][24:]
    temperature_180m_s = data2["hourly"]["temperature_180m"][24:]
    shortwave_radiation_s = data2["hourly"]["shortwave_radiation"][24:]
    direct_radiation_s = data2["hourly"]["direct_radiation"][24:]
    diffuse_radiation_s = data2["hourly"]["diffuse_radiation"][24:]

    for timestamp_str, temperature, humidity, \
        windspeed_10m, windspeed_80m, windspeed_120m, windspeed_180m, \
        winddirection_10m, winddirection_80m, winddirection_120m, winddirection_180m, \
        temperature_80m, temperature_120m, temperature_180m, \
        shortwave_radiation, direct_radiation, diffuse_radiation, \
        in zip(timestamps, temperatures, humidities, \
               windspeed_10m_s, windspeed_80m_s, windspeed_120m_s, windspeed_180m_s, \
                winddirection_10m_s, winddirection_80m_s, winddirection_120m_s, winddirection_180m_s, \
                temperature_80m_s, temperature_120m_s, temperature_180m_s, \
                shortwave_radiation_s, direct_radiation_s, diffuse_radiation_s):
        
        unix_time = time_to_unixtime(timestamp_str)

        write_api.write(influx_bucket, influx_org, [
            # Create a Point with the measurement name
            Point("hourly_forecast")
            .tag("coordinates", coordinates)
            .field("temperature", temperature)
            .field("humidity", humidity)
            .field("windspeed_10m", windspeed_10m)
            .field("windspeed_80m", windspeed_80m)
            .field("windspeed_120m", windspeed_120m)
            .field("windspeed_180m", windspeed_180m)
            .field("winddirection_10m", winddirection_10m)
            .field("winddirection_80m", winddirection_80m)
            .field("winddirection_120m", winddirection_120m)
            .field("winddirection_180m", winddirection_180m)
            .field("temperature_80m", temperature_80m)
            .field("temperature_120m", temperature_120m)
            .field("temperature_180m", temperature_180m) 
            .field("shortwave_radiation", shortwave_radiation)
            .field("direct_radiation", direct_radiation)
            .field("diffuse_radiation", diffuse_radiation)

            # Set the timestamp for the Point
            .time(unix_time, write_precision='s')
        ])

# Store icon hourly data in InfluxDB
def store_icon_data_in_influxdb(data3, lat, lon, write_api): # icon hourly data from open-meteo

    coordinates = lat,lon

    timestamps = data3["hourly"]["time"][24:48]

    temperatures = data3["hourly"]["temperature_2m"][24:48]
    humidities = data3["hourly"]["relativehumidity_2m"][24:48]
    windspeed_10m_s = data3["hourly"]["windspeed_10m"][24:48]
    windspeed_80m_s = data3["hourly"]["windspeed_80m"][24:48]
    windspeed_120m_s = data3["hourly"]["windspeed_120m"][24:48]
    windspeed_180m_s = data3["hourly"]["windspeed_180m"][24:48]
    winddirection_10m_s = data3["hourly"]["winddirection_10m"][24:48]
    winddirection_80m_s = data3["hourly"]["winddirection_80m"][24:48]
    winddirection_120m_s = data3["hourly"]["winddirection_120m"][24:48]
    winddirection_180m_s = data3["hourly"]["winddirection_180m"][24:48]
    windgusts_10m_s = data3["hourly"]["windgusts_10m"][24:48]
    temperature_80m_s = data3["hourly"]["temperature_80m"][24:48]
    temperature_120m_s = data3["hourly"]["temperature_120m"][24:48]
    temperature_180m_s = data3["hourly"]["temperature_180m"][24:48]
    shortwave_radiation_s = data3["hourly"]["shortwave_radiation"][24:48]
    direct_radiation_s = data3["hourly"]["direct_radiation"][24:48]
    diffuse_radiation_s = data3["hourly"]["diffuse_radiation"][24:49]
    direct_normal_irradiance_s = data3["hourly"]["direct_normal_irradiance"][24:48]
    terrestrial_radiation_s = data3["hourly"]["terrestrial_radiation"][24:48]

    for timestamp_str, temperature, humidity, \
        windspeed_10m, windspeed_80m, windspeed_120m, windspeed_180m, \
        winddirection_10m, winddirection_80m, winddirection_120m, winddirection_180m, windgusts_10m, \
        temperature_80m, temperature_120m, temperature_180m, \
        shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance, terrestrial_radiation \
        in zip(timestamps, temperatures, humidities, \
               windspeed_10m_s, windspeed_80m_s, windspeed_120m_s, windspeed_180m_s, \
                winddirection_10m_s, winddirection_80m_s, winddirection_120m_s, winddirection_180m_s, windgusts_10m_s, \
                temperature_80m_s, temperature_120m_s, temperature_180m_s, \
                shortwave_radiation_s, direct_radiation_s, diffuse_radiation_s, direct_normal_irradiance_s, terrestrial_radiation_s):
        
        unix_time = time_to_unixtime(timestamp_str)

        write_api.write(influx_bucket, influx_org, [
            # Create a Point with the measurement name
            Point("icon_forecast")
            .tag("coordinates", coordinates)
            .field("temperature", temperature)
            .field("humidity", humidity)
            .field("windspeed_10m", windspeed_10m)
            .field("windspeed_80m", windspeed_80m)
            .field("windspeed_120m", windspeed_120m)
            .field("windspeed_180m", windspeed_180m)
            .field("winddirection_10m", winddirection_10m)
            .field("winddirection_80m", winddirection_80m)
            .field("winddirection_120m", winddirection_120m)
            .field("winddirection_180m", winddirection_180m)
            .field("windgusts_10m", windgusts_10m)
            .field("temperature_80m", temperature_80m)
            .field("temperature_120m", temperature_120m)
            .field("temperature_180m", temperature_180m) 
            .field("shortwave_radiation", shortwave_radiation)
            .field("direct_radiation", direct_radiation)
            .field("diffuse_radiation", diffuse_radiation)
            .field("direct_normal_irradiance", direct_normal_irradiance)
            .field("terrestrial_radiation", terrestrial_radiation)

            # Set the timestamp for the Point
            .time(unix_time, write_precision='s')
        ])

# Store icon minutely_15 data in InfluxDB
def store_icon_15_data_in_influxdb(data4, lat, lon, write_api): # icon minutely_15 data from open-meteo

    coordinates = lat,lon

    timestamps = data4["minutely_15"]["time"][96:192]

    shortwave_radiation_s = data4["minutely_15"]["shortwave_radiation"][96:192]
    direct_radiation_s = data4["minutely_15"]["direct_radiation"][96:192]
    diffuse_radiation_s = data4["minutely_15"]["diffuse_radiation"][96:192]
    direct_normal_irradiance_s = data4["minutely_15"]["direct_normal_irradiance"][96:192]
    terrestrial_radiation_s = data4["minutely_15"]["terrestrial_radiation"][96:192]

    for timestamp_str, shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance, terrestrial_radiation \
        in zip(timestamps, shortwave_radiation_s, direct_radiation_s, diffuse_radiation_s, direct_normal_irradiance_s, terrestrial_radiation_s):
        
        unix_time = time_to_unixtime(timestamp_str)

        write_api.write(influx_bucket, influx_org, [
            # Create a Point with the measurement name
            Point("icon_15_forecast")
            .tag("coordinates", coordinates)
            .field("shortwave_radiation", shortwave_radiation)
            .field("direct_radiation", direct_radiation)
            .field("diffuse_radiation", diffuse_radiation)
            .field("direct_normal_irradiance", direct_normal_irradiance)
            .field("terrestrial_radiation", terrestrial_radiation)

            # Set the timestamp for the Point
            .time(unix_time, write_precision='s')
        ])

# Store gfs hourly data in InfluxDB
def store_gfs_data_in_influxdb(data5, lat, lon, write_api): # hourly data from open-meteo

    coordinates = lat,lon

    timestamps = data5["hourly"]["time"][24:]

    temperatures = data5["hourly"]["temperature_2m"][24:]
    humidities = data5["hourly"]["relativehumidity_2m"][24:]
    windspeed_10m_s = data5["hourly"]["windspeed_10m"][24:]
    windspeed_80m_s = data5["hourly"]["windspeed_80m"][24:]
    winddirection_10m_s = data5["hourly"]["winddirection_10m"][24:]
    winddirection_80m_s = data5["hourly"]["winddirection_80m"][24:]
    windgusts_10m_s = data5["hourly"]["windgusts_10m"][24:]
    shortwave_radiation_s = data5["hourly"]["shortwave_radiation"][24:]
    direct_radiation_s = data5["hourly"]["direct_radiation"][24:]
    diffuse_radiation_s = data5["hourly"]["diffuse_radiation"][24:]
    direct_normal_irradiance_s = data5["hourly"]["direct_normal_irradiance"][24:]
    terrestrial_radiation_s = data5["hourly"]["terrestrial_radiation"][24:]

    for timestamp_str, temperature, humidity, \
        windspeed_10m, windspeed_80m, winddirection_10m, winddirection_80m, windgusts_10m, \
        shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance, terrestrial_radiation\
        in zip(timestamps, temperatures, humidities, windspeed_10m_s, windspeed_80m_s, winddirection_10m_s, winddirection_80m_s, windgusts_10m_s, \
               shortwave_radiation_s, direct_radiation_s, diffuse_radiation_s, direct_normal_irradiance_s, terrestrial_radiation_s):
        

        unix_time = time_to_unixtime(timestamp_str)

        write_api.write(influx_bucket, influx_org, [    
            # Create a Point with the measurement name
            Point("gfs_forecast")
            .tag("coordinates", coordinates)
            .field("temperature", temperature)
            .field("humidity", humidity)
            .field("windspeed_10m", windspeed_10m)
            .field("windspeed_80m", windspeed_80m)
            .field("winddirection_10m", winddirection_10m)
            .field("winddirection_80m", winddirection_80m)
            .field("winddirection_80m", windgusts_10m)
            .field("shortwave_radiation", shortwave_radiation)
            .field("direct_radiation", direct_radiation)
            .field("diffuse_radiation", diffuse_radiation)
            .field("direct_normal_irradiance", direct_normal_irradiance)
            .field("terrestrial_radiation", terrestrial_radiation)

            # Set the timestamp for the Point
            .time(unix_time, write_precision='s')
        ])

# Store meteofrance hourly data in InfluxDB
def store_meteofrance_data_in_influxdb(data6, lat, lon, write_api): # hourly data from open-meteo

    coordinates = lat,lon

    timestamps = data6["hourly"]["time"][24:]

    temperatures = data6["hourly"]["temperature_2m"][24:]
    humidities = data6["hourly"]["relativehumidity_2m"][24:]
    windspeed_10m_s = data6["hourly"]["windspeed_10m"][24:]
    winddirection_10m_s = data6["hourly"]["winddirection_10m"][24:]
    windgusts_10m_s = data6["hourly"]["windgusts_10m"][24:]
    shortwave_radiation_s = data6["hourly"]["shortwave_radiation"][24:]
    direct_radiation_s = data6["hourly"]["direct_radiation"][24:]
    diffuse_radiation_s = data6["hourly"]["diffuse_radiation"][24:]
    direct_normal_irradiance_s = data6["hourly"]["direct_normal_irradiance"][24:]
    terrestrial_radiation_s = data6["hourly"]["terrestrial_radiation"][24:]

    for timestamp_str, temperature, humidity, \
        windspeed_10m, winddirection_10m, windgusts_10m, \
        shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance, terrestrial_radiation\
        in zip(timestamps, temperatures, humidities, windspeed_10m_s, winddirection_10m_s, windgusts_10m_s, \
               shortwave_radiation_s, direct_radiation_s, diffuse_radiation_s, direct_normal_irradiance_s, terrestrial_radiation_s):
        
        unix_time = time_to_unixtime(timestamp_str)

        write_api.write(influx_bucket, influx_org, [
            # Create a Point with the measurement name
            Point("meteofrance_forecast")
            .tag("coordinates", coordinates)
            .field("temperature", temperature)
            .field("humidity", humidity)
            .field("windspeed_10m", windspeed_10m)
            .field("winddirection_10m", winddirection_10m)
            .field("winddirection_80m", windgusts_10m)
            .field("shortwave_radiation", shortwave_radiation)
            .field("direct_radiation", direct_radiation)
            .field("diffuse_radiation", diffuse_radiation)
            .field("direct_normal_irradiance", direct_normal_irradiance)
            .field("terrestrial_radiation", terrestrial_radiation)

            # Set the timestamp for the Point
            .time(unix_time, write_precision='s')
        ])


def fetch_and_store_weather_data():

    # Connect to InfluxDB
    client = InfluxDBClient(url=influx_url, token=influx_token)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Retrieve city data from MariaDB
    city_data = retrieve_city_data()

    # Loop through each city and fetch weather data
    for row in city_data:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, comment = row

        # Check if localtime is 23:00
        if not is_it_23_local(tz):
            log_to_file(f"Data collection skipped for {name} as localtime is not 23:00")
            continue 
        
        # Check if city is active
        if active == 0:
            log_to_file(f"Data collection skipped for {name} as it is not active")
            continue

        try:

            if daily == 1:
                data = fetch_daily_data(lat, lon)
                store_daily_data_in_influxdb(data, lat, lon, write_api)
                log_to_file(f"Daily Data for {name} with {lat},{lon} Stored")
            if hourly == 1:
                data2 = fetch_hourly_data(lat, lon)
                store_hourly_data_in_influxdb(data2, lat, lon, write_api)
                log_to_file(f"Hourly Data for {name} with {lat},{lon} Stored")
            if icon == 1:
                data3 = fetch_icon_data(lat, lon)
                store_icon_data_in_influxdb(data3, lat, lon, write_api)
                log_to_file(f"ICON Data for {name} with {lat},{lon} Stored")
            if icon_15 == 1:
                data4 = fetch_icon_15_data(lat, lon)
                store_icon_15_data_in_influxdb(data4, lat, lon, write_api)
                log_to_file(f"ICON 15 Data for {name} with {lat},{lon} Stored")
            if gfs == 1:
                data5 = fetch_gfs_data(lat, lon)
                store_gfs_data_in_influxdb(data5, lat, lon, write_api)
                log_to_file(f"GFS Data for {name} with {lat},{lon} Stored")
            if meteofrance == 1:
                data6 = fetch_meteofrance_data(lat, lon)
                store_meteofrance_data_in_influxdb(data6, lat, lon, write_api)
                log_to_file(f"Meteofrance Data for {name} with {lat},{lon} Stored")

        except Exception as e:
            logging.error(f"Error fetching weather data for {name} from API: {str(e)}")

    # close database connections
    client.close()



def store_query_urls(city_data):
    try:
        conn = pymysql.connect(
            user=str(os.getenv('MYSQL_USER')),
            password=str(os.getenv('MYSQL_PASSWORD')),
            host=str(os.getenv('MYSQL_HOST')),
            database=str(os.getenv('MYSQL_DB'))
        )
        
        cur = conn.cursor()
        
        # loop through each city and store query URLs
        for row in city_data:
            city_id, _, _, lat, lon, _, _, _, _, _, daily, hourly, icon, icon_15, gfs, meteofrance, _ = row
            
            # check if an entry already exists
            cur.execute("SELECT 1 FROM query_urls WHERE city_id = %s", (city_id,))
            if cur.fetchone():
                continue
            
            daily_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,windspeed_10m_max,winddirection_10m_dominant,shortwave_radiation_sum&timezone=auto" if daily == 1 else None
            hourly_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,windspeed_120m,windspeed_180m,winddirection_10m,winddirection_80m,winddirection_120m,winddirection_180m,windgusts_10m,temperature_80m,temperature_120m,temperature_180m,shortwave_radiation,direct_radiation,diffuse_radiation&forecast_days=2&timezone=auto" if hourly == 1 else None
            icon_url = f"https://api.open-meteo.com/v1/dwd-icon?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,windspeed_120m,windspeed_180m,winddirection_10m,winddirection_80m,winddirection_120m,winddirection_180m,windgusts_10m,temperature_80m,temperature_120m,temperature_180m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&timezone=auto" if icon == 1 else None
            icon_15_url = f"https://api.open-meteo.com/v1/dwd-icon?latitude={lat}&longitude={lon}&minutely_15=shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&timezone=auto" if icon_15 == 1 else None
            gfs_url = f"https://api.open-meteo.com/v1/gfs?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,winddirection_10m,winddirection_80m,windgusts_10m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&forecast_days=2&timezone=auto" if gfs == 1 else None
            meteofrance_url = f"https://api.open-meteo.com/v1/meteofrance?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m,windgusts_10m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&forecast_days=2&timezone=auto" if meteofrance == 1 else None
            
            insert_query = """INSERT INTO query_urls(city_id, daily, hourly, icon, icon_15, gfs, meteofrance) VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            values = (city_id, daily_url, hourly_url, icon_url, icon_15_url, gfs_url, meteofrance_url)

            log_to_file(f"Query URLs for city id {city_id} added")
            
            # execute the query
            cur.execute(insert_query, values)
            conn.commit()

    except Exception as e:
        print("Error while connecting to MySQL", e)
    finally:
        # close connetction
        cur.close()
        conn.close()


def store_timezones(tz_data):
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cur = conn.cursor()

    # loop through each city to fetch and store timezones
    for row in tz_data:
        city_id, _, _, lat, lon, _, _, _, _, _, _, _, _, _, _, _, _ = row

        # check if tz already exists
        cur.execute("SELECT tz FROM cities WHERE city_id = %s", (city_id,))
        if cur.fetchone()[0]:  # If timezone already exists, skip to the next iteration
            continue

        timezone = get_timezone(lat, lon)

        log_to_file(f"Timezone for city id {city_id} added")

        # update the tz
        cur.execute("UPDATE cities SET tz = %s WHERE city_id = %s", (timezone, city_id))
        conn.commit()

    cur.close()
    conn.close()



# Run the script
city_data = retrieve_city_data()
store_query_urls(city_data)
tz_data = retrieve_city_data()
store_timezones(tz_data)
fetch_and_store_weather_data()

# Calculate elapsed time
end_time = time.time()
elapsed_time = end_time - start_time
log_to_file(f"Elapsed Time: {elapsed_time} seconds")