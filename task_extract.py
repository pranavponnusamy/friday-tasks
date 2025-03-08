import os
import json
import time
import random
from enum import Enum
from typing import List, Optional
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Define Task Type enum
class TaskType(str, Enum):
    MEETING = "meeting_scheduling"
    REMINDER = "reminder"
    TODO = "to_do_item"

# Define Task structure using Pydantic
class Task(BaseModel):
    description: str = Field(..., description="Clear description of the task")
    deadline: Optional[str] = Field(None, description="Deadline for the task if specified")
    task_type: TaskType = Field(..., description="Type of task (meeting, reminder, or to-do item)")
    dependencies: Optional[List[str]] = Field(None, description="Dependencies needed to complete the task")
    responsible: Optional[str] = Field(None, description="Person responsible for completing the task")

class Tasks(BaseModel):
    tasks: List[Task] = Field(..., description="List of tasks extracted from the email")

def generate(email, metadata=None):
    load_dotenv()
    
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
    )

    # Try a more efficient model first
    model = "gemini-2.0-flash"
    
    # Prepare metadata context
    metadata_context = ""
    if metadata:
        metadata_context = "\n\nEmail Metadata:"
        if metadata.get("sender"):
            metadata_context += f"\nFrom: {metadata['sender']}"
        if metadata.get("recipients"):
            metadata_context += f"\nTo: {', '.join(metadata['recipients'])}"
        if metadata.get("cc"):
            metadata_context += f"\nCC: {', '.join(metadata['cc'])}"
        if metadata.get("user_email"):
            metadata_context += f"\nYour email: {metadata['user_email']}"
    
    # Create content for the API request
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
5. Classify the task as one of the following:
   - "meeting_scheduling" for meetings and appointments
   - "reminder" for simple reminders
   - "to_do_item" for tasks and items that need to be completed

Return the tasks as a JSON array with the following structure for each task:
{{
  "description": "Task description",
  "deadline": "Deadline (or null if not specified)",
  "responsible": "Person responsible for the task (or null if not specified)",
  "dependencies": ["Dependency 1", "Dependency 2"] (or null if none),
  "task_type": "meeting_scheduling", "reminder", or "to_do_item"
}}

When determining who is responsible for a task:
- If the sender is assigning a task to recipients, the recipients are likely responsible
- If the sender is requesting something from specific people, those people are responsible
- If the email is addressed to you specifically, you're likely responsible unless stated otherwise
- If the sender is stating what they will do, they are responsible
- Use full names when available, or email addresses as fallback

Here is the email:{metadata_context}
{email}
"""),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=0.2,  # Lower temperature for more consistent results
        top_p=0.95,
        top_k=64,
        max_output_tokens=2048,  # Reduced token limit
        response_mime_type="application/json",
    )

    # Implement retry with exponential backoff
    max_retries = 5
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Making API call (attempt {attempt+1}/{max_retries})...")
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )
            
            # Get the text response and parse it as JSON
            response_text = response.candidates[0].content.parts[0].text
            print("API call successful")
            
            try:
                # Try parsing as JSON
                structured_response = json.loads(response_text)
                
                # Handle different response formats
                if isinstance(structured_response, list):
                    # If it's a list of tasks directly
                    return [Task(**task) for task in structured_response]
                elif isinstance(structured_response, dict) and "tasks" in structured_response:
                    # If it's a dict with a tasks key
                    tasks_obj = Tasks(**structured_response)
                    return tasks_obj.tasks
                else:
                    print(f"Unexpected JSON structure: {structured_response}")
                    return []
            except json.JSONDecodeError:
                print(f"Could not parse text as JSON: {response_text}")
                return []
                
        except ClientError as e:
            if e.status_code == 429:  # Rate limit error
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Rate limit exceeded. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    print("Maximum retry attempts reached. Returning empty task list.")
                    return []
            else:
                print(f"API Error: {e}")
                return []
        except Exception as e:
            print(f"Error generating output: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    return []  # Return empty list if all retries fail

if __name__ == "__main__":
   while True:
      email = input("Please enter the email to be processed: ")
      tasks = generate(email)
      for i, task in enumerate(tasks, 1):
          print(f"\nTask {i}:")
          print(f"Description: {task.description}")
          print(f"Deadline: {task.deadline or 'Not specified'}")
          print(f"Responsible: {task.responsible or 'Not specified'}")
          print(f"Dependencies: {', '.join(task.dependencies) if task.dependencies else 'None'}")
          print(f"Type: {task.task_type}")
