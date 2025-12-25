# app.py
import os
import chainlit as cl
from autogen import ConversableAgent, UserProxyAgent
from autogen import config_list_openai_aoai
from tyokalut import hae_kayttajat_tool, stock_price_autogen_tool, distance_autogen_tool, get_stock_price, calculate_distance, hae_kayttajat

async def custom_human_input_handler(
    recipient: ConversableAgent,
    messages: list[dict],
    sender: ConversableAgent,
    config: dict,
):
    last_msg = messages[-1]
    
    if "tool_calls" in last_msg and last_msg["tool_calls"]:
        return False, None
        
    if last_msg.get("content"):
        await cl.Message(
            content=last_msg["content"], 
            author=sender.name
        ).send()

    res = await cl.AskUserMessage(content="", timeout=600).send()
    
    return True, res['output'] if res else "exit"


def get_agents():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    config_list = [{"model": "gpt-4o-mini", "api_key": api_key}]

    openai_tools_list = [
        { "type": "function", "function": stock_price_autogen_tool.schema },
        { "type": "function", "function": distance_autogen_tool.schema },
        { "type": "function", "function": hae_kayttajat_tool.schema }
    ]

    assistant = ConversableAgent(
        name="Assistant",
        system_message="""Olet avulias apulainen.
        Käytä etäisyyslaskuria (calculate_distance), kun kysytään etäisyyttä.
        Jos käyttäjä antaa vain yhden koordinaatin, KYSY TOINEN.
        Tiedät myös hakea käyttäjät tietokannasta (hae_kayttajat).
        Vastaa ystävällisesti suomeksi.""",
        llm_config={
            "config_list": config_list,
            "tools": openai_tools_list
        },
    )
    
    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",  
        code_execution_config=False,
    )

    user_proxy.register_for_execution(name="get_stock_price")(get_stock_price)
    user_proxy.register_for_execution(name="calculate_distance")(calculate_distance)
    user_proxy.register_for_execution(name="hae_kayttajat")(hae_kayttajat)
    
    user_proxy.register_reply(
        trigger=[assistant, None],
        reply_func=custom_human_input_handler,
        position=0
    )
    
    return user_proxy, assistant

@cl.on_chat_start
async def start():
    user_proxy, assistant = get_agents()
    cl.user_session.set("user_proxy", user_proxy)
    cl.user_session.set("assistant", assistant)
    await cl.Message(content="Tervetuloa! Voit kysyä etäisyyksiä.").send()

@cl.on_message
async def main(message: cl.Message):
    user_proxy = cl.user_session.get("user_proxy")
    assistant = cl.user_session.get("assistant")
    
    await user_proxy.a_initiate_chat(
        assistant,
        message=message.content,
        summary_method="last_msg"
    )