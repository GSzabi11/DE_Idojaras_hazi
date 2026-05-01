# Globális Városok Élhetőségi Pipeline
**Data Engineering Opcionális Házi Feladat**

Ez a projekt egy teljes, end-to-end data engineering pipeline, amely kiválasztott világvárosok időjárási adatait és statikus metaadatait integrálja. A rendszer napi szinten gyűjt, tisztít és transzformál adatokat, hogy azokat egy adattárházban elemezhetővé és egy dashboardon vizualizálhatóvá tegye.

---

## 1. Architektúra és Indoklás

A pipeline egy modern, lokális, konténerizált adatplatformot valósít meg az alábbi technológiák segítségével:

* **Adatforrások (Extract):** 
  * **REST API:** Open-Meteo API (szemistrukturált JSON adatok az aktuális időjárásról).
  * **Lokális fájl:** `cities.csv` (strukturált adatok a városokról: koordináták, népesség).
* **Adattárolás (Storage):** 
  * **Landing Zone:** Lokális fájlrendszer (`data/landing_zone`), ahová az API-ból kinyert nyers JSON fájlok érkeznek (reprodukálhatóság és debugolás céljából).
  * **Data Warehouse:** PostgreSQL relációs adatbázis, amely egy optimalizált csillag sémát tárol.
* **Transzformáció (Transform):** Python (Pandas) alapú feldolgozás. A szemistrukturált adatok lapítása (flattening), null-értékek kezelése, típuskonverziók és aggregációk elvégzése történik a betöltés előtt.
* **Orkesztráció (Orchestration):** Apache Airflow. Kezeli a feladatok (taskok) függőségét, ütemezését (óránkénti futás) és biztosítja a folyamat **idempotenciáját** (újrafuttatás esetén nincs adatduplikáció).
* **Vizualizáció (Serving):** Metabase, amellyel az adatbázisra csatlakozva interaktív dashboardok készíthetők.
* **Infrastruktúra:** Docker Compose. Az egész rendszer (Postgres, Airflow, Metabase) egyetlen paranccsal, reprodukálhatóan elindítható.

---

## 2. Adatmodell (Csillag séma)

Az adattárház tervezése során a klasszikus Kimball-féle csillag sémát (Star Schema) alkalmaztuk az analitikai lekérdezések (OLAP) gyorsítása érdekében.
![Airflow Sikeres Futás](Images/er_diagram.png)

---

## 3. Futtatás és Használat

Futtatás előtt a .env.example fájl nevét írd át .env-re, vagy hozz létre egy sajátot a szükséges változókkal.

A projekt teljes infrastruktúrája konténerizálva van, így a futtatása mindössze pár lépésből áll:

1. A terminálban a projekt gyökérmappájába állva add ki az alábbi parancsot a Docker konténerek elindításához:
   ```bash
   docker-compose up -d
   ```
2. Ezt követően nyisd meg a `http://localhost:8080` címet a böngészőben. Itt éred el az **Airflow** grafikus felületét. A `.env` fájlban megadott felhasználónévvel és jelszóval tudsz bejelentkezni, majd elindítani a DAG-ot.

![Airflow Sikeres Futás](Images/airflow.png)

3. Az analitikai adatbázisra kötött **Metabase BI Dashboardot** a `http://localhost:3000` címen éred el. Az első indításkor egy admin fiók létrehozása szükséges az adatok vizualizációjához.

---

## 4. Analitikai lekérdezések és Dashboard

Az alábbi SQL lekérdezések az adattárház (PostgreSQL) csillag sémájára épülnek, összekötve a tény- és dimenziótáblákat. Ezek szolgáltatják az adatokat a Metabase dashboard vizualizációihoz.

### Aktuális globális hőtérkép
Megmutatja a legfrissebb letöltött időjárási adatokat városonként.
```sql
SELECT 
    c.city_name AS "Város", 
    c.country AS "Ország", 
    w.temperature AS "Hőmérséklet (°C)", 
    w.wind_speed AS "Szélsebesség (km/h)",
    d.full_datetime AS "Mérés ideje"
FROM fact_weather w
JOIN dim_cities c ON w.city_id = c.city_id
JOIN dim_date d ON w.date_id = d.date_id
WHERE d.date_id = (SELECT MAX(date_id) FROM dim_date)
ORDER BY w.temperature DESC;
```

### Városok térképes elhelyezkedése
A Metabase térképes (Pin map) vizualizációjához szükséges földrajzi koordináták lekérdezése.
```sql
SELECT 
    dim_cities.city_name AS "Város", 
    dim_cities.country AS "Ország",
    dim_cities.latitude AS "Latitude",
    dim_cities.longitude AS "Longitude"
FROM dim_cities;
```

### Országok átlag hőmérséklete és szélsebessége
A Metabase térképes (Pin map) vizualizációjához szükséges földrajzi koordináták lekérdezése.
```sql
SELECT 
    country AS "Ország", 
    avg_temperature AS "Átlaghőmérséklet (°C)", 
    avg_wind_speed AS "Átlagos Szélsebesség (km/h)",
    d.full_datetime AS "Mérés ideje"
FROM agg_country_weather a
JOIN dim_date d ON a.date_id = d.date_id
WHERE a.date_id = (SELECT MAX(date_id) FROM agg_country_weather)
ORDER BY avg_temperature DESC;
```

### Metabase Dashboard
A fenti lekérdezésekből összeállított végső, interaktív BI Dashboard:

![Metabase Dashboard](Images/dashboard1.png)
![Metabase Dashboard](Images/dashboard2.png)