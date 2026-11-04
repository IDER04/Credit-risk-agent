"""Runs a few questions through the real agent (needs MySQL + LLM). Run: python tests/manual/agent_smoke.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent import Agent

agent = Agent(on_tool=lambda name, args: print(f"   [tool called] {name}({args})"))

for question in [
    "Show me client 102.",
    "Show me client 999.",
    "How many loans does client 102 have?",
    "What is the capital of France?",
]:
    print("\nYou:", question)
    print("Agent:", agent.chat(question))

# Conversation memory: same agent remembers, a new one does not.
print("\n--- memory check")
agent.reset()
print("1:", agent.chat("My name is Sam. In one sentence, what is your role?"))
print("2:", agent.chat("What is my name?"))
print("3 (new agent):", Agent().chat("What is my name?"))
