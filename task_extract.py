import base64
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

def generate(email):
    load_dotenv()
    
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-pro-exp-02-05"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"""You are a helpful assistant that extracts actionable tasks from emails. Review the email below and identify all tasks, assignments, requests, and action items that need to be completed.

For each task identified:
1. Provide a clear, concise description of what needs to be done
2. Include any relevant deadlines mentioned
3. Note who is responsible for the task (if specified)
4. List any dependencies or prerequisites needed to complete the task
                                     
use this template for each task:
- Task: [Task description]
- Deadline: [Deadline]
- Responsible: [Person responsible(recipient,sender,etc)]
- Dependencies: [Dependencies] Make inferences.

Here is the email:
{email}
"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=64,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")

if __name__ == "__main__":
   while True:
      email = input("Please enter the email to be processed:")
      generate(email)
