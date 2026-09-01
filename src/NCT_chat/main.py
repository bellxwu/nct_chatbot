# %%
# %% import libraries
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict, Annotated
import operator
# %%
from pathlib import Path
from dotenv import load_dotenv
import json
import requests
# %%
from utils.logger import get_logger
# %%
_logs = get_logger(__name__)
# %% load .env file relative to main file
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
# %% define tool 1: call NCT API
@tool
def get_NCT(
    query: str = "",
    nct_id: str = "",
    status: str = "",
    phase: str = "",
    max_results: int = 5,
) -> str:
    '''
    Search clinicaltrials.gov (ClinicalTrials.gov API v2) for clinical trials
    and return a curated summary of the matching studies.

    Use this whenever the user asks about clinical trials, studies, or
    treatments being tested for a condition. Provide either a free-text `query`
    (a condition, disease, drug, or keyword) or a specific `nct_id`, and
    optionally narrow the results with `status` and `phase`.

    Args:
        query: Free-text search term, e.g. a condition or intervention
            ("type 2 diabetes", "semaglutide"). Ignored if `nct_id` is given.
        nct_id: A specific trial identifier, e.g. "NCT01234567". When provided,
            the tool returns just that one trial and other filters are ignored.
        status: Optional overall-status filter, e.g. "RECRUITING",
            "COMPLETED", "ACTIVE_NOT_RECRUITING", "TERMINATED". Case-insensitive.
        phase: Optional trial-phase filter. Accepts "1"-"4", "0"/"EARLY_PHASE1",
            or the full form like "PHASE2". Case-insensitive.
        max_results: Maximum number of trials to return (1-20). Defaults to 5.

    Returns:
        A JSON string containing a list of trials, each with: nct_id, title,
        status, phases, conditions, brief_summary, lead_sponsor (the company or
        organization running the trial), collaborators (a list of partner
        names), and url. On error or no match, returns a JSON object with an
        "error" or "message" field.
    '''
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    fields = [
        "protocolSection.identificationModule.nctId",
        "protocolSection.identificationModule.briefTitle",
        "protocolSection.statusModule.overallStatus",
        "protocolSection.designModule.phases",
        "protocolSection.conditionsModule.conditions",
        "protocolSection.descriptionModule.briefSummary",
        "protocolSection.sponsorCollaboratorsModule.leadSponsor.name",
        "protocolSection.sponsorCollaboratorsModule.collaborators.name",
    ]

    def _summarize(study: dict) -> dict:
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        nct = ident.get("nctId", "")
        sponsors = proto.get("sponsorCollaboratorsModule", {})
        return {
            "nct_id": nct,
            "title": ident.get("briefTitle", ""),
            "status": proto.get("statusModule", {}).get("overallStatus", ""),
            "phases": proto.get("designModule", {}).get("phases", []),
            "conditions": proto.get("conditionsModule", {}).get("conditions", []),
            "brief_summary": proto.get("descriptionModule", {}).get("briefSummary", ""),
            "lead_sponsor": sponsors.get("leadSponsor", {}).get("name", ""),
            "collaborators": [
                c.get("name", "") for c in sponsors.get("collaborators", [])
            ],
            "url": f"https://clinicaltrials.gov/study/{nct}" if nct else "",
        }

    try:
        # --- Single-trial lookup by NCT ID -------------------------------
        if nct_id:
            nct_id = nct_id.strip().upper()
            resp = requests.get(
                f"{base_url}/{nct_id}",
                params={"fields": ",".join(fields)},
                timeout=30,
            )
            if resp.status_code == 404:
                return json.dumps({"message": f"No trial found for {nct_id}."})
            resp.raise_for_status()
            return json.dumps([_summarize(resp.json())], indent=2)

        # --- Search --------------------------------------------------------
        params = {
            "fields": ",".join(fields),
            "pageSize": max(1, min(int(max_results), 20)),
            "countTotal": "true",
        }
        if query:
            params["query.cond"] = query
        if status:
            params["filter.overallStatus"] = status.strip().upper()
        if phase:
            # Normalize "2" -> "PHASE2", "0" -> "EARLY_PHASE1", pass full forms through.
            p = phase.strip().upper().replace(" ", "_")
            phase_map = {
                "0": "EARLY_PHASE1",
                "1": "PHASE1",
                "2": "PHASE2",
                "3": "PHASE3",
                "4": "PHASE4",
            }
            p = phase_map.get(p, p)
            # Essie expression filtering on the Phase area.
            params["filter.advanced"] = f"AREA[Phase]{p}"

        resp = requests.get(base_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        studies = data.get("studies", [])
        if not studies:
            return json.dumps({"message": "No matching trials found."})

        results = [_summarize(s) for s in studies]
        return json.dumps(results, indent=2)

    except requests.RequestException as exc:
        _logs.error("clinicaltrials.gov request failed: %s", exc)
        return json.dumps({"error": f"Request to clinicaltrials.gov failed: {exc}"})
# %% define tool 2
# %% model with tools, bind the 
def get_model_with_tools():
    '''
    Define the foundational model and bind tools with model
    '''
    # define model
    model = init_chat_model(
        model="claude-haiku-4-5-20251001",
        temperature=0.7
    )
    # collect tools
    tools = [get_NCT]
    # bind tools to llm
    llm_with_tools = model.bind_tools(tools)
    return llm_with_tools

def llm_call(state: dict):
    '''
    Invoke the model on the conversation and append its reply to state
    '''
    model_with_tools = get_model_with_tools()
    return {
        "messages": [
                    model_with_tools.invoke(
                        [
                            SystemMessage(
                                content="You are a financial analyst of biotech companies sifting through clinical trials."
                            )
                        ]
                        + state["messages"]
                    )
                ],
                "llm_calls": state.get('llm_calls', 0) + 1,
                "total_tokens": state.get('total_tokens', 0)
    }

def tool_node(state: dict):
    '''
    Function to give agent ability to call tool.
    '''
    tools = [get_NCT]
    tools_by_name = {tool.name: tool for tool in tools}

    results = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        # call the tool from the AI message
        observation = tool.invoke(tool_call["args"])
        results.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))

    return {"messages": results}

# %% define class
class MessagesState(TypedDict):
    '''
    Creating structured output to store messages for agent. 
    '''
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
    total_tokens: Annotated[int, operator.add]

# %% 
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    '''
    Allows agent to decide whether additional tool calls are needed. 
    '''
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"

    return END
# %% compile agent 
def get_nct_chat():
    '''
    Compile functions into graph by building nodes and edges.
    '''
    agent_builder = StateGraph(MessagesState)

    # build graph nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)

    # add edges
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        ["tool_node", END]
    )
    agent_builder.add_edge('tool_node', "llm_call")

    # compile
    return agent_builder.compile()