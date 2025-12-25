# main.py

import os
# Tuo luodut työkalut sisään
from tyokalut import stock_price_tool 

from autogen import ConversableAgent, config_list_openai_aoai

# --- 1. Aseta LLM-asetukset ---
# LLM = Large Language Model (Suuri Kielimalli)

# Hakee kokoonpanon ympäristömuuttujista (suositeltu tapa)
# Vaatii, että OPENAI_API_KEY on asetettu.
config_list = config_list_openai_aoai()

if config_list and 'model' not in config_list[0]:
    # Asetetaan malli jokaiseen listan alkioon.
    for config in config_list:
        # Käytä mallin nimeä, jonka haluat:
        config["model"] = "gpt-4o-mini" # TAI "gpt-3.5-turbo"

# Haetaan työkalun skeema (sanahirja)
function_details = stock_price_tool.schema

openai_tools_list = [
    {
        "type": "function",          # Pakollinen tyyppi
        "function": function_details # Sisältää name, description, parameters
    }
]


stock_tool_schema = stock_price_tool.schema
stock_tool_schema["type"] = "function"

# --- 2. Luo Agentti (Assistant) ---
# AssistantAgent on agentti, joka osaa käyttää työkaluja ja koodia.
assistant = ConversableAgent(
    name="Assistant",
    # KORJATTU KOHTA: Kolme lainausmerkkiä sallii usean rivin merkkijonon
    system_message="""Olet avulias apulainen, joka vastaa käyttäjän kysymyksiin.
    Käytä osaketyökalua (stock_price_tool), kun sinulta kysytään osakkeen hintaa. 
    Vastaa ystävällisesti suomeksi. Älä keksi hintoja, jos työkalu ei toimi.""",
    llm_config={
        "config_list": config_list,
        # TÄRKEÄÄ: Määrittele työkalut, jotka agentti saa käyttöönsä
        "tools": openai_tools_list
    },
    # Määrittelee, milloin agentin vastauksen katsotaan olevan valmis.
    # Esimerkiksi: kun vastaus sisältää "hyvästi" tai "kiitos".
    is_termination_msg=lambda msg: msg.get("content") is not None and ("hyvästi" in msg["content"].lower() or "kiitos" in msg["content"].lower()),
)

# --- 3. Luo Käyttäjä-Agentti (User Proxy) ---
# UserProxyAgent on agentti, joka edustaa käyttäjää ja osaa suorittaa 
# työkaluja tai koodia, jonka Assistant pyytää.
user_proxy = ConversableAgent(
    name="user_proxy",
    is_termination_msg=lambda msg: msg.get("content") is not None and ("hyvästi" in msg["content"].lower() or "kiitos" in msg["content"].lower()),    human_input_mode="NEVER", # Aseta "ALWAYS" jos haluat itse kirjoittaa välissä
    max_consecutive_auto_reply=10,
    code_execution_config=False, # Ei tarvita koodin suoritusta tähän
)


# --- 4. Käynnistä Keskustelu ---
if __name__ == "__main__":
    # Kysymys, joka aktivoi luodun työkalun (stock_price_tool)
    aloitus_viesti = "Mikä on osakkeen GOOG hinta päivänä 2024/07/20?"
    
    print(f"--- Aloitetaan keskustelu ---")
    print(f"Käyttäjän kysymys: {aloitus_viesti}")

    # Lähetetään kysymys, jolloin agentit alkavat keskustella
    user_proxy.initiate_chat(
        assistant,
        message=aloitus_viesti,
    )
    
    print(f"--- Keskustelu päättyi ---")