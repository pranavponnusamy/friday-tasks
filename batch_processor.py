import os
import time
import datetime
from typing import List, Optional
from dotenv import load_dotenv
from nylas import Client

from task_extract import Task, generate
from email_task_integration import (
    setup_nylas_client, 
    fetch_recent_emails, 
    extract_tasks_from_email,
    save_tasks_to_json
)

def process_emails_in_batches(batch_size=2, delay_between_emails=5, max_emails=10):
    """
    Process emails in small batches with delays to avoid rate limiting
    
    Args:
        batch_size: Number of emails to process in each batch
        delay_between_emails: Delay in seconds between processing each email
        max_emails: Maximum number of emails to process in total
    """
    print(f"Starting batch processing with batch_size={batch_size}, delay={delay_between_emails}s")
    
    # Setup client
    nylas, grant_id = setup_nylas_client()
    if not grant_id:
        print("Error: NYLAS_GRANT_ID not found in environment variables")
        return
    
    # Fetch emails
    emails = fetch_recent_emails(nylas, grant_id, limit=max_emails)
    if not emails:
        print("No emails found to process")
        return
    
    print(f"Processing {len(emails)} emails in batches of {batch_size}")
    
    all_tasks = []
    batch_count = 0
    
    # Process in batches
    for i in range(0, len(emails), batch_size):
        batch = emails[i:i+batch_size]
        batch_count += 1
        print(f"\n--- Processing Batch {batch_count} ---")
        
        batch_tasks = []
        
        # Process each email in the batch
        for j, email in enumerate(batch):
            subject = getattr(email, "subject", "No Subject")
            sender = ""
            if hasattr(email, "from_") and email.from_:
                sender = email.from_[0].get("email", "") if isinstance(email.from_[0], dict) else email.from_[0]
                
            print(f"\nProcessing email from: {sender}")
            print(f"Subject: {subject}")
            
            # Extract tasks
            tasks = extract_tasks_from_email(email)
            
            if tasks:
                print(f"✅ Found {len(tasks)} tasks")
                batch_tasks.extend(tasks)
            else:
                print("❌ No tasks found")
            
            # Add delay between emails to avoid rate limiting
            if j < len(batch) - 1:
                print(f"Waiting {delay_between_emails} seconds before next email...")
                time.sleep(delay_between_emails)
        
        # Save batch results
        if batch_tasks:
            all_tasks.extend(batch_tasks)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tasks_batch_{batch_count}_{timestamp}.json"
            save_tasks_to_json(batch_tasks, filename)
        
        # Add longer delay between batches
        if i + batch_size < len(emails):
            batch_delay = delay_between_emails * 2
            print(f"\nCompleted batch {batch_count}. Waiting {batch_delay} seconds before next batch...")
            time.sleep(batch_delay)
    
    print(f"\n=== Batch Processing Complete ===")
    print(f"Processed {len(emails)} emails in {batch_count} batches")
    print(f"Found {len(all_tasks)} tasks in total")
    
    return all_tasks

if __name__ == "__main__":
    load_dotenv()
    process_emails_in_batches()
