#!/usr/bin/env python3
"""
Validation script for AI Task Continuity System
Tests configuration and system components without running the full workflow.
"""

import asyncio
import sys
from datetime import datetime, date
from typing import Dict, Any, List

from rich.console import Console  
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

async def test_configuration():
    """Test basic configuration loading."""
    
    console.print("🔧 Testing Configuration...", style="blue")
    
    try:
        from config import Config
        config = Config()
        
        # Display configuration summary
        table = Table(title="Configuration Summary")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="yellow")
        table.add_column("Status", style="green")
        
        table.add_row("API Key", f"{config.notion_api_key[:12]}...", "✅ Set" if config.notion_api_key else "❌ Missing")
        table.add_row("Plan AI DB", config.plan_ai_database_id[:16] + "...", "✅ Set")
        table.add_row("Job Tracker DB", config.job_tracker_database_id[:16] + "...", "✅ Set")  
        table.add_row("Parent Page", config.daily_planner_parent_id[:16] + "...", "✅ Set")
        table.add_row("Max Feature Jobs", str(config.max_feature_jobs), "✅ Set")
        
        console.print(table)
        console.print("✅ Configuration loaded successfully", style="green")
        return config
        
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        return None

async def test_notion_connection(config):
    """Test Notion API connection and permissions."""
    
    console.print("\n🔗 Testing Notion Connection...", style="blue")
    
    try:
        from notion_api import NotionClient
        notion = NotionClient(config.notion_api_key)
        
        # Test basic connection
        await notion.validate_connection()
        console.print("✅ Notion API connection successful", style="green")
        
        return notion
        
    except Exception as e:
        console.print(f"❌ Notion connection failed: {e}", style="red")
        return None

async def test_database_access(notion, config):
    """Test access to both required databases."""
    
    console.print("\n📊 Testing Database Access...", style="blue")
    
    results = {}
    
    # Test Plan AI database
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Testing Plan AI database...", total=None)
            
            items = await notion.get_database_items(config.plan_ai_database_id)
            results['plan_ai'] = {
                'success': True,
                'count': len(items),
                'sample_fields': list(items[0]['properties'].keys()) if items else []
            }
            console.print(f"✅ Plan AI database: {len(items)} items", style="green")
            
    except Exception as e:
        console.print(f"❌ Plan AI database error: {e}", style="red")
        results['plan_ai'] = {'success': False, 'error': str(e)}
    
    # Test Job Tracker database
    try:
        with Progress(
            SpinnerColumn(), 
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Testing Job Tracker database...", total=None)
            
            items = await notion.get_database_items(config.job_tracker_database_id)
            results['job_tracker'] = {
                'success': True,
                'count': len(items),
                'sample_fields': list(items[0]['properties'].keys()) if items else []
            }
            console.print(f"✅ Job Tracker database: {len(items)} items", style="green")
            
    except Exception as e:
        console.print(f"❌ Job Tracker database error: {e}", style="red")
        results['job_tracker'] = {'success': False, 'error': str(e)}
    
    return results

async def test_task_processing(notion, config):
    """Test task processing components."""
    
    console.print("\n⚡ Testing Task Processing...", style="blue")
    
    try:
        from task_processor import TaskProcessor
        processor = TaskProcessor(notion, config)
        
        # Test getting tasks for today
        today = date.today()
        uncompleted = await processor.get_uncompleted_tasks(today)
        console.print(f"✅ Found {len(uncompleted)} uncompleted tasks for today", style="green")
        
        # Test job filtering
        feature_jobs = await processor.get_feature_jobs()
        console.print(f"✅ Selected {len(feature_jobs)} feature jobs", style="green")
        
        # Test carryover logic (without creating actual entries)
        if uncompleted:
            tomorrow = today.replace(day=today.day + 1)  # Simple tomorrow calc
            carryover = processor.create_carryover_tasks(uncompleted[:3], tomorrow)  # Test with first 3
            console.print(f"✅ Carryover logic: {len(carryover)} tasks processed", style="green")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Task processing error: {e}", style="red")
        return False

async def test_page_generation(config):
    """Test page generation components."""
    
    console.print("\n📝 Testing Page Generation...", style="blue")
    
    try:
        from page_generator import PageGenerator
        from notion_api import Task, Job
        
        # Create mock data
        mock_tasks = [
            Task("", "Test Priority Task", False, date.today(), "High", "Priorities"),
            Task("", "Test Application Task", False, date.today(), "Medium", "Application Focus")
        ]
        
        mock_jobs = [
            Job("", "AI Research Scientist at OpenAI", date.today(), "High Prior", "https://example.com")
        ]
        
        generator = PageGenerator(None, config)  # No actual Notion client needed for structure test
        
        # Test content generation
        page_content = generator.generate_page_content(mock_tasks, mock_jobs, date.today())
        console.print(f"✅ Generated page with {len(page_content['blocks'])} blocks", style="green")
        
        # Test preview generation
        preview = generator.preview_page_content(page_content)
        console.print(f"✅ Generated preview ({len(preview.split())} words)", style="green")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Page generation error: {e}", style="red")
        return False

def display_validation_summary(results: Dict[str, bool]):
    """Display final validation summary."""
    
    console.print("\n📋 Validation Summary", style="bold blue")
    
    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Details", style="dim")
    
    status_emoji = {"config": "⚙️", "notion": "🔗", "databases": "📊", "processing": "⚡", "generation": "📝"}
    
    all_passed = True
    for component, passed in results.items():
        emoji = status_emoji.get(component, "🔍")
        status = "✅ Pass" if passed else "❌ Fail"
        details = "Ready for use" if passed else "Needs attention"
        
        table.add_row(f"{emoji} {component.title()}", status, details)
        if not passed:
            all_passed = False
    
    console.print(table)
    
    if all_passed:
        success_text = Text("🎉 All validations passed! System is ready to use.", style="bold green")
        console.print(Panel(success_text, title="Success", padding=(1, 2)))
        console.print("Run: python main.py", style="bold cyan")
    else:
        warning_text = Text("⚠️  Some validations failed. Please check configuration and permissions.", style="bold yellow")
        console.print(Panel(warning_text, title="Issues Found", padding=(1, 2)))
        console.print("Check .env file and Notion permissions", style="dim")

async def main():
    """Main validation flow."""
    
    # Welcome
    title = Text("🔍 AI Task Continuity System - Validation", style="bold blue")
    console.print(Panel(title, padding=(1, 2)))
    
    results = {}
    
    # Test configuration
    config = await test_configuration()
    results['config'] = config is not None
    
    if not config:
        console.print("\n❌ Cannot proceed without valid configuration", style="red")
        sys.exit(1)
    
    # Test Notion connection
    notion = await test_notion_connection(config)
    results['notion'] = notion is not None
    
    if notion:
        # Test database access
        db_results = await test_database_access(notion, config)
        results['databases'] = all(r.get('success', False) for r in db_results.values())
        
        # Test task processing
        results['processing'] = await test_task_processing(notion, config)
    else:
        results['databases'] = False
        results['processing'] = False
    
    # Test page generation (independent of Notion)
    results['generation'] = await test_page_generation(config)
    
    # Show summary
    display_validation_summary(results)
    
    return all(results.values())

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n⚠️  Validation cancelled", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Validation error: {e}", style="red")
        sys.exit(1)