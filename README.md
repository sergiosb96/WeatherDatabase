# Weather Database

### README will be updated...

#### A simple Python Web UI to manage an SQL Database for Cities and Coordinates.
#### The database is used to collect weather forecasts from each coordinate.

### This project is part of my Thesis for NTUA. 

## Dependencies
1. [Python](https://www.python.org/)
2. [MariaDB](https://mariadb.org/)
4. InfluxDB
3. Docker & [Docker-Compose](https://docs.docker.com/compose/install/)

## Required API keys
1. [Google](https://developers.google.com/maps/documentation/geocoding/get-api-key) Geocoding API
2. [OpenWeatherMap](https://openweathermap.org/current) API

## Useful Applications
Database Managment Applications (DBMS) such as [HeidiSQL](https://www.heidisql.com/)

## Installation
### You must have Docker and [Docker-Compose](https://docs.docker.com/compose/install/) installed

1. run ```git clone https://github.com/sergiosb96/CitiesManager```
2. run ```cd CitiesManager``` (to change directory)
3. edit the .env.example and add you API keys (```sudo nano .env.example```)
4. copy and rename it to .env (```cp ./.env.example ./.env```)
5. run ```docker compose up -d``` inside the directory (might need sudo permissions)
6. visit http://localhost:5000

### weather script must be ran at 11:00 UTC time.