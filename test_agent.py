from agent import Agent

agent = Agent(on_tool=lambda name, args: print(f"   [tool called] {name}({args})"))

for question in [
    "Show me client 102.",
    "Show me client 999.",
    "How many credits does client 102 have?",
    "What is the capital of France?",
]:
    print("\nYou:", question)
    print("Agent:", agent.chat(question))