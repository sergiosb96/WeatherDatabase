from flask import Flask, session, render_template, request, redirect, url_for, g, send_file, jsonify, flash as flash_message
from flask_mysqldb import MySQL
from werkzeug.utils import url_quote
import pandas as pd
import plotly.express as px
import random 
from bokeh.plotting import figure
from bokeh.embed import components
from datetime import datetime, timedelta
import requests
import os
import re
import csv
from collections import OrderedDict
import json
from io import StringIO
from dotenv import  load_dotenv
from influxdb_client import InfluxDBClient

app = Flask(__name__)

load_dotenv()

# InfluxDB variables
influx_bucket = str(os.getenv('INFLUXDB_BUCKET'))
influx_org = str(os.getenv('INFLUXDB_ORG'))
influx_token = str(os.getenv('INFLUX_TOKEN'))
influx_url = str(os.getenv('INFLUXDB_HOST'))

# SQL variables
app.config['MYSQL_HOST'] = str(os.getenv('MYSQL_HOST'))
app.config['MYSQL_USER'] = str(os.getenv('MYSQL_USER'))
app.config['MYSQL_PASSWORD'] = str(os.getenv('MYSQL_PASSWORD'))
app.config['MYSQL_DB'] = str(os.getenv('MYSQL_DB'))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

google_api_key = str(os.getenv('GOOGLE'))
api_key = str(os.getenv('OW'))
app.secret_key = os.urandom(24)

mysql = MySQL(app)

def get_db():
    if 'db' not in g:
        g.db = mysql.connection
    return g.db

def city_exists(city):
    sql = "SELECT name FROM cities WHERE name = %s"
    val = (city,)
    cur = mysql.connection.cursor()
    cur.execute(sql, val)
    result = cur.fetchone()
    if result:
        return True
    else:
        return False

def coord_exists(lat, lon):
    
    cur = mysql.connection.cursor()
    cur.execute('SELECT COUNT(*) FROM cities WHERE abs(lat - %s) < 0.0001 AND abs(lon - %s) < 0.0001', (lat, lon))
    count = cur.fetchone()[0]
    
    if count > 0:
       return True
    else:
        return False
    
def validate_and_normalize_coord(d: float) -> float:
    # convert input to a string
    if not isinstance(d, str):
        d = str(d)
    
    # check if input matches valid format
    match = re.match(r"^(-?\d{1,3}\.\d{1,15})$", d)
    if match:
        # remove extra decimal places and keep only 3 decimal places
        normalized = f"{float(match.group(1)):.3f}"
        return float(normalized)
    else:
        return None

def fetch_cities_from_database(city_id=None):
    cur = get_db().cursor()
    
    if city_id:
        cur.execute("SELECT city_id, name, lat, lon, added, started FROM cities WHERE city_id = %s", (city_id,))
        city = cur.fetchone()
        cur.close()
        return city
    else:
        cur.execute("SELECT city_id, name, lat, lon, added, started FROM cities")
        cities = cur.fetchall()
        cur.close()
        return cities


def fetch_query_urls_from_database(city_id):
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT daily, hourly, icon, icon_15, gfs, meteofrance FROM query_urls WHERE city_id=%s"
    cur.execute(query, (city_id,))
    row = cur.fetchone()
    cur.close()
    
    if row is None:
        return {}
    
    return {
        "daily_forecast": row[0],
        "hourly_forecast": row[1],
        "icon_forecast": row[2],
        "icon_15_forecast": row[3],
        "gfs_forecast": row[4],
        "meteofrance_forecast": row[5]
    }


def fetch_coordinates_from_database(city_id):
    cur = get_db().cursor()
    cur.execute("SELECT lon, lat FROM cities WHERE city_id=%s", (city_id,))
    coordinates = cur.fetchone()
    cur.close()
    return coordinates

