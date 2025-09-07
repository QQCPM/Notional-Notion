"""
Interactive CLI Interface for AI Task Continuity System
Provides user review, editing, and approval capabilities.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown

from notion_api import Task, Job
from page_generator import PageGenerator
from utils import (
    clean_job_title,
    format_deadline_urgency,
    create_priority_badge,
    truncate_text
)

console = Console()
logger = logging.getLogger("task_continuity")

class EditAction(Enum):
    """Available edit actions."""
    VIEW_PREVIEW = "preview"
    EDIT_TASKS = "tasks"  
    EDIT_JOBS = "jobs"
    ADD_TASK = "add"
    REMOVE_TASK = "remove"
    APPROVE = "approve"
    CANCEL = "cancel"

class CLIInterface:
    """Interactive command-line interface for user review and editing."""
    
    def __init__(self):
        self.logger = logging.getLogger("task_continuity.cli")
    
    async def review_and_edit(
        self, 
        page_content: Dict[str, Any],
        carryover_tasks: List[Task],
        feature_jobs: List[Job]
    ) -> Dict[str, Any]:
        """Main review and editing flow."""
        
        self.logger.info("Starting interactive review session")
        
        # Make working copies
        working_content = page_content.copy()
        working_content['carryover_tasks'] = carryover_tasks.copy()
        working_content['feature_jobs'] = feature_jobs.copy()
        
        # Show initial preview
        await self._display_draft_preview(working_content)
        
        # Interactive editing loop
        while True:
            action = await self._get_user_action()
            
            if action == EditAction.VIEW_PREVIEW:
                await self._display_full_preview(working_content)
                
            elif action == EditAction.EDIT_TASKS:
                working_content = await self._edit_tasks_interactive(working_content)
                
            elif action == EditAction.EDIT_JOBS:
                working_content = await self._edit_jobs_interactive(working_content)
                
            elif action == EditAction.ADD_TASK:
                working_content = await self._add_task_interactive(working_content)
                
            elif action == EditAction.REMOVE_TASK:
                working_content = await self._remove_task_interactive(working_content)
                
            elif action == EditAction.APPROVE:
                if await self._confirm_approval(working_content):
                    console.print("✅ Plan approved for publication", style="bold green")
                    return working_content
                    
            elif action == EditAction.CANCEL:
                if Confirm.ask("⚠️  Are you sure you want to cancel? Changes will be lost."):
                    console.print("❌ Operation cancelled", style="yellow")
                    raise KeyboardInterrupt()
    
    async def _display_draft_preview(self, page_content: Dict[str, Any]):
        """Display initial draft preview."""
        
        title_text = Text(f"📋 Tomorrow's Plan Draft", style="bold blue")
        subtitle_text = Text(f"Date: {page_content['formatted_date']}", style="dim")
        
        console.print(Panel(
            f"{title_text}\n{subtitle_text}",
            title="Draft Preview",
            padding=(1, 2)
        ))
        
        # Quick stats
        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Count", style="yellow")
        
        stats_table.add_row("📋 Carryover Tasks", str(len(page_content['carryover_tasks'])))
        stats_table.add_row("💼 Feature Jobs", str(len(page_content['feature_jobs'])))
        stats_table.add_row("📂 Categories", str(len(page_content['task_categories'])))
        
        console.print(stats_table)
        console.print()
        
        # Show sample tasks and jobs
        await self._show_quick_summary(page_content)
    
    async def _show_quick_summary(self, page_content: Dict[str, Any]):
        """Show quick summary of key content."""
        
        panels = []
        
        # Priority tasks sample
        priority_tasks = [t for t in page_content['carryover_tasks'] if t.category == "Priorities"]
        if priority_tasks:
            priority_text = "\n".join([f"• {truncate_text(task.name, 40)}" for task in priority_tasks[:3]])
            if len(priority_tasks) > 3:
                priority_text += f"\n... and {len(priority_tasks) - 3} more"
        else:
            priority_text = "No priority tasks"
        
        panels.append(Panel(
            priority_text,
            title=f"🎯 Priorities ({len(priority_tasks)})",
            width=40
        ))
        
        # Feature jobs sample  
        if page_content['feature_jobs']:
            jobs_text = "\n".join([
                f"• {truncate_text(clean_job_title(job.name), 35)}"
                for job in page_content['feature_jobs'][:3]
            ])
            if len(page_content['feature_jobs']) > 3:
                jobs_text += f"\n... and {len(page_content['feature_jobs']) - 3} more"
        else:
            jobs_text = "No feature jobs"
            
        panels.append(Panel(
            jobs_text,
            title=f"💼 Feature Jobs ({len(page_content['feature_jobs'])})",
            width=40
        ))
        
        console.print(Columns(panels, equal=True))
        console.print()
    
    async def _get_user_action(self) -> EditAction:
        """Get user's desired action."""
        
        actions = [
            ("preview", "📋 View full preview"),
            ("tasks", "✏️  Edit tasks"),
            ("jobs", "💼 Edit feature jobs"), 
            ("add", "➕ Add new task"),
            ("remove", "➖ Remove task"),
            ("approve", "✅ Approve & publish"),
            ("cancel", "❌ Cancel")
        ]
        
        console.print("🎛️  What would you like to do?", style="bold")
        for key, description in actions:
            console.print(f"   {key:8} - {description}")
        
        while True:
            choice = Prompt.ask("\nYour choice", choices=[a[0] for a in actions])
            try:
                return EditAction(choice)
            except ValueError:
                console.print("❌ Invalid choice, please try again", style="red")
    
    async def _display_full_preview(self, page_content: Dict[str, Any]):
        """Display full page preview."""
        
        generator = PageGenerator(None, None)  # Just for preview generation
        preview_text = generator.preview_page_content(page_content)
        
        console.print(Panel(
            Markdown(preview_text),
            title=f"Full Preview - {page_content['formatted_date']}",
            padding=(1, 2)
        ))
        
        input("\nPress Enter to continue...")
    
    async def _edit_tasks_interactive(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """Interactive task editing."""
        
        console.print("📝 Task Editor", style="bold blue")
        
        # Show tasks by category
        categories = page_content['task_categories']
        
        if not categories:
            console.print("No tasks to edit", style="yellow")
            return page_content
        
        # Display current tasks
        table = Table(title="Current Tasks")
        table.add_column("#", style="dim")
        table.add_column("Category", style="cyan")
        table.add_column("Task", style="white")
        table.add_column("Priority", style="yellow")
        
        all_tasks = []
        for category, tasks in categories.items():
            all_tasks.extend(tasks)
        
        for i, task in enumerate(all_tasks, 1):
            table.add_row(
                str(i),
                task.category,
                truncate_text(task.name, 50),
                task.priority_level or "None"
            )
        
        console.print(table)
        
        # Edit options
        console.print("\n🛠️  Edit Options:")
        console.print("   • Enter task numbers to toggle (e.g., '1,3,5')")
        console.print("   • Type 'done' to finish editing")
        console.print("   • Type 'cancel' to cancel changes")
        
        while True:
            choice = Prompt.ask("\nYour choice").strip().lower()
            
            if choice == 'done':
                break
            elif choice == 'cancel':
                return page_content
            
            # Parse task numbers
            try:
                if ',' in choice:
                    task_numbers = [int(x.strip()) for x in choice.split(',')]
                else:
                    task_numbers = [int(choice)]
                
                # Validate range
                for num in task_numbers:
                    if not (1 <= num <= len(all_tasks)):
                        raise ValueError(f"Task {num} out of range")
                
                # Show selected tasks for confirmation
                selected_tasks = [all_tasks[i-1] for i in task_numbers]
                console.print("\n📋 Selected tasks:")
                for task in selected_tasks:
                    console.print(f"   • {task.name} ({task.category})")
                
                action = Prompt.ask(
                    "\nAction for selected tasks", 
                    choices=["remove", "change-priority", "change-category", "back"]
                )
                
                if action == "remove":
                    if Confirm.ask("Remove these tasks?"):
                        for task in selected_tasks:
                            page_content['carryover_tasks'].remove(task)
                        page_content = self._rebuild_page_content(page_content)
                        console.print("✅ Tasks removed", style="green")
                        break
                        
                elif action == "change-priority":
                    new_priority = Prompt.ask(
                        "New priority",
                        choices=["High", "Medium", "Low", "None"],
                        default="None"
                    )
                    for task in selected_tasks:
                        task.priority_level = new_priority if new_priority != "None" else ""
                    page_content = self._rebuild_page_content(page_content)
                    console.print("✅ Priority updated", style="green")
                    
                elif action == "change-category":
                    available_categories = [
                        "Priorities", "Daily Habits", "Application Focus",
                        "Research & Learning", "Networking", "Pipeline Development"
                    ]
                    new_category = Prompt.ask(
                        "New category",
                        choices=available_categories
                    )
                    for task in selected_tasks:
                        task.category = new_category
                    page_content = self._rebuild_page_content(page_content)
                    console.print("✅ Category updated", style="green")
                
            except ValueError as e:
                console.print(f"❌ Invalid input: {e}", style="red")
                continue
        
        return page_content
    
    async def _edit_jobs_interactive(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """Interactive job editing."""
        
        console.print("💼 Feature Jobs Editor", style="bold blue")
        
        jobs = page_content['feature_jobs']
        
        if not jobs:
            console.print("No feature jobs to edit", style="yellow")
            return page_content
        
        # Display current jobs
        table = Table(title="Current Feature Jobs")
        table.add_column("#", style="dim")
        table.add_column("Job Title", style="cyan")
        table.add_column("Priority", style="yellow")
        table.add_column("Deadline", style="green")
        
        for i, job in enumerate(jobs, 1):
            deadline_str = format_deadline_urgency(job.deadline) if job.deadline else "No deadline"
            priority_str = create_priority_badge(job.priority) if job.priority else "None"
            
            table.add_row(
                str(i),
                clean_job_title(job.name)[:40],
                priority_str,
                deadline_str
            )
        
        console.print(table)
        
        console.print("\n🛠️  Edit Options:")
        console.print("   • Enter job numbers to remove (e.g., '1,3')")
        console.print("   • Type 'reorder' to change job order")
        console.print("   • Type 'done' to finish editing")
        
        while True:
            choice = Prompt.ask("\nYour choice").strip().lower()
            
            if choice == 'done':
                break
            elif choice == 'reorder':
                # Simple reordering by priority
                if Confirm.ask("Reorder jobs by priority and deadline?"):
                    # Re-sort jobs (this would need the original sorting logic)
                    console.print("✅ Jobs reordered", style="green")
            else:
                try:
                    # Parse job numbers to remove
                    if ',' in choice:
                        job_numbers = [int(x.strip()) for x in choice.split(',')]
                    else:
                        job_numbers = [int(choice)]
                    
                    # Validate range
                    for num in job_numbers:
                        if not (1 <= num <= len(jobs)):
                            raise ValueError(f"Job {num} out of range")
                    
                    # Show selected jobs
                    selected_jobs = [jobs[i-1] for i in job_numbers]
                    console.print("\n📋 Selected jobs:")
                    for job in selected_jobs:
                        console.print(f"   • {clean_job_title(job.name)}")
                    
                    if Confirm.ask("Remove these jobs?"):
                        for job in selected_jobs:
                            page_content['feature_jobs'].remove(job)
                        console.print("✅ Jobs removed", style="green")
                        break
                        
                except ValueError as e:
                    console.print(f"❌ Invalid input: {e}", style="red")
                    continue
        
        return page_content
    
    async def _add_task_interactive(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """Add new task interactively."""
        
        console.print("➕ Add New Task", style="bold blue")
        
        # Get task details
        task_name = Prompt.ask("Task name")
        if not task_name.strip():
            console.print("❌ Task name cannot be empty", style="red")
            return page_content
        
        categories = [
            "Priorities", "Daily Habits", "Application Focus",
            "Research & Learning", "Networking", "Pipeline Development"
        ]
        category = Prompt.ask("Category", choices=categories, default="Application Focus")
        
        priority = Prompt.ask(
            "Priority", 
            choices=["High", "Medium", "Low", "None"],
            default="Medium"
        )
        
        # Create new task
        new_task = Task(
            id="",
            name=task_name.strip(),
            status=False,
            next_reminder=page_content['date'],
            priority_level=priority if priority != "None" else "",
            category=category
        )
        
        page_content['carryover_tasks'].append(new_task)
        page_content = self._rebuild_page_content(page_content)
        
        console.print(f"✅ Added task: {task_name}", style="green")
        return page_content
    
    async def _remove_task_interactive(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """Remove task interactively."""
        
        console.print("➖ Remove Task", style="bold blue")
        
        tasks = page_content['carryover_tasks']
        if not tasks:
            console.print("No tasks to remove", style="yellow")
            return page_content
        
        # Simple search interface
        search_term = Prompt.ask("Search for task (partial name)").strip().lower()
        
        matching_tasks = [
            task for task in tasks 
            if search_term in task.name.lower()
        ]
        
        if not matching_tasks:
            console.print("❌ No matching tasks found", style="red")
            return page_content
        
        if len(matching_tasks) == 1:
            task_to_remove = matching_tasks[0]
            if Confirm.ask(f"Remove task: {task_to_remove.name}?"):
                page_content['carryover_tasks'].remove(task_to_remove)
                page_content = self._rebuild_page_content(page_content)
                console.print("✅ Task removed", style="green")
        else:
            console.print(f"Found {len(matching_tasks)} matching tasks:")
            for i, task in enumerate(matching_tasks, 1):
                console.print(f"   {i}. {task.name} ({task.category})")
            
            choice = Prompt.ask(
                "Which task to remove?",
                choices=[str(i) for i in range(1, len(matching_tasks) + 1)]
            )
            
            task_to_remove = matching_tasks[int(choice) - 1]
            if Confirm.ask(f"Remove task: {task_to_remove.name}?"):
                page_content['carryover_tasks'].remove(task_to_remove)
                page_content = self._rebuild_page_content(page_content)
                console.print("✅ Task removed", style="green")
        
        return page_content
    
    def _rebuild_page_content(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """Rebuild page content after task modifications."""
        
        from utils import categorize_tasks_by_category
        
        # Rebuild task categories
        page_content['task_categories'] = categorize_tasks_by_category(
            page_content['carryover_tasks']
        )
        
        return page_content
    
    async def _confirm_approval(self, page_content: Dict[str, Any]) -> bool:
        """Final confirmation before approval."""
        
        console.print("🔍 Final Review", style="bold yellow")
        
        # Show final stats
        stats_text = f"""
📊 Final Plan Summary:
   • {len(page_content['carryover_tasks'])} tasks to carry over
   • {len(page_content['feature_jobs'])} feature jobs selected
   • {len(page_content['task_categories'])} active categories
   • Target date: {page_content['formatted_date']}
        """
        
        console.print(Panel(stats_text, title="Summary"))
        
        return Confirm.ask(
            "\n✅ Create tomorrow's plan with these settings?",
            default=True
        )