import os
import json
import datetime
from typing import List, Optional
from dotenv import load_dotenv
from nylas import Client
from pydantic import BaseModel

# Import task extraction functionality
from task_extract import generate, Task

def setup_nylas_client():
    """Initialize and return the Nylas client"""
    load_dotenv()
    
    nylas = Client(
        os.environ.get('NYLAS_API_KEY'),
        os.environ.get('NYLAS_API_URI')
    )
    
    return nylas, os.environ.get("NYLAS_GRANT_ID")

def fetch_recent_emails(nylas, grant_id, days=7, limit=10):
    """Fetch emails from the last X days"""
    one_week_ago = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())
    
    print(f"Fetching up to {limit} emails from the last {days} days...")
    
    messages = nylas.messages.list(
        grant_id,
        query_params={
            "limit": limit,
            "received_after": one_week_ago,
            "in": "INBOX"
        }
    )
    
    # Sort messages from most recent to least recent
    sorted_messages = sorted(messages[0], key=lambda m: getattr(m, "date", 0), reverse=True)
    return sorted_messages

def display_email_summary(email, index):
    """Display a concise summary of an email"""
    sender = ""
    if hasattr(email, "from_") and email.from_:
        sender = email.from_[0].get("email", "") if isinstance(email.from_[0], dict) else email.from_[0]
    
    subject = getattr(email, "subject", "No Subject")
    date_ts = getattr(email, "date", 0)
    date_str = datetime.datetime.fromtimestamp(date_ts).strftime("%Y-%m-%d %H:%M") if date_ts else "Unknown"
    
    print(f"\n[{index}] From: {sender}")
    print(f"    Date: {date_str}")
    print(f"    Subject: {subject}")

def extract_tasks_from_email(email):
    """Extract tasks from an email using the task extraction module"""
    body = getattr(email, "body", "")
    subject = getattr(email, "subject", "")
    
    # Combine subject and body for better context
    full_content = f"Subject: {subject}\n\n{body}"
    
    # Extract metadata to help determine task responsibility
    metadata = {
        "subject": subject,
        "user_email": os.environ.get("NYLAS_USER_EMAIL", "")
    }
    
    # Extract sender information
    if hasattr(email, "from_") and email.from_:
        if isinstance(email.from_[0], dict):
            sender_name = email.from_[0].get("name", "")
            sender_email = email.from_[0].get("email", "")
            metadata["sender"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
        else:
            metadata["sender"] = email.from_[0]
    
    # Extract recipients information
    if hasattr(email, "to") and email.to:
        metadata["recipients"] = []
        for recipient in email.to:
            if isinstance(recipient, dict):
                name = recipient.get("name", "")
                email_addr = recipient.get("email", "")
                metadata["recipients"].append(f"{name} <{email_addr}>" if name else email_addr)
            else:
                metadata["recipients"].append(recipient)
    
    # Extract CC recipients
    if hasattr(email, "cc") and email.cc:
        metadata["cc"] = []
        for cc in email.cc:
            if isinstance(cc, dict):
                name = cc.get("name", "")
                email_addr = cc.get("email", "")
                metadata["cc"].append(f"{name} <{email_addr}>" if name else email_addr)
            else:
                metadata["cc"].append(cc)
    
    # Extract tasks using the imported function with metadata
    return generate(full_content, metadata)

def display_extracted_tasks(tasks: List[Task], email_index: int):
    """Display tasks extracted from an email"""
    if not tasks:
        print(f"No tasks found in email [{email_index}]")
        return
    
    print(f"\nExtracted {len(tasks)} task(s) from email [{email_index}]:")
    
    for i, task in enumerate(tasks, 1):
        print(f"\nTask {i}:")
        print(f"  Description: {task.description}")
        print(f"  Type: {task.task_type}")
        print(f"  Responsible: {task.responsible or 'Not specified'}")
        print(f"  Deadline: {task.deadline or 'Not specified'}")
        if task.dependencies:
            print(f"  Dependencies: {', '.join(task.dependencies)}")

def save_tasks_to_json(tasks: List[Task], filename="extracted_tasks.json"):
    """Save extracted tasks to a JSON file"""
    # Convert tasks to dictionaries
    tasks_dict = [task.dict() for task in tasks]
    
    # Load existing tasks if file exists
    existing_tasks = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                existing_tasks = json.load(f)
        except json.JSONDecodeError:
            existing_tasks = []
    
    # Append new tasks
    all_tasks = existing_tasks + tasks_dict
    
    # Save all tasks
    with open(filename, 'w') as f:
        json.dump(all_tasks, f, indent=2)
    
    print(f"Tasks saved to {filename}")

import time

def main():
    # Setup Nylas client
    nylas, grant_id = setup_nylas_client()
    
    if not grant_id:
        print("Error: NYLAS_GRANT_ID not found in environment variables")
        return
    
    # Fetch recent emails
    print("Fetching recent emails...")
    emails = fetch_recent_emails(nylas, grant_id)
    
    if not emails:
        print("No emails found")
        return
    
    print(f"\nFound {len(emails)} emails")
    
    all_extracted_tasks = []
    
    # Process emails
    for i, email in enumerate(emails):
        display_email_summary(email, i)
        
        # Ask if user wants to extract tasks from this email
        choice = input("\nExtract tasks from this email? (y/n/q to quit): ").lower()
        
        if choice == 'q':
            break
        
        if choice == 'y':
            print("Extracting tasks...")
            tasks = extract_tasks_from_email(email)
            display_extracted_tasks(tasks, i)
            
            if tasks:
                all_extracted_tasks.extend(tasks)
                
                # Ask if user wants to save tasks
                save_choice = input("Save these tasks? (y/n): ").lower()
                if save_choice == 'y':
                    save_tasks_to_json(tasks)
            
            # Add a small delay between API calls to prevent rate limiting
            if i < len(emails) - 1:
                print("Adding delay before processing next email to avoid rate limiting...")
                time.sleep(3)  # 3-second delay between emails
    
    # Summary
    if all_extracted_tasks:
        print(f"\nExtracted a total of {len(all_extracted_tasks)} tasks from emails")
    else:
        print("\nNo tasks were extracted")

if __name__ == "__main__":
    main()
