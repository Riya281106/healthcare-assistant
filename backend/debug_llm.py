from app.services.llm.service import get_ai_response

result = get_ai_response("what should I know about fever?")

with open("debug_output.txt", "w", encoding="utf-8") as f:
    f.write(result)

print("Wrote result to debug_output.txt")