def generate_query_api_url(city_coordinates, selected_sources, start_date, end_date):
    city_lon, city_lat = city_coordinates
    api_base_url = str(os.getenv('API_BASE_URL'))
    api_url = f'{api_base_url}api/influx/query?source={(selected_sources)}&coordinates=({city_lat}, {city_lon})&start_date={start_date}&end_date={end_date}'

    return api_url

def generate_data_api_url(city_coordinates, selected_sources, start_date, end_date):
    city_lon, city_lat = city_coordinates
    api_base_url = str(os.getenv('API_BASE_URL'))
    api_url = f'{api_base_url}api/v1/query?source={(selected_sources)}&coordinates=({city_lat}, {city_lon})&start_date={start_date}&end_date={end_date}'

    return api_url

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/api/docs', methods=['GET', 'POST'])
def docs():
    
    api_base_url = str(os.getenv('API_BASE_URL'))

    return render_template('docs.html', api_base_url=api_base_url)


def get_random_color():
    return 'rgba({}, {}, {}, 1)'.format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

@app.route('/data_charts', methods=['GET', 'POST'])
def data_charts():
    cities = fetch_cities_from_database()

    if request.method == 'POST':
        # get data from the form
        selected_city = request.form.get('city_name')
        selected_sources = request.form.get('sources')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        selected_city_id = int(request.form.get('city_id'))

        # Diagnostic Print
        print(f"Selected City: {selected_city}, Data Source: {selected_sources}, Start Date: {start_date}, End Date: {end_date}")

        # convert to datetime
        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # calculate the difference in days
        day_difference = (end_date_dt - start_date_dt).days

        # fetch the coordinates for the selected city from the database
        city_coordinates = fetch_coordinates_from_database(selected_city_id)

        # combine the information into an API URL
        query_url = generate_query_api_url(city_coordinates, selected_sources, start_date, end_date)
        query_api_response = requests.get(query_url).json()

        # Diagnostic Print
        print(f"API Response Length: {len(query_api_response)}")

        dfs = {}

        if day_difference > 10:
            print("Error: Date range is more than 10 days")
            # Using flash to show error messages to user, but you can handle this in another way.
            flash_message('Date range is more than 10 days', 'error')
            return render_template('data_charts.html', cities=cities)

        if not query_api_response:
            print("Error: There is no data available for the selected date range")
            flash_message('There is no data available for the selected date range', 'error')
            return render_template('data_charts.html', cities=cities)

        for data in query_api_response:
            records = data['records']
            for record in records:
                field = record['values']['_field']
                values = {
                    '_time': record['values']['_time'][:16],
                    '_value': str(record['values']['_value'])[:6]
                }
                if field not in dfs:
                    dfs[field] = pd.DataFrame()
                df = pd.DataFrame(values, index=[0])
                dfs[field] = pd.concat([dfs[field], df], ignore_index=True)

        # Convert dfs into a single combined dataset for Chart.js
        labels = list(dfs.values())[0]['_time'].tolist()  # Assuming all dfs have same _time values
        datasets = []

        color_index = 0
        for key, field, df in dfs.items():
            datasets.append({
                'label': field,
                'data': df['_value'].tolist(),
                'borderColor': get_random_color(),
                'yAxisID': 'y-axis-' + key,
                'fill': False
            })

        chart_data = {
            'labels': labels,
            'datasets': datasets
        }

        # Diagnostic Print
        print(f"Chart Data: {chart_data}")

        session['chart_data'] = chart_data
        return render_template(
            'data_charts.html', 
            cities=cities,
            chart_data=chart_data, 
            selected_city=selected_city,
            city_coordinates=city_coordinates,
            measurement=selected_sources,
            start_date=start_date,
            end_date=end_date
        )


    return render_template('data_charts.html', cities=cities)


