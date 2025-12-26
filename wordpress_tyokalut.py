# wordpress_tyokalut.py
# WordPress-specific Docker helper tools (adds an optional 'wpcli' service for WP-CLI)

import os
import subprocess
import json
import shutil
from typing_extensions import Annotated
from autogen_core.tools import FunctionTool
import re

ENV_DIR = os.getenv("DOCKER_ENV_DIR", "./environments")


def _slugify(name: str) -> str:
    """Convert a display name to a safe filesystem/service name."""
    s = name.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_-]", "", s)
    return s[:128]

os.makedirs(ENV_DIR, exist_ok=True)


def _run(cmd, cwd=None):
    """Suorita shell-komento ja palauta stdout tai nosta poikkeus."""
    print(f"Suoritetaan: {' '.join(cmd)} (cwd={cwd})")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Komentovirhe: {res.returncode}: {res.stderr.strip()}")
    return res.stdout.strip()


async def wp_luo_ymparisto(
    nimi: str,
    tyyppi: Annotated[str, "Esim. 'wordpress'"],
    portti: Annotated[int, "Julkaistava host-portti (esim. 80)"],
    lisatiedot: Annotated[str, "Tarkemmat asetukset JSON-muodossa (esim. plugins lista)"] = "{}"
) -> str:
    """Luo Docker-ympäristön hakemistoon `environments/<nimi>` ja käynnistää sen.

    - `tyyppi` tukee tällä hetkellä vähintään 'wordpress'.
    - `lisatiedot` on JSON-merkkijono, jossa voi olla esim. {'plugins': ['woocommerce']}
    """
    try:
        data = json.loads(lisatiedot or "{}")
    except Exception as e:
        return f"Virhe lisätietojen jäsentämisessä: {str(e)}"

    slug = _slugify(nimi)
    env_path = os.path.join(ENV_DIR, slug)
    if os.path.exists(env_path):
        return f"Ympäristö '{nimi}' on jo olemassa (slug: {slug})." 

    os.makedirs(env_path, exist_ok=True)

    if tyyppi.lower() == "wordpress":
        # Luo yksinkertainen docker-compose.yml (WordPress + optional wpcli service)
        compose = f"""
services:
  db:
    image: mysql:5.7
    restart: always
    environment:
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wordpress
      MYSQL_PASSWORD: wordpress
      MYSQL_RANDOM_ROOT_PASSWORD: '1'
    volumes:
      - db_data:/var/lib/mysql

  wordpress:
    image: wordpress:latest
    depends_on:
      - db
    ports:
      - \"{portti}:80\"
    environment:
      WORDPRESS_DB_HOST: db:3306
      WORDPRESS_DB_USER: wordpress
      WORDPRESS_DB_PASSWORD: wordpress
      WORDPRESS_DB_NAME: wordpress
    volumes:
      - wordpress_data:/var/www/html

  wpcli:
    image: wordpress:cli
    depends_on:
      - wordpress
    volumes:
      - wordpress_data:/var/www/html
    command: tail -f /dev/null
    restart: unless-stopped

volumes:
  db_data:
  wordpress_data:
"""
    else:
        return f"Tyyppiä '{tyyppi}' ei tueta vielä. Tällä hetkellä tuettuja: wordpress."

    compose_path = os.path.join(env_path, "docker-compose.yml")
    with open(compose_path, "w") as f:
        f.write(compose)

    # Save metadata (display name, type, requested port)
    meta = {"display_name": nimi, "type": tyyppi, "port": portti}
    try:
        with open(os.path.join(env_path, "meta.json"), "w") as mf:
            json.dump(meta, mf)
    except Exception as e:
        print(f"Varoitus: meta.json tallennus epäonnistui: {e}")

    try:
        _run(["docker", "compose", "-f", "docker-compose.yml", "up", "-d"], cwd=env_path)
    except Exception as e:
        return f"Docker-compose up epäonnistui: {str(e)}"

    # Asenna mahdolliset WordPress-pluginit, jos on määritelty
    plugins = data.get("plugins", []) if isinstance(data, dict) else []
    if plugins:
        try:
            # Yritetään käyttää wp-cli, on mahdollista että sitä ei ole valmiiksi asennettuna konttiin
            for plugin in plugins:
                installed = False
                try:
                    # Try using a dedicated wpcli service
                    _run(["docker", "compose", "-f", "docker-compose.yml", "exec", "-T", "wpcli", "wp", "plugin", "install", plugin, "--activate", "--allow-root"], cwd=env_path)
                    installed = True
                except Exception:
                    try:
                        # Fallback to running wp inside the wordpress container
                        _run(["docker", "compose", "-f", "docker-compose.yml", "exec", "-T", "wordpress", "wp", "plugin", "install", plugin, "--activate", "--allow-root"], cwd=env_path)
                        installed = True
                    except Exception:
                        print(f"WP-CLI ei ollut saatavilla tai plugin asennus epäonnistui: {plugin}")
            return f"Ympäristö '{nimi}' luotu ja käynnistetty. Plugin-asennukset yritetty (voi vaatia manuaalisen asennuksen konttiin)."
        except Exception as e:
            return f"Ympäristö luotu, mutta plugin-asennuksessa virhe: {str(e)}"

    return f"Ympäristö '{nimi}' luotu ja käynnistetty porttiin {portti}."


