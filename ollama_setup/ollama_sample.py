from ollama import ChatResponse, chat

response: ChatResponse = chat(
    model="qwen3.5:9b",
    messages=[
        {
            "role": "user",
            "content": "What is 3 + 7 ?",
        },
    ],
    stream=False,
)

print(response["message"]["content"])
# or access fields directly from the response object
# print(response.message.content)
