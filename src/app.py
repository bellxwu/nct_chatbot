# %%
from NCT_chat.main import get_nct_chat
from langchain_core.messages import HumanMessage, AIMessage
import gradio as gr
from dotenv import load_dotenv
# %%
from utils.logger import get_logger

_logs = get_logger(__name__)

# %% Load secrets/config once at import (API keys for the LLM).
load_dotenv(".env")
load_dotenv(".secrets")
# %%
# Compile the LangGraph agent a single time, at startup, not per message.
agent = get_nct_chat()

# System-facing description shown to the user in the chat header.
DESCRIPTION = (
    "Ask about clinical trials on ClinicalTrials.gov — search by condition, "
    "drug, sponsor, or a specific NCT ID (e.g. NCT01234567). "
    "Initial focus is oncology."
)

EXAMPLES = [
    "What recruiting phase 3 oncology trials are there for pancreatic cancer?",
    "Show me details for NCT04185883",
    "Which companies are sponsoring trials for glioblastoma?",
]


def nct_chat(message: str, history: list[dict]) -> str:
    """
    Bridge between Gradio's ChatInterface and the LangGraph agent.

    Gradio hands us the new `message` plus `history` (a list of
    {'role', 'content'} dicts). We replay that history as LangChain
    messages, append the new turn, invoke the graph, and return the
    final assistant reply as a plain string.
    """
    langchain_messages = []
    n = 0  # count of prior assistant turns -> seed for llm_calls
    _logs.debug(f"History: {history}")

    for msg in history:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))
            n += 1

    langchain_messages.append(HumanMessage(content=message))

    # Shape must match MessagesState in main.py.
    state = {
        "messages": langchain_messages,
        "llm_calls": n,
        "total_tokens": 0,
    }

    try:
        response = agent.invoke(state)
        tokens = response["total_tokens"]
        llm_calls = response["llm_calls"]
    except Exception as exc:  # keep the UI alive if the graph/API fails
        _logs.error("Agent invocation failed: %s", exc)
        return f"Sorry — something went wrong handling that request: {exc}", state["total_tokens"], state["llm_calls"]

    # The last message in the returned state is the assistant's reply.
    return response["messages"][-1].content, tokens, llm_calls

token_box = gr.Number(label="Total Tokens", value=0)
llm_calls_box = gr.Number(label="LLM calls", value=0)

with gr.Blocks() as chat:
    token_box = gr.Number(label="Total tokens", value=0)
    llm_calls_box = gr.Number(label="Total LLM calls")
    gr.ChatInterface(
        fn=nct_chat,
        title="NCT Trials Explorer",
        description=DESCRIPTION,
        examples=EXAMPLES,
        additional_outputs=[token_box, llm_calls_box]
    )

if __name__ == "__main__":
    _logs.info("Starting NCT Chat App...")
    chat.launch()