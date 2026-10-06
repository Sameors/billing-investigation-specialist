from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from datetime import datetime
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3 
import requests
import uuid
import os
# thread_id = str(uuid.uuid4())
LEDGER_URL = os.getenv("LEDGER_URL", "http://localhost:8000")

class SpecialistState(TypedDict):
    order_id: str
    charges: list[dict]   
    decision: str          
    reason: str
    attempt: int
    refund_history: list[dict]   
    dispute_flag: list[dict]
    needs_human: str
    retry_reason: str
    fetch_error: str
    
def fetch_ledger(state: SpecialistState) -> dict:
    try:
        response = requests.get(f"{LEDGER_URL}/ledger/{state['order_id']}", timeout=2)
    except requests.exceptions.ConnectionError:
        return {"charges": [], "fetch_error": "connection_failed"}
    if response.status_code == 404:
        return {"charges": [], "fetch_error": ""}   # genuinely no data, not a service failure
    return {"charges": response.json(), "fetch_error": ""}
    
def assess_evidence(state: SpecialistState) -> str:
    if len(state["charges"]) == 0 and state["attempt"] <= 4:
        return "retry_fetch"
    time_format = "%I:%M%p"
    if state["attempt"] > 4:
        return "human_review"
    minutes_difference = ((datetime.strptime(state["charges"][0]["timestamp"], time_format) - 
                           datetime.strptime(state["charges"][1]["timestamp"], time_format)).total_seconds()) / 60
    if state["charges"][0]["amount"] == state["charges"][1]["amount"] and minutes_difference < 2:
        return "dual_check"
    return "auto_resolve"

def auto_resolve(state: SpecialistState) -> dict:
    decision = "resolve"
    reason = "clean history, no conflict"
    return {"decision":decision ,"reason":reason}

def retry_fetch(state: SpecialistState) -> dict:
        if state["fetch_error"] == "connection_failed":
            reason = f"ledger service unreachable, retrying (attempt {state['attempt']+1})"
        else:
            reason = "ledger empty, would retry here"
        return {"retry_reason": reason, "attempt":state["attempt"]+1}

def dual_check(state) -> dict:
    return {}  

def check_refund_history(state: SpecialistState) -> dict:
    try:
        response = requests.get(f"{LEDGER_URL}/refund-history/{state['order_id']}", timeout=2)
    except requests.exceptions.ConnectionError:
        return {"refund_history": [{"isflagged": False, "note": "refund history service unreachable", "service_error": True}]}
    return {"refund_history":response.json()}

def check_dispute_flags(state: SpecialistState) -> dict:
    try:
        response = requests.get(f"{LEDGER_URL}/dispute-flags/{state['order_id']}", timeout=2)
    except requests.exceptions.ConnectionError:
        return {"dispute_flag": [{"isflagged": False, "note": "dispute flag service unreachable", "service_error": True}]}
    return {"dispute_flag":response.json()}
     

def reconcile(state) -> dict:
    if state["refund_history"].get("service_error") or state["dispute_flag"].get("service_error"): 
        return {"needs_human":True ,"reason":"service unreachable"}
    if state["refund_history"]["isflagged"] :
        return {"needs_human":True ,"reason":state["refund_history"]["note"]}
    if state["dispute_flag"]["isflagged"]:
        return {"needs_human":True ,"reason":state["dispute_flag"]["note"]}    
    return {"needs_human":False}

def needs_human(state) -> str:
    if state["needs_human"] == True:
        return "human_review"
    return "auto_resolve"

def human_review(state) -> dict:
    reason = state["reason"] or state["retry_reason"]
    decision = interrupt({"reason": reason, "order_id": state["order_id"]})
    return {"decision": decision}

graph = StateGraph(SpecialistState)

graph.add_node("fetch_ledger", fetch_ledger)
graph.add_node("auto_resolve", auto_resolve)
graph.add_node("retry_fetch", retry_fetch)
graph.add_node("dual_check", dual_check)
graph.add_node("reconcile", reconcile)
graph.add_node("human_review", human_review)
graph.add_node("check_refund_history", check_refund_history)
graph.add_node("check_dispute_flags", check_dispute_flags)

graph.add_edge(START, "fetch_ledger")
graph.add_conditional_edges("fetch_ledger", assess_evidence)
graph.add_edge("retry_fetch", "fetch_ledger")
graph.add_edge("auto_resolve", END)
graph.add_edge("dual_check","check_refund_history")
graph.add_edge("dual_check","check_dispute_flags")
graph.add_edge("check_refund_history","reconcile")
graph.add_edge("check_dispute_flags","reconcile")
graph.add_conditional_edges("reconcile", needs_human)
graph.add_edge("human_review", END)

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
app = graph.compile(checkpointer=checkpointer)

# config = {"configurable": {"thread_id": thread_id}}


# result1 = app.invoke({"order_id": "B2002", "charges": [], "decision": "", "reason": "", "attempt": 0}, config=config)
# print(result1)   # should show the paused interrupt, with only reason/order_id inside

# result2 = app.invoke(Command(resume="escalate"), config=config)
# print(result2)   # should show the final state, decision == "escalate"