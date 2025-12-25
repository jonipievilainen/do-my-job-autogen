import os
import psycopg2

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "dbautogen"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

def test_table_access():
    conn = None
    try:
        print(f"Yritetään hakea tietoja taulusta 'kayttajat'...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Testataan haku
        cur.execute("SELECT COUNT(*) FROM kayttajat;")
        maara = cur.fetchone()[0]
        
        print(f"✅ Onnistui! Taulussa on tällä hetkellä {maara} käyttäjää.")
        
        # Tulostetaan vielä nimet varmuuden vuoksi
        cur.execute("SELECT kayttajanimi FROM kayttajat LIMIT 5;")
        nimet = cur.fetchall()
        for nimi in nimet:
            print(f" - Löytyi nimi: {nimi[0]}")
            
        cur.close()
    except psycopg2.errors.UndefinedTable:
        print("❌ VIRHE: Taulua 'kayttajat' ei löydy! Oletko luonut sen?")
    except Exception as e:
        print(f"❌ VIRHE: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_table_access()

