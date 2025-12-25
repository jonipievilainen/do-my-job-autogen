#!/bin/bash

# 1. Asetetaan OpenAI API-avain
# MUISTA: Älä jaa tätä tiedostoa (esim. GitHubiin), jos avain on tässä näkyvissä!
export OPENAI_API_KEY="123"

# 2. Tietokanta-asetukset
export DB_NAME="AAA"
export DB_USER="BBB"
export DB_PASS="CCC"
export DB_HOST="DDD"
export DB_PORT="EEE"

# 3. Tarkistetaan löytyykö virtuaaliympäristö
if [ -d ".venv" ]; then
    echo "✅ Aktivoidaan olemassa oleva virtuaaliympäristö..."
else
    echo "🔍 .venv-kansiota ei löytynyt. Luodaan uusi virtuaaliympäristö..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "❌ VIRHE: Virtuaaliympäristön luonti epäonnistui. Tarkista onko python3-venv asennettu."
        exit 1
    fi
    echo "✅ Virtuaaliympäristö luotu."
fi

# Aktivointi
source .venv/bin/activate

# 4. Tarkistetaan ja asennetaan vaaditut kirjastot
if [ -f "requirements.txt" ]; then
    echo "📦 Tarkistetaan kirjastojen päivitykset..."
    pip install --upgrade pip  # Päivitetään pip samalla
    pip install -r requirements.txt
else
    echo "⚠️ VAROITUS: requirements.txt puuttuu, ohitetaan asennus."
fi

# 5. Käynnistetään Chainlit
echo "🚀 Käynnistetään sovellus porttiin 8087..."
chainlit run app.py --port 8087 --host 0.0.0.0 -w