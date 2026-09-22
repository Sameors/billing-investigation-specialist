from graph import app
from langgraph.types import interrupt, Command

config = {"configurable": {"thread_id": "test-case-001"}}
result = app.invoke(Command(resume="escalate"), config=config)
print(result)