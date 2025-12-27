# app.py
import os
import chainlit as cl
from autogen import ConversableAgent, UserProxyAgent, GroupChat, GroupChatManager
from tyokalut import hae_kayttajat_tool, stock_price_autogen_tool, distance_autogen_tool, get_stock_price, calculate_distance, hae_kayttajat
from wordpress_tyokalut import wp_luo_ymparisto_tool, wp_poista_ymparisto_tool, wp_listaa_ymparistot_tool, wp_muuta_ymparisto_tool, wp_sammuta_ymparisto_tool, wp_kaynnista_ymparisto_tool, wp_listaa_kaikki_ymparistot_tool, wp_luo_ymparisto, wp_poista_ymparisto, wp_listaa_ymparistot, wp_muuta_ymparisto, wp_sammuta_ymparisto, wp_kaynnista_ymparisto, wp_listaa_kaikki_ymparistot

async def custom_human_input_handler(recipient, messages, sender, config):
    last_msg = messages[-1]
    if "tool_calls" in last_msg and last_msg["tool_calls"]:
        return False, None
    if last_msg.get("content"):
        await cl.Message(content=last_msg["content"], author=sender.name).send()
    res = await cl.AskUserMessage(content="", timeout=600).send()
    return True, res['output'] if res else "exit"

def get_agents():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    config_list = [{"model": "gpt-4o-mini", "api_key": api_key}]

    general_tools = [
        {"type": "function", "function": stock_price_autogen_tool.schema},
        {"type": "function", "function": distance_autogen_tool.schema},
        {"type": "function", "function": hae_kayttajat_tool.schema},
    ]
    
    wp_tools = [
        {"type": "function", "function": wp_luo_ymparisto_tool.schema},
        {"type": "function", "function": wp_poista_ymparisto_tool.schema},
        {"type": "function", "function": wp_listaa_ymparistot_tool.schema},
        {"type": "function", "function": wp_muuta_ymparisto_tool.schema},
        {"type": "function", "function": wp_sammuta_ymparisto_tool.schema},
        {"type": "function", "function": wp_kaynnista_ymparisto_tool.schema},
        {"type": "function", "function": wp_listaa_kaikki_ymparistot_tool.schema}
    ]

    # Agentit
    assistant = ConversableAgent(
        name="Orkestroija",
        system_message="""Olet pääagentti. Tehtäväsi on auttaa käyttäjää ja ohjata 
        WordPress-tekniset kysymykset WordPress_Expert-agentille. 
        Käytä omia työkalujasi etäisyyksiin ja käyttäjähakuun.""",
        llm_config={"config_list": config_list, "tools": general_tools},
    )
    
    wp_expert = ConversableAgent(
        name="WordPress_Expert",
        system_message="""Olet WordPress-asiantuntija. Hallinnoit Docker-pohjaisia 
        WordPress-ympäristöjä työkaluillasi. Raportoi tulokset selkeästi.""",
        llm_config={"config_list": config_list, "tools": wp_tools},
    )
    
    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    all_tools = [
        (get_stock_price, "get_stock_price"),
        (calculate_distance, "calculate_distance"),
        (hae_kayttajat, "hae_kayttajat"),
        (wp_luo_ymparisto, "wp_luo_ymparisto"),
        (wp_poista_ymparisto, "wp_poista_ymparisto"),
        (wp_listaa_ymparistot, "wp_listaa_ymparistot"),
        (wp_muuta_ymparisto, "wp_muuta_ymparisto"),
        (wp_sammuta_ymparisto, "wp_sammuta_ymparisto"),
        (wp_kaynnista_ymparisto, "wp_kaynnista_ymparisto"),
        (wp_listaa_kaikki_ymparistot, "wp_listaa_kaikki_ymparistot"),
    ]
    for func, name in all_tools:
        user_proxy.register_for_execution(name=name)(func)
    
    groupchat = GroupChat(
        agents=[user_proxy, assistant, wp_expert], 
        messages=[], 
        max_round=15
    )
    
    manager = GroupChatManager(
        groupchat=groupchat, 
        llm_config={"config_list": config_list}
    )
    
    user_proxy.register_reply(
        trigger=[manager, None],
        reply_func=custom_human_input_handler,
        position=0
    )
    
    return user_proxy, manager

@cl.on_chat_start
async def start():
    user_proxy, manager = get_agents()
    cl.user_session.set("user_proxy", user_proxy)
    cl.user_session.set("manager", manager)
    await cl.Message(content="Tervetuloa! Olen orkestroija apulaisineen. Miten voin auttaa?").send()

@cl.on_message
async def main(message: cl.Message):
    user_proxy = cl.user_session.get("user_proxy")
    manager = cl.user_session.get("manager")
    
    await user_proxy.a_initiate_chat(
        manager,
        message=message.content,
        summary_method="last_msg"
    )