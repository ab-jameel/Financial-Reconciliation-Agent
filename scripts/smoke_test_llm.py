# scripts/smoke_test_llm.py
from dotenv import load_dotenv
load_dotenv()
import litellm, os

if __name__ == "__main__":
    response = litellm.completion(
        model=os.environ["LLM_MODEL"],
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
    )
    print(response.choices[0].message.content)