import os 
import uvicorn
import pandas as pd
import json
import time
from typing import Optional
from dateutil.parser import parse
from fastapi import FastAPI
from dotenv import  load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

app = FastAPI()

bucket = str(os.getenv('INFLUXDB_BUCKET'))
org = str(os.getenv('INFLUXDB_ORG'))
token = str(os.getenv('INFLUX_TOKEN'))
url = str(os.getenv('INFLUXDB_HOST'))

client = InfluxDBClient(url=url, token=token, org=org)


def convert_api_response(api_response, generation_time):
    if not api_response:
        return {
            "status": "error",
            "error": "No data available"
        }

    dfs = {}
    all_times = []

    for table in api_response:
        records = table.records
        for record in records:
            field = record.values.get("_field")
            time_value = str(record.values.get("_time"))[:16]
            value = record.values.get("_value")

            if field not in dfs:
                dfs[field] = pd.DataFrame()

            df = pd.DataFrame({"value": [value]})
            dfs[field] = pd.concat([dfs[field], df], ignore_index=True)

            if time_value not in all_times:
                all_times.append(time_value)

    json_data = {
        "status": "success",
        "coordinates": str(api_response[0].records[0].values.get("coordinates")),
        "data_source": str(api_response[0].records[0].values.get("_measurement")),
        "start": str(api_response[0].records[0].values.get("_start"))[:16],
        "stop": str(api_response[0].records[0].values.get("_stop"))[:16],
        "time": all_times,
        "results": {},
        "query_time_ms": generation_time,
    }

    for field, df in dfs.items():
        json_data["results"][field] = df.to_dict(orient="list")

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

    query = f'from(bucket: "{bucket}") |> range(start: {int(start.timestamp())}, stop: {int(end.timestamp())}) |> filter(fn: (r) => r._measurement == "{source}" and r.coordinates == "{coordinates}")'

    if fields:
        field_list = fields.split(',')
        filters = ' or '.join([f'r._field == "{field}"' for field in field_list])
        query += f' |> filter(fn: (r) => {filters})'

    start_time = time.time()
    
    query_api = client.query_api()
    result = query_api.query(org=org, query=query)
    
    generation_time = int((time.time() - start_time) * 1000)

    json_result = convert_api_response(result, generation_time)

    return json_result

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)