import pandas as pd
import requests
import json
import os
from datetime import datetime

LANDING_ZONE_DIR = "/opt/airflow/data/landing_zone"
CITIES_CSV_PATH  = "/opt/airflow/data/cities.csv"

if not os.path.exists(LANDING_ZONE_DIR):
    os.makedirs(LANDING_ZONE_DIR)

def fetch_weather_data():
    print("Időjárás adatok letöltésének indítása...")
    
    # A CSV fájl beolvasása
    try:
        cities_df = pd.read_csv(CITIES_CSV_PATH)
        print(f"{len(cities_df)} város sikeresen beolvasva a CSV-ből.")
    except FileNotFoundError:
        raise FileNotFoundError(f"Nem található nyers adat a landing zone-ban: {CITIES_CSV_PATH}")
        return

    weather_results = []

    # Végigmegyünk a városokon és meghívjuk az API-t
    for index, row in cities_df.iterrows():
        city = row['city_name']
        lat = row['latitude']
        lon = row['longitude']
        
        # Open-Meteo API URL összerakása
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        
        print(f"Lekérdezés: {city}...")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            # Hozzárakjuk a city_id-t, hogy később össze tudjuk kötni a relációs adatbázisban
            data['city_id'] = row['city_id'] 
            weather_results.append(data)
        else:
            print(f"Hiba {city} lekérdezésekor. Status code: {response.status_code}")

    # A nyers adatok elmentése a Landing Zone-ba
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{LANDING_ZONE_DIR}/raw_weather_{timestamp}.json"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(weather_results, f, ensure_ascii=False, indent=4)
        
    print(f"Kész! A nyers adatok elmentve: {output_filename}")

if __name__ == "__main__":
    fetch_weather_data()