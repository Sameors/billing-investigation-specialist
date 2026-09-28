from graph import app

config = {"configurable": {"thread_id": "0d13ddd8-8882-43d3-a6b4-5b14bd3fff53"}}
result = app.invoke({"order_id": "A1123", "charges": [], "decision": "", "reason": "", "attempt": 0}, config=config)
print(result)