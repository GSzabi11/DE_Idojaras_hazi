import pandas as pd
import json
import os
import glob
from sqlalchemy import create_engine
from sqlalchemy import text

LANDING_ZONE_DIR = "/opt/airflow/data/landing_zone"
CITIES_CSV_PATH  = "/opt/airflow/data/cities.csv"
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "weather_db")

def transform_and_load():
    print("Transzformációs folyamat indítása...")

    # Legfrissebb nyers fájl megkeresése a landing zone-ban
    list_of_files = glob.glob(f'{LANDING_ZONE_DIR}/*.json')
    if not list_of_files:
        raise FileNotFoundError(f"Nem található nyers adat a landing zone-ban: {list_of_files}")
    
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"Feldolgozás alatt: {latest_file}")

    with open(latest_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # JSON lapítása
    records = []
    for entry in raw_data:
        city_id = entry.get('city_id')
        current = entry.get('current', {})
        
        records.append({
            'city_id': city_id,
            'measurement_time': current.get('time'),
            'temperature': current.get('temperature_2m'),
            'humidity': current.get('relative_humidity_2m'),
            'wind_speed': current.get('wind_speed_10m')
        })

    df = pd.DataFrame(records)

    # Adattisztítás és típuskonverzió
    print("Adattisztítás és típuskonverzió...")
    
    df.fillna({
        'temperature': 0.0,
        'humidity': 0,
        'wind_speed': 0.0
    }, inplace=True)

    df['measurement_time'] = pd.to_datetime(df['measurement_time'])
    
    # Dimenziókulcs (date_id) generálása a csillag sémához
    # Ezzel kötjük majd össze a fact_weather táblát a dim_date táblával
    df['date_id'] = df['measurement_time'].dt.strftime('%Y%m%d%H').astype(int)

   # Aggregáció és mentés az adatbázisba
    print("Ország szintű aggregációk kiszámítása...")
    # Beolvassuk a városokat, hogy tudjuk, melyik város melyik országban van
    cities_for_agg = pd.read_csv(CITIES_CSV_PATH)
    
    # Összekapcsoljuk az időjárás adatokat az országokkal
    merged_df = df.merge(cities_for_agg[['city_id', 'country']], on='city_id', how='left')
    
    # Csoportosítunk ország és időpont szerint, majd átlagolunk
    agg_df = merged_df.groupby(['country', 'date_id']).agg(
        avg_temperature=('temperature', 'mean'),
        avg_wind_speed=('wind_speed', 'mean')
    ).reset_index()
    
    # Kerekítés 2 tizedesjegyre
    agg_df['avg_temperature'] = agg_df['avg_temperature'].round(2)
    agg_df['avg_wind_speed'] = agg_df['avg_wind_speed'].round(2)

    # Végső ténytábla oszlopok sorrendbe rakása
    fact_df = df[['city_id', 'date_id', 'temperature', 'humidity', 'wind_speed']]

    # Betöltés a Data Warehouse-ba
    engine_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(engine_url)
    
    try:
        with engine.begin() as conn:
            print("Dimenziótáblák frissítése...")
            
            # Városok betöltése (Csak a hiányzókat töltjük be)
            cities_df = pd.read_csv(CITIES_CSV_PATH)
            
            cities_df['population'] = cities_df['population'].astype(str).str.replace(' ', '')
            cities_df['population'] = pd.to_numeric(cities_df['population'])
            
            existing_city_ids = [row[0] for row in conn.execute(text("SELECT city_id FROM dim_cities")).fetchall()]
            new_cities_df = cities_df[~cities_df['city_id'].isin(existing_city_ids)]
            
            if not new_cities_df.empty:
                new_cities_df.to_sql('dim_cities', conn, if_exists='append', index=False)
                print(f"{len(new_cities_df)} új város hozzáadva a dimenziótáblához.")
            else:
                print("Minden város szerepel már az adatbázisban.")
                
            # Dátum dimenzió feltöltése
            date_df = pd.DataFrame({
                'date_id': df['date_id'].unique(),
                'full_datetime': df['measurement_time'].unique(),
                'year': df['measurement_time'].dt.year.unique(),
                'month': df['measurement_time'].dt.month.unique(),
                'day': df['measurement_time'].dt.day.unique(),
                'hour': df['measurement_time'].dt.hour.unique()
            })
            date_ids = ','.join(map(str, date_df['date_id'].tolist()))
            
            print("Ténytáblák és aggregációk frissítése...")
            conn.execute(text(f"DELETE FROM fact_weather WHERE date_id IN ({date_ids})"))
            conn.execute(text(f"DELETE FROM agg_country_weather WHERE date_id IN ({date_ids})"))
            conn.execute(text(f"DELETE FROM dim_date WHERE date_id IN ({date_ids})"))
            
            # Új adatok beszúrása
            date_df.to_sql('dim_date', conn, if_exists='append', index=False)
            fact_df.to_sql('fact_weather', conn, if_exists='append', index=False)
            
            # Új aggregációs tábla beszúrása
            agg_df.to_sql('agg_country_weather', conn, if_exists='append', index=False)
            
        print("Pipeline sikeresen lefutott! Adatok betöltve az adattárházba.")
        
    except Exception as e:
        print(f"Hiba a betöltés során: {e}")
        raise e

if __name__ == "__main__":
    transform_and_load()