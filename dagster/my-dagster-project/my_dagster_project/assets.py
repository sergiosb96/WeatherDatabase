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
from dagster import asset, op, graph_asset, multi_asset, AssetOut, graph, AssetIn, job, Output

load_dotenv()

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


@asset 
def influx_env_variable():
    influx_dict = {}
    influx_dict['influx_bucket'] = str(os.getenv('INFLUXDB_BUCKET'))
    influx_dict['influx_org'] = str(os.getenv('INFLUXDB_ORG'))
    influx_dict['influx_token'] = str(os.getenv('INFLUX_TOKEN'))
    influx_dict['influx_url'] = str(os.getenv('INFLUXDB_HOST'))
    return influx_dict
    
    
    
@asset 
def connect_influxdb(influx_env_variable):
    client = InfluxDBClient(url=influx_env_variable['influx_url'], token=influx_env_variable['influx_token'])
    write_api = client.write_api(write_options=SYNCHRONOUS)
    return write_api


#started checking localtime 23:00 
@asset 
def retrieve_city_data_is_it_23_local():
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    # Query the database for city data
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) != 23")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data


@asset
def log_to_file_23_local(retrieve_city_data_is_it_23_local):
    for row in retrieve_city_data_is_it_23_local:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
         
        message = f"Data collection skipped for {name} as it is not 23:00"
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
    
        with open('logfile.log', 'a') as file:
            file.write(log_message)

#ended checking localtime 23:00


# started checking active and storing logs in log filelog

@asset 
def retrieve_city_data_check_active():
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    # Query the database for city data
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE  HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active = 0")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data    

@asset
def log_to_file_check_active(retrieve_city_data_check_active):
    for row in retrieve_city_data_check_active:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        message = f"Data collection skipped for {name} as it is not active"
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
    
        with open('logfile.log', 'a') as file:
            file.write(log_message)
            

# ended checking active and storing logs in log filelog


# started checking horizon and storing logs in log filelog

@asset 
def retrieve_city_data_check_horizon():
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    # Query the database for city data
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE  HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active != 0 AND horizon > datediff(CURDATE(),last_hit)")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data    

@asset
def log_to_file_check_horizon(retrieve_city_data_check_horizon):
    for row in retrieve_city_data_check_horizon:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        message = f"Data collection skipped for {name} as horizon is not reached"
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
    
        with open('logfile.log', 'a') as file:
            file.write(log_message)
            

# ended checking horizon and storing logs in log filelog


# started fetch and store daily data 

@asset 
def retrieve_city_data_daily():
    # Query the database for city data
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active != 0 AND horizon <= datediff(CURDATE(),last_hit) AND daily = 1")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data

@asset 
def fetch_daily_data(retrieve_city_data_daily):
    list_url = []
    temp_list = []
    for row in retrieve_city_data_daily:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        horizon = horizon + 1
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,windspeed_10m_max,winddirection_10m_dominant,shortwave_radiation_sum&timezone=auto&forecast_days={horizon}"
        
        temp_list.append(lat)
        temp_list.append(lon)
        temp_list.append(url)
        temp_list.append(name)
        
        list_url.append(temp_list)
        temp_list = []
    print(list_url)
    return list_url

