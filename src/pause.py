from graph import app

config = {"configurable": {"thread_id": "test-case-001"}}
result = app.invoke({"order_id": "B2001", "charges": [], "decision": "", "reason": "", "attempt": 0}, config=config)
print(result)