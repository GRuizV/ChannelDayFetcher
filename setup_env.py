"""
Environment Setup Helper
------------------------
Helps users set up their .env file interactively.

Usage:
    python setup_env.py
"""

import os
from pathlib import Path


def setup_environment():
    """Interactive setup for .env file."""
    
    print("\n" + "="*60)
    print("🔧 Slack Channel Fetcher - Environment Setup")
    print("="*60 + "\n")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    # Check if .env already exists
    if env_file.exists():
        print("⚠️  .env file already exists!")
        overwrite = input("Do you want to overwrite it? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("❌ Setup cancelled. Existing .env file kept.")
            return
    
    # Check if example file exists
    if not env_example.exists():
        print("❌ env.example file not found!")
        print("Please make sure you're in the ChannelDayFetcher directory.")
        return
    
    # Get Slack token from user
    print("\n📝 Enter your Slack Bot Token:")
    print("   (Get it from: https://api.slack.com/apps → Your App → OAuth & Permissions)")
    print("   Token starts with: xoxb-")
    print()
    
    while True:
        token = input("SLACK_TOKEN: ").strip()
        
        if not token:
            print("❌ Token cannot be empty!")
            continue
        
        if not token.startswith("xoxb-"):
            print("⚠️  Warning: Token should start with 'xoxb-'")
            confirm = input("Continue anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
        
        break
    
    # Create .env file
    try:
        with open(env_file, "w") as f:
            f.write("# Slack Channel Fetcher - Environment Variables\n")
            f.write("# This file is gitignored - safe for your token\n\n")
            f.write(f"SLACK_TOKEN={token}\n")
        
        print("\n✅ .env file created successfully!")
        print(f"📁 Location: {env_file.absolute()}")
        print("\n🎉 Setup complete! You can now run:")
        print("   streamlit run ui.py")
        print("   or")
        print("   python cli.py")
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")


if __name__ == "__main__":
    try:
        setup_environment()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