@app.route('/data_tables', methods=['GET', 'POST'])
def data_tables():
    cities = fetch_cities_from_database()

    if request.method == 'POST':
        # get data from the form
        selected_city = request.form.get('city_name')
        selected_sources = request.form.get('sources')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        selected_city_id = int(request.form.get('city_id'))

        # convert to datetime
        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # calculate the difference in days
        day_difference = (end_date_dt - start_date_dt).days

        # fetch the coordinates for the selected city from the database
        city_coordinates = fetch_coordinates_from_database(selected_city_id)

        # combine the information into an API URL
        query_url = generate_query_api_url(city_coordinates, selected_sources, start_date, end_date)
        query_api_response = requests.get(query_url).json()

        dfs = {}

        if day_difference > 10:
            return jsonify({'error': 'Date range is more than 10 days'})
        
        if not query_api_response:
            return jsonify({'error': 'There is no data available for the selected date range'})

        for data in query_api_response:

            records = data['records']

            for record in records:

                field = record['values']['_field']
                values = {
                    '_time': record['values']['_time'][:16],
                    '_value': str(record['values']['_value'])[:6]
                }

                if field not in dfs:
                    dfs[field] = pd.DataFrame()

                df = pd.DataFrame(values, index=[0])
                dfs[field] = pd.concat([dfs[field], df], ignore_index=True)

        return jsonify({
            'template': render_template('data_tables.html', cities=cities, dfs=dfs,
                                        city_coordinates=city_coordinates, start_date=start_date, 
                                        end_date=end_date, selected_city=selected_city, 
                                        selected_sources=selected_sources, 
                                        measurement=query_api_response[0]['records'][0]['values']['_measurement'])
        }) 

    return render_template('data_tables.html', cities=cities)




@app.route('/api', methods=['GET', 'POST'])
def data():
    cities = fetch_cities_from_database()

    if request.method == 'POST':
        # get data from the form
        selected_city = request.form.get('city_name')
        selected_sources = request.form.get('sources')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        selected_city_id = int(request.form.get('city_id'))

        # Fetch detailed city info, including "started" and "added", for the selected city
        city_details = fetch_cities_from_database(selected_city_id)
        started = city_details[5]
        added = city_details[4]

        # fetch the coordinates for the selected city from the database
        city_coordinates = fetch_coordinates_from_database(selected_city_id)

        # combine the information into an API URL
        api_url = generate_data_api_url(city_coordinates, selected_sources, start_date, end_date)

        weather_query_urls = fetch_query_urls_from_database(selected_city_id)
        url_to_use = weather_query_urls.get(selected_sources, None)

        if not api_url:
            return render_template('no_data.html', cities=cities, api_url=api_url, city_coordinates=city_coordinates, 
                                   url_to_use=url_to_use, start_date=start_date, end_date=end_date, selected_city=selected_city, 
                                   selected_sources=selected_sources, started=started, added=added)
            
        return render_template('api.html', cities=cities, api_url=api_url, url_to_use=url_to_use, city_coordinates=city_coordinates,
                               start_date=start_date, end_date=end_date, selected_city=selected_city, selected_sources=selected_sources,
                               started=started, added=added)

    return render_template('api.html', cities=cities)


@app.route('/export_csv', methods=['POST'])
def export_csv():
    api_url = request.form.get('api_url')
    measurement = request.form.get('measurement')
    coordinates = request.form.get('coordinates')
    url_to_use = request.form.get('url_to_use')
    selected_city = request.form.get('selected_city')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    added = request.form.get('added')
    started = request.form.get('started')
    
    response = requests.get(api_url)
    if response.status_code != 200:
        return 'Failed to retrieve data', 500
    
    api_data = response.json()
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"data_export__for_{coordinates}_at_{timestamp}.csv"
    
    new_rows = [
        ['API url:', api_url, ''],
        ['Open-Meteo url:', url_to_use, ''],
        ['City:', selected_city, ''],
        ['Coordinates:', coordinates, ''],
        ['Data_Source:', measurement, ''],
        ['Start:', start_date, ''],
        ['End:', end_date, ''],
        ['Added:', added, ''],
        ['Started:', started, '']
    ]
    
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(new_rows)
        
        times = api_data.get('time', [])
        results = api_data.get('results', {})
        
        if times and results:

            header = ['Time'] + list(results.keys())
            writer.writerow(header)
            
            for i, time in enumerate(times):
                row = [time]
                for key, measurement in results.items():
                    values = measurement.get('value', [])
                    row.append(values[i] if i < len(values) else '')
                writer.writerow(row)
                
    return send_file(filename, as_attachment=True)


