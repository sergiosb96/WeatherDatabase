import os 
import uvicorn
import pandas as pd
import time
from typing import Optional
from dateutil.parser import parse
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import asyncio
import aiomysql
from dotenv import  load_dotenv, find_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

app = FastAPI()

bucket = str(os.getenv('INFLUXDB_BUCKET'))
org = str(os.getenv('INFLUXDB_ORG'))
token = str(os.getenv('INFLUX_TOKEN'))
url = str(os.getenv('INFLUXDB_HOST'))

client = InfluxDBClient(url=url, token=token, org=org)

DB_CONFIG = {
    "host": str(os.getenv('MYSQL_HOST')),
    "user": str(os.getenv('MYSQL_USER')),
    "password": str(os.getenv('MYSQL_PASSWORD')),
    "db": str(os.getenv('MYSQL_DB'))
}

async def get_db():
    conn = await aiomysql.connect(**DB_CONFIG)
    return conn

async def fetch_query_urls_from_database(lat, lon):
    conn = await get_db()
    cur = await conn.cursor()
    
    query_city_id = "SELECT city_id, added, started FROM cities WHERE lat=%s AND lon=%s"
    await cur.execute(query_city_id, (lat, lon))
    result = await cur.fetchone()
    
    if result is None:
        await cur.close()
        conn.close()
        return {}
    
    city_id, added, started = result

    query_url = """
    SELECT daily, hourly, icon, icon_15, gfs, meteofrance 
    FROM query_urls 
    WHERE city_id=%s
    """
    await cur.execute(query_url, (city_id,))
    row = await cur.fetchone()
    
    await cur.close()
    conn.close()
    
    if row is None:
        return {
            "added": added,
            "started": started
        }
    
    return {
        "daily_forecast": row[0],
        "hourly_forecast": row[1],
        "icon_forecast": row[2],
        "icon_15_forecast": row[3],
        "gfs_forecast": row[4],
        "meteofrance_forecast": row[5],
        "added": added,
        "started": started
    }


async def convert_api_response(api_response, generation_time):
    if not api_response:
        raise HTTPException(status_code=404, detail="No data available")

    dfs = {}
    all_times = set()

    try:
        for table in api_response:
            for record in table.records:
                field = record.values.get("_field")
                time_value = str(record.values.get("_time"))[:16]
                value = record.values.get("_value")

                dfs.setdefault(field, []).append(value)
                all_times.add(time_value)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        coordinates = str(api_response[0].records[0].values.get("coordinates"))
        data_source = str(api_response[0].records[0].values.get("_measurement"))
        start = str(api_response[0].records[0].values.get("_start"))[:16]
        stop = str(api_response[0].records[0].values.get("_stop"))[:16]
    except IndexError:
        raise HTTPException(status_code=404, detail="No data available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    clean_coordinates = coordinates.strip("()").replace(" ", "")
    lat, lon = map(float, clean_coordinates.split(','))
    city_details_and_urls = await fetch_query_urls_from_database(lat, lon)
    url_to_use = city_details_and_urls.get(data_source, None)

    sorted_times = sorted(list(all_times))
    
    json_data = {
        "status": "success",
        "coordinates": coordinates,
        "data_source": data_source,
        "Open-Meteo url": url_to_use,
        "start": start,
        "stop": stop,
        "added": city_details_and_urls.get("added"),
        "started": city_details_and_urls.get("started"),
        "query_time_ms": generation_time,
        "time": sorted_times,
        "results": {},
    }

    try:
        for field, values in dfs.items():
            json_data["results"][field] = {"value": values}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return json_data


@app.get("/api/influx/query")
async def query_influx(source: str, coordinates: str, start_date: str, end_date: str, fields: Optional[str] = None):
    start = parse(start_date)
    end = parse(end_date)

    query = f'from(bucket: "{bucket}") |> range(start: {int(start.timestamp())}, stop: {int(end.timestamp())}) |> filter(fn: (r) => r._measurement == "{source}" and r.coordinates == "{coordinates}")'

    if fields:
        field_list = fields.split(',')
        filters = ' or '.join([f'r._field == "{field}"' for field in field_list])
        query += f' |> filter(fn: (r) => {filters})'

    query_api = client.query_api()
    result = query_api.query(org=org, query=query)
    return result


@app.get("/api/v1/query")
async def query_data(source: str, coordinates: str, start_date: str, end_date: str, fields: Optional[str] = None):
    start = parse(start_date)
    end = parse(end_date)

    # Check if start date is after the end date
    if start > end:
        raise HTTPException(status_code=400, detail="End date is after start date")

    query = f'from(bucket: "{bucket}") |> range(start: {int(start.timestamp())}, stop: {int(end.timestamp())}) |> filter(fn: (r) => r._measurement == "{source}" and r.coordinates == "{coordinates}")'
    
    if fields:
        field_list = fields.split(',')
        filters = ' or '.join([f'r._field == "{field}"' for field in field_list])
        query += f' |> filter(fn: (r) => {filters})'
    
    start_time = time.time()
    
    query_api = client.query_api()

    try:
        result = await asyncio.to_thread(query_api.query, org=org, query=query)
    except Exception as e:
        return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    
    generation_time = int((time.time() - start_time) * 1000)
    
    try:
        json_result = await convert_api_response(result, generation_time)
    except HTTPException as he:
        return JSONResponse(content={"status": "error", "error": he.detail}, status_code=he.status_code)
    
    return json_result

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)