@asset 
def fetch_weather_data_daily(fetch_daily_data):
    list_data_lat_lon = []
    temp_list = []
    for value in fetch_daily_data:
        response = requests.get(value[2])
        data = response.json()
        temp_list.append(value[0])
        temp_list.append(value[1])
        temp_list.append(data)
        list_data_lat_lon.append(temp_list)
        temp_list = []
    print('---------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(list_data_lat_lon)
    print('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    return list_data_lat_lon

@asset 
def store_daily_data_in_influxdb(fetch_weather_data_daily,connect_influxdb,influx_env_variable):
    for value in fetch_weather_data_daily:
        data = value[2]
        timestamps = data["daily"]["time"][1:]
        temp_min_s = data["daily"]["temperature_2m_min"][1:]
        temp_max_s = data["daily"]["temperature_2m_max"][1:]
        wind_max_s = data["daily"]["windspeed_10m_max"][1:]
        wind_dir_s = data["daily"]["winddirection_10m_dominant"][1:]
        radiation_s = data["daily"]["shortwave_radiation_sum"][1:]

        #add coordinates
        coordinates = value[0],value[1]

        for timestamp_str, temp_min, temp_max, \
            wind_max, wind_dir, radiation, \
            in zip(timestamps, temp_min_s, temp_max_s, \
                wind_max_s, wind_dir_s, radiation_s):
            
            unix_time = date_to_unixtime(timestamp_str)

            connect_influxdb.write(influx_env_variable['influx_bucket'], influx_env_variable['influx_org'], [
                Point("daily_forecast")
                .tag("coordinates", coordinates)
                .field("temparature_min_C", temp_min)
                .field("temparature_max_C", temp_max)
                .field("shortwave_radiation_sum", radiation)
                .field("wind_speed", wind_max)
                .field("wind_direction", wind_dir)
                .time(unix_time, write_precision='s')
            ])
        
@asset
def log_to_file_daily(fetch_daily_data):
    if len(fetch_daily_data) > 0:
        for value in fetch_daily_data:
            message = f"Daily Data for {value[3]} with {value[0]},{value[1]} Stored"
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f'{timestamp} - {message}\n'
        
            with open('logfile.log', 'a') as file:
                file.write(log_message)
    else:
        message = f"No Data Available for Daily Run"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
        
        with open('logfile.log', 'a') as file:
            file.write(log_message)
        
@asset 
def update_last_hit_daily(retrieve_city_data_daily):
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cursor = conn.cursor()
    
    for row in retrieve_city_data_daily:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        today = datetime.datetime.today().date() 
        update_query = "UPDATE cities SET last_hit = %s WHERE city_id = %s"
        cursor.execute(update_query, (today, city_id))
        conn.commit()

# Fetch and Store daily data ended here



#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# started fetch and store hourly data 

@asset 
def retrieve_city_data_hourly():
    # Query the database for city data
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active != 0 AND horizon <= datediff(CURDATE(),last_hit) AND hourly = 1")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data

@asset 
def fetch_hourly_data(retrieve_city_data_hourly):
    list_url = []
    temp_list = []
    for row in retrieve_city_data_hourly:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        horizon = horizon + 1
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,windspeed_120m,windspeed_180m,winddirection_10m,winddirection_80m,winddirection_120m,winddirection_180m,windgusts_10m,temperature_80m,temperature_120m,temperature_180m,shortwave_radiation,direct_radiation,diffuse_radiation&forecast_days=2&timezone=auto&forecast_days={horizon}"
        
        temp_list.append(lat)
        temp_list.append(lon)
        temp_list.append(url)
        temp_list.append(name)
        
        list_url.append(temp_list)
        temp_list = []
    print(list_url)
    return list_url

@asset 
def fetch_weather_data_hourly(fetch_hourly_data):
    list_data_lat_lon = []
    temp_list = []
    for value in fetch_hourly_data:
        response = requests.get(value[2])
        data = response.json()
        temp_list.append(value[0])
        temp_list.append(value[1])
        temp_list.append(data)
        list_data_lat_lon.append(temp_list)
        temp_list = []
    print('---------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(list_data_lat_lon)
    print('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    return list_data_lat_lon

@asset 
def store_hourly_data_in_influxdb(fetch_weather_data_hourly,connect_influxdb,influx_env_variable):
    for value in fetch_weather_data_hourly:
        coordinates = value[0],value[1]
        data2 = value[2]
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

            connect_influxdb.write(influx_env_variable['influx_bucket'], influx_env_variable['influx_org'], [
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
        
@asset
def log_to_file_hourly(fetch_hourly_data):
    print(fetch_hourly_data)
    print(len(fetch_hourly_data))
    if len(fetch_hourly_data) > 0:
        for value in fetch_hourly_data:
            message = f"Hourly Data for {value[3]} with {value[0]},{value[1]} Stored"
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f'{timestamp} - {message}\n'
        
            with open('logfile.log', 'a') as file:
                file.write(log_message)
    else:
        message = f"No Data Available for Hourly Run"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
        
        with open('logfile.log', 'a') as file:
            file.write(log_message)
        
        
@asset 
def update_last_hit_hourly(retrieve_city_data_hourly):
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cursor = conn.cursor()
    
    for row in retrieve_city_data_hourly:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        today = datetime.datetime.today().date() 
        update_query = "UPDATE cities SET last_hit = %s WHERE city_id = %s"
        cursor.execute(update_query, (today, city_id))
        conn.commit()

# Fetch and Store hourly data ended here

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# started fetch and store icon data 

@asset 
def retrieve_city_data_icon():
    # Query the database for city data
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active != 0 AND horizon <= datediff(CURDATE(),last_hit) AND icon = 1")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data

@asset 
def fetch_icon_data(retrieve_city_data_icon):
    list_url = []
    temp_list = []
    for row in retrieve_city_data_icon:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        horizon = horizon + 1
        
        url = f"https://api.open-meteo.com/v1/dwd-icon?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,windspeed_120m,windspeed_180m,winddirection_10m,winddirection_80m,winddirection_120m,winddirection_180m,windgusts_10m,temperature_80m,temperature_120m,temperature_180m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&timezone=auto&forecast_days={horizon}"
        
        temp_list.append(lat)
        temp_list.append(lon)
        temp_list.append(url)
        temp_list.append(name)
        
        list_url.append(temp_list)
        temp_list = []
    print(list_url)
    return list_url

@asset 
def fetch_weather_data_icon(fetch_icon_data):
    list_data_lat_lon = []
    temp_list = []
    for value in fetch_icon_data:
        response = requests.get(value[2])
        data = response.json()
        temp_list.append(value[0])
        temp_list.append(value[1])
        temp_list.append(data)
        list_data_lat_lon.append(temp_list)
        temp_list = []
    print('---------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(list_data_lat_lon)
    print('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    return list_data_lat_lon

@asset 
def store_icon_data_in_influxdb(fetch_weather_data_icon,connect_influxdb,influx_env_variable):
    for value in fetch_weather_data_icon:
        coordinates = value[0],value[1]
        data3 = value[2]
        timestamps = data3["hourly"]["time"][24:]

        temperatures = data3["hourly"]["temperature_2m"][24:]
        humidities = data3["hourly"]["relativehumidity_2m"][24:]
        windspeed_10m_s = data3["hourly"]["windspeed_10m"][24:]
        windspeed_80m_s = data3["hourly"]["windspeed_80m"][24:]
        windspeed_120m_s = data3["hourly"]["windspeed_120m"][24:]
        windspeed_180m_s = data3["hourly"]["windspeed_180m"][24:]
        winddirection_10m_s = data3["hourly"]["winddirection_10m"][24:]
        winddirection_80m_s = data3["hourly"]["winddirection_80m"][24:]
        winddirection_120m_s = data3["hourly"]["winddirection_120m"][24:]
        winddirection_180m_s = data3["hourly"]["winddirection_180m"][24:]
        windgusts_10m_s = data3["hourly"]["windgusts_10m"][24:]
        temperature_80m_s = data3["hourly"]["temperature_80m"][24:]
        temperature_120m_s = data3["hourly"]["temperature_120m"][24:]
        temperature_180m_s = data3["hourly"]["temperature_180m"][24:]
        shortwave_radiation_s = data3["hourly"]["shortwave_radiation"][24:]
        direct_radiation_s = data3["hourly"]["direct_radiation"][24:]
        diffuse_radiation_s = data3["hourly"]["diffuse_radiation"][24:]
        direct_normal_irradiance_s = data3["hourly"]["direct_normal_irradiance"][24:]
        terrestrial_radiation_s = data3["hourly"]["terrestrial_radiation"][24:]

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

            connect_influxdb.write(influx_env_variable['influx_bucket'], influx_env_variable['influx_org'], [
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
        
@asset
def log_to_file_icon(fetch_icon_data):
    if len(fetch_icon_data) > 0:
        for value in fetch_icon_data:
            message = f"ICON Data for {value[3]} with {value[0]},{value[1]} Stored"
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f'{timestamp} - {message}\n'
        
            with open('logfile.log', 'a') as file:
                file.write(log_message)
    else:
        message = f"No Data Available for ICON Run"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
        
        with open('logfile.log', 'a') as file:
            file.write(log_message)
        
@asset 
def update_last_hit_icon(retrieve_city_data_icon):
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cursor = conn.cursor()
    
    for row in retrieve_city_data_icon:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        today = datetime.datetime.today().date() 
        update_query = "UPDATE cities SET last_hit = %s WHERE city_id = %s"
        cursor.execute(update_query, (today, city_id))
        conn.commit()

# Fetch and Store icon data ended here

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# started fetch and store icon_15 data 

@asset 
def retrieve_city_data_icon_15():
    # Query the database for city data
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active != 0 AND horizon <= datediff(CURDATE(),last_hit) AND icon_15 = 1")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data

@asset 
def fetch_icon_15_data(retrieve_city_data_icon_15):
    list_url = []
    temp_list = []
    for row in retrieve_city_data_icon_15:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        horizon = horizon + 1
        
        url = f"https://api.open-meteo.com/v1/dwd-icon?latitude={lat}&longitude={lon}&minutely_15=shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&timezone=auto&forecast_days={horizon}"
        
        temp_list.append(lat)
        temp_list.append(lon)
        temp_list.append(url)
        temp_list.append(name)
        
        list_url.append(temp_list)
        temp_list = []
    print(list_url)
    return list_url

@asset 
def fetch_weather_data_icon_15(fetch_icon_15_data):
    list_data_lat_lon = []
    temp_list = []
    for value in fetch_icon_15_data:
        response = requests.get(value[2])
        data = response.json()
        temp_list.append(value[0])
        temp_list.append(value[1])
        temp_list.append(data)
        list_data_lat_lon.append(temp_list)
        temp_list = []
    print('---------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(list_data_lat_lon)
    print('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    return list_data_lat_lon

@asset 
def store_icon_15_data_in_influxdb(fetch_weather_data_icon_15,connect_influxdb,influx_env_variable):
    for value in fetch_weather_data_icon_15:
        coordinates = value[0],value[1]
        data4 = value[2]
        timestamps = data4["minutely_15"]["time"][96:]

        shortwave_radiation_s = data4["minutely_15"]["shortwave_radiation"][96:]
        direct_radiation_s = data4["minutely_15"]["direct_radiation"][96:]
        diffuse_radiation_s = data4["minutely_15"]["diffuse_radiation"][96:]
        direct_normal_irradiance_s = data4["minutely_15"]["direct_normal_irradiance"][96:]
        terrestrial_radiation_s = data4["minutely_15"]["terrestrial_radiation"][96:]

        for timestamp_str, shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance, terrestrial_radiation \
            in zip(timestamps, shortwave_radiation_s, direct_radiation_s, diffuse_radiation_s, direct_normal_irradiance_s, terrestrial_radiation_s):
            
            unix_time = time_to_unixtime(timestamp_str)

            connect_influxdb.write(influx_env_variable['influx_bucket'], influx_env_variable['influx_org'], [
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
        
@asset
def log_to_file_icon_15(fetch_icon_15_data):
    if len(fetch_icon_15_data) > 0:
        for value in fetch_icon_15_data:
            message = f"ICON-15 Data for {value[3]} with {value[0]},{value[1]} Stored"
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f'{timestamp} - {message}\n'
        
            with open('logfile.log', 'a') as file:
                file.write(log_message)
    else:
        message = f"No Data Available for ICON-15 Run"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
        
        with open('logfile.log', 'a') as file:
            file.write(log_message)

@asset 
def update_last_hit_icon_15(retrieve_city_data_icon_15):
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cursor = conn.cursor()
    
    for row in retrieve_city_data_icon_15:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        today = datetime.datetime.today().date() 
        update_query = "UPDATE cities SET last_hit = %s WHERE city_id = %s"
        cursor.execute(update_query, (today, city_id))
        conn.commit()


# Fetch and Store icon 15 data ended here

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# started fetch and store gfs data 

@asset 
def retrieve_city_data_gfs():
    # Query the database for city data
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active != 0 AND horizon <= datediff(CURDATE(),last_hit) AND gfs = 1")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data

@asset 
def fetch_gfs_data(retrieve_city_data_gfs):
    list_url = []
    temp_list = []
    for row in retrieve_city_data_gfs:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        horizon = horizon + 1
        url = f"https://api.open-meteo.com/v1/gfs?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,windspeed_80m,winddirection_10m,winddirection_80m,windgusts_10m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&forecast_days=2&timezone=auto&forecast_days={horizon}"
        
        temp_list.append(lat)
        temp_list.append(lon)
        temp_list.append(url)
        temp_list.append(name)
        
        list_url.append(temp_list)
        temp_list = []
    print(list_url)
    return list_url

@asset 
def fetch_weather_data_gfs(fetch_gfs_data):
    list_data_lat_lon = []
    temp_list = []
    for value in fetch_gfs_data:
        response = requests.get(value[2])
        data = response.json()
        temp_list.append(value[0])
        temp_list.append(value[1])
        temp_list.append(data)
        list_data_lat_lon.append(temp_list)
        temp_list = []
    print('---------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(list_data_lat_lon)
    print('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    return list_data_lat_lon

@asset 
def store_gfs_data_in_influxdb(fetch_weather_data_gfs,connect_influxdb,influx_env_variable):
    for value in fetch_weather_data_gfs:
        coordinates = value[0],value[1]
        data5 = value[2]
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

            connect_influxdb.write(influx_env_variable['influx_bucket'], influx_env_variable['influx_org'], [    
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

        
@asset
def log_to_file_gfs(fetch_gfs_data):
    if len(fetch_gfs_data) > 0:
        for value in fetch_gfs_data:
            message = f"GFS Data for {value[3]} with {value[0]},{value[1]} Stored"
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f'{timestamp} - {message}\n'
        
            with open('logfile.log', 'a') as file:
                file.write(log_message)
    else:
        message = f"No Data Available for GFS Run"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
        
        with open('logfile.log', 'a') as file:
            file.write(log_message)
        
@asset 
def update_last_hit_gfs(retrieve_city_data_gfs):
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cursor = conn.cursor()
    
    for row in retrieve_city_data_gfs:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        today = datetime.datetime.today().date() 
        update_query = "UPDATE cities SET last_hit = %s WHERE city_id = %s"
        cursor.execute(update_query, (today, city_id))
        conn.commit()

# Fetch and Store gfs data ended here

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# started fetch and store meteofrance data 

@asset 
def retrieve_city_data_meteofrance():
    # Query the database for city data
    conn = pymysql.connect(user=str(os.getenv('MYSQL_USER')),password=str(os.getenv('MYSQL_PASSWORD')),host=str(os.getenv('MYSQL_HOST')),database=str(os.getenv('MYSQL_DB')))
    cur = conn.cursor()
    cur.execute("SELECT city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit FROM cities WHERE HOUR(DATE_ADD(UTC_TIMESTAMP(),INTERVAL tz SECOND)) = 23 AND active != 0 AND horizon <= datediff(CURDATE(),last_hit) AND meteofrance = 1")

    city_data = cur.fetchall()
    # Close database connections
    cur.close()
    conn.close()

    return city_data

@asset 
def fetch_meteofrance_data(retrieve_city_data_meteofrance):
    list_url = []
    temp_list = []
    for row in retrieve_city_data_meteofrance:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        horizon = horizon + 1
        
        url = f"https://api.open-meteo.com/v1/meteofrance?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m,windgusts_10m,shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,terrestrial_radiation&forecast_days=2&timezone=auto&forecast_days={horizon}"
        
        temp_list.append(lat)
        temp_list.append(lon)
        temp_list.append(url)
        temp_list.append(name)
        
        list_url.append(temp_list)
        temp_list = []
    print(list_url)
    return list_url

@asset 
def fetch_weather_data_meteofrance(fetch_meteofrance_data):
    list_data_lat_lon = []
    temp_list = []
    for value in fetch_meteofrance_data:
        response = requests.get(value[2])
        data = response.json()
        temp_list.append(value[0])
        temp_list.append(value[1])
        temp_list.append(data)
        list_data_lat_lon.append(temp_list)
        temp_list = []
    print('---------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(list_data_lat_lon)
    print('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    return list_data_lat_lon

@asset 
def store_meteofrance_data_in_influxdb(fetch_weather_data_meteofrance,connect_influxdb,influx_env_variable):
    for value in fetch_weather_data_meteofrance:
        coordinates = value[0],value[1]
        data6 = value[2]
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

            connect_influxdb.write(influx_env_variable['influx_bucket'], influx_env_variable['influx_org'], [
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
        
@asset
def log_to_file_meteofrance(fetch_meteofrance_data):
    if len(fetch_meteofrance_data) > 0:
        for value in fetch_meteofrance_data:
            message = f"MeteoFrance Data for {value[3]} with {value[0]},{value[1]} Stored"
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f'{timestamp} - {message}\n'
        
            with open('logfile.log', 'a') as file:
                file.write(log_message)
    else:
        message = f"No Data Available for MeteoFrance Run"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'{timestamp} - {message}\n'
        
        with open('logfile.log', 'a') as file:
            file.write(log_message)

@asset 
def update_last_hit_meteofrance(retrieve_city_data_meteofrance):
    conn = pymysql.connect(
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
        host=str(os.getenv('MYSQL_HOST')),
        database=str(os.getenv('MYSQL_DB'))
    )
    cursor = conn.cursor()
    
    for row in retrieve_city_data_meteofrance:
        city_id, active, name, lat, lon, tz, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, horizon, comment, last_hit = row
        
        today = datetime.datetime.today().date() 
        update_query = "UPDATE cities SET last_hit = %s WHERE city_id = %s"
        cursor.execute(update_query, (today, city_id))
        conn.commit()


# Fetch and Store meteofrance data ended here

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