@app.route('/export_json', methods=['POST'])
def export_json():
    api_url = request.form.get('api_url')
    coordinates = request.form.get('coordinates')
    url_to_use = request.form.get('url_to_use')
    
    response = requests.get(api_url)
    
    if response.status_code != 200:
        return 'Failed to retrieve data', 500
    
    api_data = response.json()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"data_export__for_{coordinates}_at_{timestamp}.json"

    export_data = {
        'API url': api_url,
        'Open-Meteo url': url_to_use,
        'API Data': api_data
    }

    with open(filename, 'w') as file:
        file.write(json.dumps(export_data, indent=4)) 
    
    return send_file(filename, as_attachment=True)



@app.route('/cities', methods=['GET', 'POST'])
def cities():
    if request.method == 'POST':
        search = request.form['search']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM cities WHERE name LIKE %s", ('%' + search + '%',))
        cities = cur.fetchall()
        cur.close()
        return render_template('cities.html', cities=cities)
    else:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM cities")
        cities = cur.fetchall()
        cur.close()
        return render_template('cities.html', cities=cities)


@app.route('/cities/add', methods=['POST'])
def add_city():
    city = request.form['city']
    daily = request.form['daily']
    hourly = request.form['hourly']
    icon = request.form['icon']
    icon_15 = request.form['icon_15']
    gfs = request.form['gfs']
    meteofrance = request.form['meteofrance']
    comment = request.form['comment']

    current_date = datetime.now().date()
    next_day_date = current_date + timedelta(days=1)


    if city_exists(city):
        flash_message(f'{city} is already on the list of cities.')
    else:
        url = f'https://maps.googleapis.com/maps/api/geocode/json?address={city}&key={google_api_key}'
        response = requests.get(url).json()
        if response['status'] == "ZERO_RESULTS":
            flash_message('Invalid city name! Please try again...')
            return redirect(('/cities'))
        else:

            for result in response["results"]:
                for component in result["address_components"]:
                    if "country" in component["types"]:
                       country = component["long_name"]
                       country_code = component["short_name"]

    
        lat = response['results'][0]['geometry']['location']['lat']
        lon = response['results'][0]['geometry']['location']['lng']

        lat_valid = validate_and_normalize_coord(lat)
        lon_valid = validate_and_normalize_coord(lon)

        with get_db().cursor() as cursor:
            query = "INSERT INTO cities (name, lat, lon, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, comment) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (city, lat_valid, lon_valid, country, country_code, current_date, next_day_date, daily, hourly , icon, icon_15, gfs, meteofrance, comment))
        get_db().commit()

        flash_message(f'{city} has been added to the list. The closest coordinates are {lat_valid} & {lon_valid}')
    return redirect(('/cities'))

