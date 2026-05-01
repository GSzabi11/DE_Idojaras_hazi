-- Létrehozzuk az adattárház adatbázisát
CREATE DATABASE weather_db;

-- Átváltás a létrehozott adatbázisra (psql parancs)
\c weather_db;

-- Városok dimenziótáblája
CREATE TABLE IF NOT EXISTS dim_cities (
    city_id INT PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    population BIGINT
);

-- Dátum/Idő dimenziótábla
CREATE TABLE IF NOT EXISTS dim_date (
    date_id INT PRIMARY KEY,
    full_datetime TIMESTAMP NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    hour INT NOT NULL
);

-- Időjárás ténytábla
CREATE TABLE IF NOT EXISTS fact_weather (
    city_id INT REFERENCES dim_cities(city_id),
    date_id INT REFERENCES dim_date(date_id),
    temperature DECIMAL(5,2),
    humidity INT,
    wind_speed DECIMAL(5,2),
    PRIMARY KEY (city_id, date_id) 
);

-- Időjárás ténytábla országos aggregációval
CREATE TABLE IF NOT EXISTS agg_country_weather (
    country VARCHAR(100) NOT NULL,
    date_id INT REFERENCES dim_date(date_id),
    avg_temperature DECIMAL(5,2),
    avg_wind_speed DECIMAL(5,2),
    PRIMARY KEY (country, date_id)
);