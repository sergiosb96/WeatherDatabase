from flask import Flask, render_template, request, redirect, g, send_file, flash as flash_message
from flask_mysqldb import MySQL
import pandas as pd
from datetime import datetime
import requests
import os
import re
import csv
import json
from io import StringIO
from dotenv import  load_dotenv

app = Flask(__name__)

load_dotenv()

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

def fetch_cities_from_database():
    cur = get_db().cursor()
    cur.execute("SELECT name, lat, lon FROM cities")
    cities = cur.fetchall()
    cur.close()
    return cities


def fetch_coordinates_from_database(selected_city):
    cur = get_db().cursor()
    cur.execute("SELECT lon, lat FROM cities WHERE name = %s", (selected_city,))
    coordinates = cur.fetchone()
    cur.close()
    return coordinates

def generate_query_api_url(city_coordinates, selected_sources, start_date, end_date):
    city_lon, city_lat = city_coordinates
    api_base_url = str(os.getenv('API_BASE_URL'))
    api_url = f'{api_base_url}api/influx/query?source={",".join(selected_sources)}&coordinates=({city_lat}, {city_lon})&start_date={start_date}&end_date={end_date}'

    return api_url

def generate_data_api_url(city_coordinates, selected_sources, start_date, end_date):
    city_lon, city_lat = city_coordinates
    api_base_url = str(os.getenv('API_BASE_URL'))
    api_url = f'{api_base_url}api/v1/query?source={",".join(selected_sources)}&coordinates=({city_lat}, {city_lon})&start_date={start_date}&end_date={end_date}'

    return api_url



@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/api/docs', methods=['GET', 'POST'])
def docs():
    
    api_base_url = str(os.getenv('API_BASE_URL'))

    return render_template('docs.html', api_base_url=api_base_url)



@app.route('/api', methods=['GET', 'POST'])
def data():
    cities = fetch_cities_from_database()

    if request.method == 'POST':
        # get data from the form
        selected_city = request.form.get('city')
        selected_sources = request.form.getlist('sources')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # fetch the coordinates for the selected city from the database
        city_coordinates = fetch_coordinates_from_database(selected_city)

        # combine the information into an API URL
        query_url = generate_query_api_url(city_coordinates, selected_sources, start_date, end_date)
        query_api_response = requests.get(query_url).json()

        api_url = generate_data_api_url(city_coordinates, selected_sources, start_date, end_date)
        data_api_response = requests.get(api_url).json()

        dfs = {}

        if not query_api_response:
            return render_template('no_data.html', cities=cities, api_url=api_url, city_coordinates=city_coordinates, \
                                    start_date=start_date, end_date=end_date, selected_city=selected_city, selected_sources=selected_sources)

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


        return render_template('api.html', cities=cities, api_url=api_url, data_api_response=data_api_response, dfs=dfs, \
                            city_coordinates=city_coordinates, start_date=start_date, end_date=end_date, selected_city=selected_city, \
                            selected_sources=selected_sources, measurement=query_api_response[0]['records'][0]['values']['_measurement'])

    return render_template('api.html', cities=cities)



@app.route('/export_csv', methods=['POST'])
def export_csv():
    # get data from the form
    data = request.form.getlist('dfs[]')
    fields = request.form.getlist('fields[]')
    city = request.form.get('city')
    coordinates = request.form.get('coordinates')
    measurement = request.form.get('measurement')

    merged_df = pd.DataFrame()

    for csv_data, field_name in zip(data, fields):

        df = pd.read_csv(StringIO(csv_data))
        df.insert(0, '_field', field_name)

        merged_df = pd.concat([merged_df, df], ignore_index=True)

    # create filename with the city and the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"data_export__for_{city}_at_{timestamp}.csv"

    # add new rows with info at the beginning
    new_rows = [
        ['City:', city, ''],
        ['Coordinates:', coordinates, ''],
        ['Data_Source:', measurement, '']
    ]

    # export the merged DataFrame to a CSV file
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(new_rows)
        merged_df.to_csv(file, index=False)

    # send the file
    return send_file(filename, as_attachment=True)


@app.route('/export_json', methods=['POST'])
def export_json():
    # get data from the form
    data = request.form.getlist('dfs[]')
    fields = request.form.getlist('fields[]')
    city = request.form.get('city')
    coordinates = request.form.get('coordinates')
    measurement = request.form.get('measurement')

    merged_df = pd.DataFrame()

    for csv_data, field_name in zip(data, fields):

        df = pd.read_csv(StringIO(csv_data))
        df.insert(0, '_field', field_name)

        merged_df = pd.concat([merged_df, df], ignore_index=True)

    # create filename with the city and the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename_json = f"data_export__for_{city}_at_{timestamp}.json"

    # add new rows with info at the beginning
    new_rows = [
        ['City:', city],
        ['Coordinates:', coordinates],
        ['Data_Source:', measurement]
    ]

    # export the merged DataFrame to a JSON file
    merged_json = merged_df.to_json(orient='records')

    with open(filename_json, 'w') as file:
        file.write(json.dumps(new_rows + json.loads(merged_json), indent=4))

    # send the file
    return send_file(filename_json, as_attachment=True)



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
            query = "INSERT INTO cities (name, lat, lon, country, country_code, daily, hourly, icon, icon_15, gfs, meteofrance) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (city, lat_valid, lon_valid, country, country_code, daily, hourly, icon, icon_15, gfs, meteofrance))
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
            query = "INSERT INTO cities (name, lat, lon, country, country_code, daily, hourly, icon, icon_15, gfs, meteofrance) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (city, lat_valid, lon_valid, country, country_code, daily, hourly, icon, icon_15, gfs, meteofrance))
        get_db().commit()

        flash_message(f'{lat_valid} & {lon_valid} has been added to the list! The closest city is {city}.')
    return redirect(('/cities'))

@app.route('/cities/delete', methods=['POST'])
def delete():
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
    app.run(host='0.0.0.0', port=5000)