@app.route('/cities/add-coords', methods=['POST'])
def add_city_coords():
    lat = request.form['lat']
    lon = request.form['lon']
    daily = request.form['daily']
    hourly = request.form['hourly']
    icon = request.form['icon']
    icon_15 = request.form['icon_15']
    gfs = request.form['gfs']
    meteofrance = request.form['meteofrance']
    comment = request.form['comment']

    current_date = datetime.now().date()
    next_day_date = current_date + timedelta(days=1)

    lat_valid = validate_and_normalize_coord(lat)
    lon_valid = validate_and_normalize_coord(lon)

    if coord_exists(lat_valid, lon_valid):
        flash_message(f'{lat_valid} & {lon_valid} is already on the list.')
    else:
        url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat_valid},{lon_valid}&key={google_api_key}'
        response = requests.get(url).json()
        if response['status'] == "INVALID_REQUEST":
            flash_message('Invalid Coordinates! Please try again...')
            return redirect(('/cities'))
        if response['status'] == "OK":
            for result in response["results"]:
             for component in result["address_components"]:
                   if "locality" in component["types"] or "administrative_area_level_3" in component["types"]:
                      city = component["long_name"]
                   else: 
                       url2 = f'http://api.openweathermap.org/geo/1.0/reverse?lat={lat_valid}&lon={lon_valid}&limit=1&appid={api_key}'
                       response2 = requests.get(url2).json()
                       if len(response2) != 0:
                            city = response2[0]['name']
                            country_code2 = response2[0]['country']
                       else:
                           city = "UNKNOWN"
                           country_code2 = "UNKNOWN"


            for result in response["results"]:
                for component in result["address_components"]:
                    if "country" in component["types"]:
                       country = component["long_name"]
                       country_code = component["short_name"]
                    else:
                        country = "UNKNOWN"
                        country_code = country_code2


        with get_db().cursor() as cursor:
            query = "INSERT INTO cities (name, lat, lon, country, country_code, added, started, daily, hourly , icon, icon_15, gfs, meteofrance, comment) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (city, lat_valid, lon_valid, country, country_code, current_date, next_day_date, daily, hourly , icon, icon_15, gfs, meteofrance, comment))
        get_db().commit()

        flash_message(f'{lat_valid} & {lon_valid} has been added to the list! The closest city is {city}.')
    return redirect(('/cities'))


@app.route('/toggle_active/<int:city_id>/<int:active>', methods=['GET'])
def toggle_active(city_id, active):
    cur = mysql.connection.cursor()
    if active == 1:
        # active city set the started column
        cur.execute("UPDATE cities SET active = %s, started = %s WHERE city_id = %s", 
                    (active, datetime.now().date() + timedelta(days=1), city_id))
        flash_message('City has been activated successfully!')
    else:
        # deactivating  city only change active column
        cur.execute("UPDATE cities SET active = %s WHERE city_id = %s", (active, city_id))
        flash_message('City has been deactivated successfully!')
        
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('cities'))


@app.route('/cities/delete', methods=['POST'])
def delete():
    city_id = request.form['id']
    cur = mysql.connection.cursor()

    cur.execute("SELECT lat, lon FROM cities WHERE city_id = %s", (city_id,))
    city = cur.fetchone()
    
    if not city:
        flash_message('City not found.')
        return redirect('/cities')
    
    lat, lon = city
    coordinates = f'({lat}, {lon})'
    
    # delete weather data from influxdb
    client = InfluxDBClient(url=influx_url, token=influx_token)

    try:
        delete_api = client.delete_api()
        
        # define start date and stop date
        start = "1970-01-01T00:00:00Z"
        stop = (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z"
        
        # define coordinates for deletion and delete data
        predicate = f'coordinates="{coordinates}"'
    
        delete_api.delete(start, stop, predicate, influx_bucket, influx_org)

    except Exception as e:
        flash_message(f'Error deleting data from InfluxDB: {str(e)}')

    finally:
        client.__del__()

    # delete city data drom sql
    try:
        cur.execute("DELETE FROM cities WHERE city_id = %s", (city_id,))
        mysql.connection.commit()
        flash_message(f'Location data for {city} and ALL related weather data from InfluxDB have been removed.')
        
    except Exception as e:
        flash_message(f'Error deleting city from SQL: {str(e)}')
        
    finally:
        cur.close()

    return redirect('/cities')


@app.route('/cities/remove', methods=['POST'])
def remove():
    id = request.form['id']
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cities WHERE city_id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash_message('City has been removed.')
    return redirect('/cities')


@app.route('/cities/search', methods=['POST'])
def search():
    try:
        keyword = request.form['keyword']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM cities WHERE lon OR lat LIKE %s', ('%' + keyword + '%',))
        cities = cursor.fetchall()
        if not cities:
            flash_message(f'No results found for "{keyword}".', 'warning')
        return render_template('index.html', cities=cities)
    except Exception as e:
        flash_message(f'An error occurred while searching: {e}', 'danger')
        return redirect('/cities')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)