import json

from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from tools import TOOL_SPECS, Pending, run_tool

SYSTEM_PROMPT = """You are a credit-risk assistant connected to a bank's client database through tools.

RULES
1. For any question about clients, call a tool. Never answer from memory.
2. Never invent client ids, names or figures. If a tool returns an error, report it plainly.
3. If no available tool can answer, say so. Do not guess.
4. Terminology: in this database a "crédit" is a loan. Always say "loan(s)" in English (or "prêt(s)" in French), never "credit(s)". Loan types such as Consommation or Immobilier are types of loan.
5. Answer concisely, in the same language as the user.
6. To change data, call the matching tool directly. The system itself asks the human to confirm, so do not ask for confirmation yourself. Only say a change was made if the tool result has status "created", "updated" or "deleted". If the result is "cancelled", say nothing was changed.
7. When creating something, ask for any required detail the user did not give instead of guessing. When updating, the loan or client id plus the fields the user wants to change are enough. Never ask for the other fields, and never ask the user to confirm unchanged values. Omit fields you are not changing; never pass 0 or an empty string as a placeholder."""

MAX_STEPS = 5

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


class Agent:
    def __init__(self, on_tool=None):
        self.on_tool = on_tool or (lambda name, args: None)
        self.reset()

    def reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_text, confirm=None):
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(MAX_STEPS):
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=self.messages,
                tools=TOOL_SPECS,
            )
            msg = response.choices[0].message

            # No tool requested -> this is the final answer.
            if not msg.tool_calls:
                self.messages.append({"role": "assistant", "content": msg.content})
                return msg.content or ""

            # The model asked for tools: record its request, then run each one.
            self.messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.function.name, "arguments": c.function.arguments},
                    }
                    for c in msg.tool_calls
                ],
            })
            for call in msg.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = None
                self.on_tool(name, args)
                if args is None:
                    result = {"error": "Arguments were not valid JSON."}
                else:
                    result = run_tool(name, args)
                    if isinstance(result, Pending):
                        if confirm is not None and confirm(result.description):
                            result = result.run()
                        else:
                            result = {"status": "cancelled",
                                      "message": "The user declined. Nothing was changed."}
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str, ensure_ascii=False),
                })
        return "I could not finish this request (too many steps). Please rephrase it."