async def wp_poista_ymparisto(nimi: str) -> str:
    """Poistaa ympäristön: pysäyttää ja poistaa kontit ja poistaa hakemiston."""
    env_path = os.path.join(ENV_DIR, nimi)
    if not os.path.exists(env_path):
        return f"Ympäristöä '{nimi}' ei löydy." 

    compose_path = os.path.join(env_path, "docker-compose.yml")
    try:
        _run(["docker", "compose", "-f", "docker-compose.yml", "down", "-v"], cwd=env_path)
    except Exception as e:
        return f"Docker-compose down epäonnistui: {str(e)}"

    try:
        shutil.rmtree(env_path)
    except Exception as e:
        return f"Kontit pysäytetty, mutta hakemiston poisto epäonnistui: {str(e)}"

    return f"Ympäristö '{nimi}' poistettu." 


async def wp_sammuta_ymparisto(nimi: str) -> str:
    """Sammuttaa ympäristön: pysäyttää kontit mutta ei poista hakemistoa."""
    env_path = os.path.join(ENV_DIR, nimi)
    if not os.path.exists(env_path):
        return f"Ympäristöä '{nimi}' ei löydy." 

    compose_path = os.path.join(env_path, "docker-compose.yml")
    if not os.path.exists(compose_path):
        return f"Ympäristöä '{nimi}' ei löydy tai siinä ei ole docker-compose.yml:ää."

    try:
        _run(["docker", "compose", "-f", "docker-compose.yml", "stop"], cwd=env_path)
    except Exception as e:
        return f"Ympäristön sammuttaminen epäonnistui: {str(e)}"

    return f"Ympäristö '{nimi}' sammutettu." 


async def wp_kaynnista_ymparisto(nimi: str) -> str:
    """Käynnistää ympäristön: käynnistää kontit uudelleen (up -d)."""
    env_path = os.path.join(ENV_DIR, nimi)
    if not os.path.exists(env_path):
        return f"Ympäristöä '{nimi}' ei löydy." 

    compose_path = os.path.join(env_path, "docker-compose.yml")
    if not os.path.exists(compose_path):
        return f"Ympäristöä '{nimi}' ei löydy tai siinä ei ole docker-compose.yml:ää."

    try:
        _run(["docker", "compose", "-f", "docker-compose.yml", "up", "-d"], cwd=env_path)
    except Exception as e:
        return f"Ympäristön käynnistäminen epäonnistui: {str(e)}"

    return f"Ympäristö '{nimi}' käynnistetty." 


async def wp_listaa_kaikki_ymparistot() -> str:
    """Listaa kaikki ympäristöt, niiden metatiedot ja tila (sis. ei-docker-compose hakemistot)."""
    envs = sorted([d for d in os.listdir(ENV_DIR) if os.path.isdir(os.path.join(ENV_DIR, d))])
    if not envs:
        return "Ei löydetty ympäristöjä."

    tulos = "Kaikki ympäristöt:\n"
    for e in envs:
        display = e
        port = None
        meta_path = os.path.join(ENV_DIR, e, "meta.json")
        if os.path.exists(meta_path):
            try:
                m = json.load(open(meta_path))
                display = m.get("display_name", e)
                port = m.get("port")
            except Exception:
                pass

        compose_path = os.path.join(ENV_DIR, e, "docker-compose.yml")
        has_compose = os.path.exists(compose_path)
        if has_compose:
            try:
                out = _run(["docker", "compose", "-f", "docker-compose.yml", "ps", "--services", "--filter", "status=running"], cwd=os.path.join(ENV_DIR, e))
                tila = "käynnissä" if out.strip() else "pysähdyksissä"
            except Exception:
                tila = "tila: tarkistamaton"
        else:
            tila = "ei docker-compose.yml"

        tulos += f"- {display} (slug: {e}) - port: {port if port else 'unknown'}, compose: {'yes' if has_compose else 'no'}, tila: {tila}\n"

    return tulos


async def wp_listaa_ymparistot() -> str:
    """Listaa ympäristöt hakemistosta ja niiden tila (käynnissä/pysähdyksissä)."""
    envs = [d for d in os.listdir(ENV_DIR) if os.path.isdir(os.path.join(ENV_DIR, d))]
    if not envs:
        return "Ei löydetty ympäristöjä."

    tulos = "Löydetyt ympäristöt ja tila:\n"
    for e in envs:
        compose_path = os.path.join(ENV_DIR, e, "docker-compose.yml")
        display = e
        meta_path = os.path.join(ENV_DIR, e, "meta.json")
        if os.path.exists(meta_path):
            try:
                m = json.load(open(meta_path))
                display = m.get("display_name", e)
            except Exception:
                pass

        if os.path.exists(compose_path):
            try:
                out = _run(["docker", "compose", "-f", "docker-compose.yml", "ps", "--services", "--filter", "status=running"], cwd=os.path.join(ENV_DIR, e))
                tila = "käynnissä" if out.strip() else "pysähdyksissä"
            except Exception:
                tila = "tila: tarkistamaton"
        else:
            tila = "ei docker-compose.yml"
        tulos += f"- {display} (slug: {e}): {tila}\n"

    return tulos


