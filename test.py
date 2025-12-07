from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-277620b036514acc8899643eee5163e0"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain how a flyback transformer works."}
    ],
)

print(response.choices[0].message.content)
