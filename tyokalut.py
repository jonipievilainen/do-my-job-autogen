# tyokalut.py

import os
import psycopg2
import random
import psycopg2
from typing_extensions import Annotated
from autogen_core import CancellationToken
from autogen_core.tools import FunctionTool
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "dbautogen"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

async def get_stock_price(
    ticker: str,
    date: Annotated[str, "Päivämäärä muodossa VVVV/KK/PP"]
) -> float:
    print(f"Haetaan hinta symbolille {ticker} päivältä {date}...")
    return random.uniform(10, 200)

stock_price_autogen_tool = FunctionTool(
    get_stock_price,
    name="get_stock_price",
    description="Keksi minkä tahansa random yrityksen osakkeen hinta tiettynä päivänä."
)

async def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    print(f"RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")
    return 100.5

distance_autogen_tool = FunctionTool(
    calculate_distance,
    name="calculate_distance",
    description="Laske etäisyys kahden GPS-koordinaatin välillä."
)

async def hae_kayttajat() -> str:
    """Hakee kaikki käyttäjät tietokannasta ja palauttaa ne tekstinä."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT kayttajanimi FROM kayttajat;")
        rows = cur.fetchall()
        
        cur.close()
        conn.close()
        
        if not rows:
            return "Tietokannassa ei ole vielä käyttäjiä."
            
        # Muotoillaan lista luettavaksi merkkijonoksi LLM:lle
        tulos = "Löytyi seuraavat käyttäjät:\n"
        for r in rows:
            tulos += f"Nimi: {r['kayttajanimi']}\n"
        return tulos

    except Exception as e:
        return f"Virhe tietokantahaussa: {str(e)}"

hae_kayttajat_tool = FunctionTool(
    hae_kayttajat,
    name="hae_kayttajat",
    description="Hakee listan kaikista dbautogen-tietokannan käyttäjistä."
)