async def wp_muuta_ymparisto(nimi: str, asetukset: Annotated[str, "JSON asetukset, esim. {'portti': 8081} "]) -> str:
    """Muokkaa olemassaolevaa ympäristöä -- tällä hetkellä tukee portin muokkausta ja uusien pluginien lisäämistä."""
    slug = _slugify(nimi)
    env_path = os.path.join(ENV_DIR, slug)
    compose_path = os.path.join(env_path, "docker-compose.yml")
    if not os.path.exists(compose_path):
        return f"Ympäristöä '{nimi}' (slug: {slug}) ei löydy tai siinä ei ole docker-compose.yml:ää." 

    try:
        aset = json.loads(asetukset or "{}")
    except Exception as e:
        return f"Virhe asetusten jäsentämisessä: {str(e)}"

    # Yksinkertainen muutos: portin päivitys
    if "portti" in aset:
        with open(compose_path, "r+") as f:
            s = f.read()
            # Etsi ensimmäinen port-mappi ja korvaa portti
            import re
            new = re.sub(r"ports:\n\s*- \"\d+:80\"", f"ports:\n      - \"{aset['portti']}:80\"", s, count=1)
            f.seek(0)
            f.write(new)
            f.truncate()
        try:
            _run(["docker", "compose", "-f", "docker-compose.yml", "up", "-d"], cwd=env_path)
            return f"Ympäristön '{nimi}' portti päivitetty ja ympäristö uudelleenkäynnistetty." 
        except Exception as e:
            return f"Portin päivitys epäonnistui: {str(e)}"

    # Pluginien lisääminen
    if "plugins" in aset and isinstance(aset["plugins"], list):
        try:
            for plugin in aset["plugins"]:
                try:
                    _run(["docker", "compose", "-f", "docker-compose.yml", "exec", "-T", "wpcli", "wp", "plugin", "install", plugin, "--activate", "--allow-root"], cwd=env_path)
                except Exception:
                    try:
                        _run(["docker", "compose", "-f", "docker-compose.yml", "exec", "-T", "wordpress", "wp", "plugin", "install", plugin, "--activate", "--allow-root"], cwd=env_path)
                    except Exception:
                        print(f"WP-CLI ei saatavilla tai plugin asennus epäonnistui: {plugin}")
            return f"Pluginien asennus yritetty ympäristöön '{nimi}', tarkista tarvittaessa manuaalisesti." 
        except Exception as e:
            return f"Pluginien asennus epäonnistui: {str(e)}"

    return "Ei tehtyjä muutoksia. Tuettuja asetuksia: 'portti', 'plugins'."


# FunctionToolit
wp_luo_ymparisto_tool = FunctionTool(
    wp_luo_ymparisto,
    name="wp_luo_ymparisto",
    description="Luo WordPress Docker-ympäristön (WordPress + db). Lisää valinnainen 'wpcli' palvelu WP-CLI:lle. Parametrit: nimi, tyyppi, portti, lisatiedot(JSON)."
)

wp_poista_ymparisto_tool = FunctionTool(
    wp_poista_ymparisto,
    name="wp_poista_ymparisto",
    description="Poistaa WordPress-ympäristön ja siihen liittyvät volyymit. Parametri: nimi."
)

wp_listaa_ymparistot_tool = FunctionTool(
    wp_listaa_ymparistot,
    name="wp_listaa_ymparistot",
    description="Listaa paikalliset WordPress-ympäristöt ja niiden tila."
)

wp_muuta_ymparisto_tool = FunctionTool(
    wp_muuta_ymparisto,
    name="wp_muuta_ymparisto",
    description="Muokkaa WordPress-ympäristöä (esim. portti, plugin-lista). Parametrit: nimi, asetukset(JSON)."
)

wp_sammuta_ymparisto_tool = FunctionTool(
    wp_sammuta_ymparisto,
    name="wp_sammuta_ymparisto",
    description="Sammuttaa WordPress-ympäristön (pysäyttää kontit). Parametri: nimi."
)

wp_kaynnista_ymparisto_tool = FunctionTool(
    wp_kaynnista_ymparisto,
    name="wp_kaynnista_ymparisto",
    description="Käynnistää WordPress-ympäristön (up -d). Parametri: nimi."
)

wp_listaa_kaikki_ymparistot_tool = FunctionTool(
    wp_listaa_kaikki_ymparistot,
    name="wp_listaa_kaikki_ymparistot",
    description="Listaa kaikki ympäristöt ja niiden metatiedot (display name, portti, compose-tila)."
)
