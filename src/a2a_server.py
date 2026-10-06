from flask import Flask, jsonify, request
import uuid
from graph import app as specialist_graph   
from langgraph.types import interrupt, Command
import os

flask_app = Flask(__name__)
TASKS = {}

AGENT_CARD = {
    "name": "billing-investigation-specialist",
    "description": "Billing specialist which checks history, disputes to resolve triage ticket.",   
    "url": "http://localhost:8001", 
    "skills": [
        {
            "id": "investigate_billing_dispute",
            "name": "investigate_billing_dispute",
            "description": '''Accepts an order_id and returns a resolution decision (resolve/escalate) with a reason. May pause pending human review for ambiguous cases.'''
        }
    ]
}

@flask_app.route("/tasks", methods=["POST"])
def submit_task():
    order_id = request.json["order_id"]
    task_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": task_id}}
    
    initial_state = {"order_id": order_id, "charges": [], "decision": "", "reason": "", "attempt": 0}
    result = specialist_graph.invoke(initial_state, config=config)
    if "__interrupt__" in result:
        status = "input-required"
    else:
        status = "completed"
    TASKS[task_id] = {"status": status, "result": result}
    return jsonify({"order_id": order_id, "status": result["decision"] , "reason": result["reason"],"task_id": task_id})

@flask_app.route("/tasks/<task_id>", methods=["GET"])
def check_task(task_id):
    task = TASKS.get(task_id)
    if task is None:
        return jsonify({"error": "unknown task_id"}), 404
    return jsonify({"task_id": task_id, **task})    

@flask_app.route("/tasks/<task_id>/input", methods=["POST"])
def submit_input(task_id):
    task = TASKS.get(task_id)
    if task is None or task["status"] != "input-required":
        return jsonify({"error": "task not awaiting input"}), 400
    
    human_answer = request.json["decision"]   # e.g. "escalate" or "resolve"
    config = {"configurable": {"thread_id": task_id}}
    
    result = specialist_graph.invoke(Command(resume=human_answer), config=config)
    
    status = "input-required" if "__interrupt__" in result else "completed"
    TASKS[task_id] = {"status": status, "result": result}
    return jsonify({"task_id": task_id, "status": status})

@flask_app.route("/.well-known/agent.json")
def agent_card():
    return jsonify(AGENT_CARD)

if __name__ == "__main__":
    #flask_app.run(port=8001)
    host = os.getenv("BIND_HOST", "127.0.0.1")
    port = int(os.getenv("BIND_PORT", 8001))
    flask_app.run(host=host, port=port)
