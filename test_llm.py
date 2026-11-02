from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

response = client.chat.completions.create(
    model=LLM_MODEL,
    messages=[{"role": "user", "content": "In one sentence, what is a payment incident in credit risk?"}],
)
print(response.choices[0].message.content)