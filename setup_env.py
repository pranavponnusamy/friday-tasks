import os
import sys
from dotenv import load_dotenv, set_key

def setup_environment():
    """Setup or update environment variables needed for the application"""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    
    # Create .env file if it doesn't exist
    if not os.path.exists(env_file):
        open(env_file, 'w').close()
    
    # Load existing environment
    load_dotenv(env_file)
    
    # Required variables
    required_vars = {
        'GEMINI_API_KEY': 'Your Google Gemini API key',
        'NYLAS_API_KEY': 'Your Nylas API key',
        'NYLAS_API_URI': 'Nylas API URI (default: https://api.nylas.com)',
        'NYLAS_GRANT_ID': 'Your Nylas grant ID',
        'NYLAS_USER_EMAIL': 'Your email address used with Nylas'
    }
    
    updated = False
    
    # Check each required variable
    for var, description in required_vars.items():
        if not os.environ.get(var):
            value = input(f"Enter {description}: ")
            if value:
                os.environ[var] = value
                set_key(env_file, var, value)
                updated = True
            else:
                print(f"Warning: {var} not set")
    
    if updated:
        print("\nEnvironment variables updated successfully")
    else:
        print("\nEnvironment already configured")

if __name__ == "__main__":
    setup_environment()
    
    # Test connection to services
    print("\nTesting connections:")
    
    # Test Gemini API
    try:
        from google import genai
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        model = client.get_model("gemini-2.0-flash")
        print("✅ Gemini API connection successful")
    except Exception as e:
        print(f"❌ Gemini API connection failed: {str(e)}")
    
    # Test Nylas API
    try:
        from nylas import Client
        nylas = Client(
            os.environ.get('NYLAS_API_KEY'),
            os.environ.get('NYLAS_API_URI')
        )
        grant_id = os.environ.get("NYLAS_GRANT_ID")
        nylas.messages.list(grant_id, query_params={"limit": 1})
        print("✅ Nylas API connection successful")
    except Exception as e:
        print(f"❌ Nylas API connection failed: {str(e)}")
    
    print("\nSetup complete!")
