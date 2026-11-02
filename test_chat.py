from agent import Agent

agent = Agent()
print("1:", agent.chat("My name is Sam. In one sentence, what is your role?"))
print("2:", agent.chat("What is my name?"))

other = Agent()   # a brand-new conversation
print("3:", other.chat("What is my name?"))