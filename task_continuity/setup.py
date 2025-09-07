#!/usr/bin/env python3
"""
Setup and validation script for AI Task Continuity System
Helps users install dependencies and validate their configuration.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

console = Console()

def check_python_version():
    """Check if Python version is compatible."""
    
    if sys.version_info < (3, 9):
        console.print("❌ Python 3.9 or higher is required", style="red")
        console.print(f"Current version: {sys.version}", style="dim")
        return False
    
    console.print(f"✅ Python version: {sys.version.split()[0]}", style="green")
    return True

def install_dependencies():
    """Install required Python packages."""
    
    console.print("📦 Installing dependencies...", style="blue")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        console.print("❌ requirements.txt not found", style="red")
        return False
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Installing packages...", total=None)
            
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ], capture_output=True, text=True, check=True)
            
            progress.update(task, completed=True)
        
        console.print("✅ Dependencies installed successfully", style="green")
        return True
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to install dependencies: {e}", style="red")
        console.print(f"Error output: {e.stderr}", style="dim red")
        return False

def create_env_file():
    """Guide user through creating .env file."""
    
    console.print("⚙️  Environment Configuration", style="blue")
    
    env_file = Path(".env")
    env_sample = Path(".env.sample")
    
    if env_file.exists():
        if not Confirm.ask("⚠️  .env file already exists. Overwrite?"):
            console.print("Keeping existing .env file", style="yellow")
            return True
    
    if not env_sample.exists():
        console.print("❌ .env.sample not found", style="red")
        return False
    
    # Copy sample to .env
    with open(env_sample, 'r') as f:
        sample_content = f.read()
    
    with open(env_file, 'w') as f:
        f.write(sample_content)
    
    console.print("✅ Created .env file from template", style="green")
    console.print("📝 Please edit .env with your Notion configuration", style="yellow")
    
    # Guide user through key settings
    console.print("\n🔑 Required Configuration:", style="bold")
    console.print("1. Get Notion API key: https://www.notion.so/my-integrations")
    console.print("2. Extract database IDs from Notion URLs")
    console.print("3. Grant integration access to your databases")
    
    if Confirm.ask("\nOpen .env file for editing now?"):
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(env_file)])
            elif sys.platform == "linux":
                subprocess.run(["xdg-open", str(env_file)])
            elif sys.platform == "win32":
                os.startfile(str(env_file))
        except Exception as e:
            console.print(f"⚠️  Couldn't open editor: {e}", style="yellow")
            console.print(f"Please manually edit: {env_file}", style="dim")
    
    return True

async def validate_configuration():
    """Validate the configuration and Notion connection."""
    
    console.print("🔍 Validating configuration...", style="blue")
    
    try:
        from config import Config
        
        console.print("✅ Configuration loaded", style="green")
        config = Config()
        
        # Test Notion connection
        console.print("🔗 Testing Notion API connection...", style="blue")
        
        from notion_api import NotionClient
        notion = NotionClient(config.notion_api_key)
        
        await notion.validate_connection()
        console.print("✅ Notion API connection successful", style="green")
        
        # Test database access
        console.print("📊 Testing database access...", style="blue")
        
        # Test Plan AI database
        try:
            tasks = await notion.get_database_items(
                config.plan_ai_database_id,
                filters=None
            )
            console.print(f"✅ Plan AI database accessible ({len(tasks)} items)", style="green")
        except Exception as e:
            console.print(f"❌ Plan AI database error: {e}", style="red")
            return False
        
        # Test Job Tracker database
        try:
            jobs = await notion.get_database_items(
                config.job_tracker_database_id,
                filters=None
            )
            console.print(f"✅ Job Tracker database accessible ({len(jobs)} items)", style="green")
        except Exception as e:
            console.print(f"❌ Job Tracker database error: {e}", style="red")
            return False
        
        console.print("🎉 Configuration validation complete!", style="bold green")
        return True
        
    except Exception as e:
        console.print(f"❌ Configuration validation failed: {e}", style="red")
        return False

def show_next_steps():
    """Show user what to do next."""
    
    next_steps = Text()
    next_steps.append("🎯 Next Steps:\n\n", style="bold blue")
    next_steps.append("1. Run the system: ", style="white")
    next_steps.append("python main.py\n", style="bold cyan")
    next_steps.append("2. Review the generated plan in terminal\n", style="white")
    next_steps.append("3. Make any edits needed\n", style="white")
    next_steps.append("4. Approve to create tomorrow's Notion page\n", style="white")
    next_steps.append("\n📚 Need help? Check README.md for detailed docs", style="dim")
    
    console.print(Panel(next_steps, title="Setup Complete!", padding=(1, 2)))

async def main():
    """Main setup flow."""
    
    # Welcome message
    title = Text("🚀 AI Task Continuity System - Setup", style="bold blue")
    console.print(Panel(title, padding=(1, 2)))
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if Confirm.ask("📦 Install required dependencies?", default=True):
        if not install_dependencies():
            sys.exit(1)
    
    # Create .env file
    if Confirm.ask("⚙️  Set up environment configuration?", default=True):
        if not create_env_file():
            sys.exit(1)
    
    # Validate configuration
    if Confirm.ask("🔍 Validate Notion configuration?", default=True):
        if await validate_configuration():
            show_next_steps()
        else:
            console.print("\n❌ Setup incomplete - please check your configuration", style="red")
            console.print("Edit .env file and run: python setup.py", style="yellow")
            sys.exit(1)
    else:
        console.print("\n⚠️  Skipped validation - make sure to configure .env manually", style="yellow")
        show_next_steps()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n⚠️  Setup cancelled", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Setup error: {e}", style="red")
        sys.exit(1)