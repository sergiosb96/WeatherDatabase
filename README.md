# Weather Database

## About

An All-in-one solution to collect Weather Forecasts from various sources and for multiple location.
The user adds a point of interest (POI) using the UI and then the app collects weather data each day for the next, at 23:00 (11:00PM) local time.
Weather data are stored in a timeseries database (InfluxDB) and the POI data are stored in an SQL database (MariaDB).
The automation of the data collection is achieved using a modern data orchestration tool called Dagster.
The user can access the data using our API or visualize them using the UI (charts & tables).


## Dependencies
1. [Python](https://www.python.org/)
2. [Flask](https://flask.palletsprojects.com/)
3. [FastAPI](https://fastapi.tiangolo.com/  )
2. [MariaDB](https://mariadb.org/)
4. [InfluxDB](https://www.influxdata.com/)
5. [Dagster](https://dagster.io/)
3. Docker & [Docker-Compose](https://docs.docker.com/compose/install/)

## Required API keys
1. [Google](https://developers.google.com/maps/documentation/geocoding/get-api-key) Geocoding API
2. [OpenWeatherMap](https://openweathermap.org/current) API

## Useful Applications
1. Database Managment Applications (DBMS) such as [HeidiSQL](https://www.heidisql.com/)
2. [Portainer](https://www.portainer.io/) for Docker Container Management

## Installation
### You must have Docker and [Docker-Compose](https://docs.docker.com/compose/install/) installed

1. run ```git clone https://github.com/sergiosb96/WeatherDatabase```
2. run ```cd WeatherDatabase``` (to change directory)
3. edit the .env.example and add you API keys (```sudo nano .env.example```)
4. copy and rename it to .env (```cp ./.env.example ./.env```)
5. run ```docker compose up -d``` inside the directory (might need sudo permissions)

## Ports

- UI: 5000
- API: 9000
- Dagster: 7000
- InfluxDB: 8086
- MySQL: 3306

![Demo](https://github.com/sergiosb96/WeatherDatabase/blob/main/video.mp4)


### This project is part of my Thesis for NTUA. 

## Thesis Abstract
This thesis addresses the issue of collecting meteorological forecasts using open programming interfaces for predicting electrical energy quantities. It analyzes different weather forecasting methods, ultimately utilizing numerical prediction models, categorized into global and regional, from which selections were made for each category. The study then transitioned to predicting electricity production and demand, investigating various methods and identifying variables needed for more accurate forecasting. Furthermore, sources with open programming interfaces were sought for weather data collection. Practically, an application comprising five interconnected sub-applications was developed, with tools to create a user interface for interacting with data collection points, which are stored in a relational database, while weather data is stored in a separate time series database. An open Application Programming Interface (API) was developed for data access, allowing integration with other applications. Data collection and storage are automated through an application that also conducts necessary checks as needed. The final development was done using Docker, allowing easy deployment and use by any user.