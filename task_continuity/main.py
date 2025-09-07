#!/usr/bin/env python3
"""
AI Task Continuity System - Main Entry Point
Automates the transition from today's incomplete tasks to tomorrow's organized plan.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from config import Config
from notion_api import NotionClient
from task_processor import TaskProcessor
from page_generator import PageGenerator
from cli_interface import CLIInterface
from utils import setup_logging, handle_errors

console = Console()

@handle_errors
async def main():
    """Main orchestration function for the Task Continuity System."""
    
    # Initialize logging
    logger = setup_logging()
    logger.info("Starting AI Task Continuity System")
    
    # Display welcome message
    welcome_text = Text("🚀 AI Task Continuity System", style="bold blue")
    console.print(Panel(welcome_text, title="Welcome", padding=(1, 2)))
    
    try:
        # Initialize configuration
        config = Config()
        console.print("✓ Configuration loaded", style="green")
        
        # Initialize Notion client
        notion = NotionClient(config.notion_api_key)
        await notion.validate_connection()
        console.print("✓ Notion API connection validated", style="green")
        
        # Initialize processors
        task_processor = TaskProcessor(notion, config)
        page_generator = PageGenerator(notion, config)
        cli = CLIInterface()
        
        # Get dates
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        console.print(f"📅 Processing tasks from {today} → {tomorrow}", style="yellow")
        
        # Step 1: Collect uncompleted tasks
        console.print("\n🔍 Scanning uncompleted tasks...", style="cyan")
        uncompleted_tasks = await task_processor.get_uncompleted_tasks(today)
        console.print(f"Found {len(uncompleted_tasks)} uncompleted tasks", style="green")
        
        # Step 2: Get and filter feature jobs
        console.print("\n💼 Analyzing job opportunities...", style="cyan")
        feature_jobs = await task_processor.get_feature_jobs()
        console.print(f"Selected {len(feature_jobs)} priority jobs", style="green")
        
        # Step 3: Create carryover tasks
        console.print("\n⚡ Processing task carryover...", style="cyan")
        carryover_tasks = task_processor.create_carryover_tasks(uncompleted_tasks, tomorrow)
        console.print(f"Prepared {len(carryover_tasks)} tasks for carryover", style="green")
        
        # Step 4: Generate tomorrow's page
        console.print("\n📝 Generating tomorrow's page...", style="cyan")
        page_content = page_generator.generate_page_content(carryover_tasks, feature_jobs, tomorrow)
        
        # Step 5: User review and approval
        console.print("\n👀 Review Phase", style="bold yellow")
        approved_content = await cli.review_and_edit(page_content, carryover_tasks, feature_jobs)
        
        # Step 6: Publish final version
        console.print("\n🚀 Publishing tomorrow's plan...", style="cyan")
        page_url = await page_generator.create_tomorrow_page(approved_content, tomorrow)
        await task_processor.create_database_entries(approved_content['carryover_tasks'])
        
        # Success message
        success_text = Text(f"✅ Tomorrow's plan ready!\n🔗 {page_url}", style="bold green")
        console.print(Panel(success_text, title="Success", padding=(1, 2)))
        
    except KeyboardInterrupt:
        console.print("\n⚠️  Operation cancelled by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        console.print(f"\n❌ Error: {e}", style="red")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())