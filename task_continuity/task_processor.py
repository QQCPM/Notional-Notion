"""
Task Processing Logic for AI Task Continuity System
Handles carryover rules, job filtering, and intelligent task selection.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import Config
from notion_api import NotionClient, Task, Job, create_task_properties
from utils import (
    format_date_for_display,
    get_days_until_deadline,
    format_deadline_urgency,
    clean_job_title,
    categorize_tasks_by_category,
    create_priority_badge
)

console = Console()
logger = logging.getLogger("task_continuity")

@dataclass
class ProcessedJob:
    """Enhanced Job data with processing metadata."""
    job: Job
    category_priority: int
    priority_score: int  
    deadline_urgency: int
    total_score: int
    
    @classmethod
    def from_job(cls, job: Job, config: Config) -> 'ProcessedJob':
        """Create ProcessedJob with scoring."""
        category_priority = config.get_job_category_priority(job.name)
        priority_score = config.get_priority_level_score(job.priority)
        
        # Calculate deadline urgency (sooner = lower score = higher priority)
        days_until = get_days_until_deadline(job.deadline)
        if days_until is None:
            deadline_urgency = 100  # No deadline = lowest urgency
        elif days_until < 0:
            deadline_urgency = 0  # Overdue = highest urgency
        elif days_until <= 1:
            deadline_urgency = 1  # Due today/tomorrow
        elif days_until <= 3:
            deadline_urgency = 2  # Due within 3 days
        elif days_until <= 7:
            deadline_urgency = 3  # Due within a week
        else:
            deadline_urgency = 4  # Due later
        
        # Total score (lower = higher priority)
        total_score = category_priority + priority_score + deadline_urgency
        
        return cls(
            job=job,
            category_priority=category_priority,
            priority_score=priority_score,
            deadline_urgency=deadline_urgency,
            total_score=total_score
        )

class TaskProcessor:
    """Core logic processor for task continuity and job selection."""
    
    def __init__(self, notion_client: NotionClient, config: Config):
        self.notion = notion_client
        self.config = config
        self.logger = logging.getLogger("task_continuity.processor")
    
    async def get_uncompleted_tasks(self, target_date: date) -> List[Task]:
        """Get all uncompleted tasks scheduled for the target date."""
        
        self.logger.info(f"Fetching uncompleted tasks for {target_date}")
        
        try:
            tasks = await self.notion.get_uncompleted_tasks_by_date(
                self.config.plan_ai_database_id,
                target_date
            )
            
            # Log summary
            if tasks:
                categories = categorize_tasks_by_category(tasks)
                self.logger.info(f"Found {len(tasks)} uncompleted tasks across {len(categories)} categories")
                
                # Display breakdown
                table = Table(title=f"Uncompleted Tasks - {format_date_for_display(target_date)}")
                table.add_column("Category", style="cyan")
                table.add_column("Count", style="yellow")
                table.add_column("Priority Breakdown", style="green")
                
                for category, category_tasks in categories.items():
                    priority_counts = {}
                    for task in category_tasks:
                        priority = task.priority_level or "None"
                        priority_counts[priority] = priority_counts.get(priority, 0) + 1
                    
                    priority_breakdown = ", ".join([f"{p}: {c}" for p, c in priority_counts.items()])
                    table.add_row(category, str(len(category_tasks)), priority_breakdown)
                
                console.print(table)
            else:
                console.print("🎉 No uncompleted tasks found - great job!", style="green")
            
            return tasks
            
        except Exception as e:
            self.logger.error(f"Failed to fetch uncompleted tasks: {e}")
            console.print(f"❌ Failed to fetch uncompleted tasks: {e}", style="red")
            raise
    
    async def get_feature_jobs(self) -> List[Job]:
        """Get and intelligently filter jobs for Feature Jobs section."""
        
        self.logger.info("Fetching and filtering jobs for feature selection")
        
        try:
            # Get all jobs
            all_jobs = await self.notion.get_all_jobs(self.config.job_tracker_database_id)
            
            if not all_jobs:
                console.print("⚠️  No jobs found in Job Tracker database", style="yellow")
                return []
            
            # Filter for AI/Research roles
            feature_candidates = []
            
            for job in all_jobs:
                # Check if job matches any feature keywords
                if any(keyword.lower() in job.name.lower() 
                       for keyword in self.config.all_job_keywords):
                    processed_job = ProcessedJob.from_job(job, self.config)
                    feature_candidates.append(processed_job)
            
            if not feature_candidates:
                console.print("⚠️  No AI/Research jobs found matching criteria", style="yellow")
                return []
            
            # Sort by total score (lower score = higher priority)
            feature_candidates.sort(key=lambda x: x.total_score)
            
            # Select top jobs
            selected = feature_candidates[:self.config.max_feature_jobs]
            selected_jobs = [pj.job for pj in selected]
            
            # Display selection results
            self.logger.info(f"Selected {len(selected_jobs)} feature jobs from {len(feature_candidates)} candidates")
            
            self._display_job_selection_table(feature_candidates, selected)
            
            return selected_jobs
            
        except Exception as e:
            self.logger.error(f"Failed to get feature jobs: {e}")
            console.print(f"❌ Failed to get feature jobs: {e}", style="red")
            raise
    
    def _display_job_selection_table(
        self, 
        candidates: List[ProcessedJob], 
        selected: List[ProcessedJob]
    ):
        """Display job selection results in a formatted table."""
        
        table = Table(title="Job Selection Analysis")
        table.add_column("Job Title", style="cyan", max_width=30)
        table.add_column("Category", style="blue")
        table.add_column("Priority", style="yellow")
        table.add_column("Deadline", style="green")
        table.add_column("Score", style="red")
        table.add_column("Selected", style="bold")
        
        for pj in candidates[:10]:  # Show top 10 candidates
            job = pj.job
            deadline_str = format_deadline_urgency(job.deadline)
            
            # Determine category based on title
            category = "Other"
            if pj.category_priority == 1:
                category = "Research"
            elif pj.category_priority == 2:
                category = "AI/ML"
            elif pj.category_priority == 3:
                category = "Internship"
            elif pj.category_priority == 4:
                category = "Engineer"
            
            selected_mark = "✅" if pj in selected else ""
            
            table.add_row(
                clean_job_title(job.name),
                category,
                create_priority_badge(job.priority),
                deadline_str,
                str(pj.total_score),
                selected_mark
            )
        
        console.print(table)
    
    def create_carryover_tasks(self, tasks: List[Task], new_date: date) -> List[Task]:
        """Create carryover tasks for tomorrow, excluding Schedule items."""
        
        self.logger.info(f"Processing {len(tasks)} tasks for carryover to {new_date}")
        
        carryover_tasks = []
        excluded_count = 0
        
        for task in tasks:
            # CRITICAL: Exclude Schedule category items (they don't carry over)
            if task.category == "Schedule":
                excluded_count += 1
                self.logger.debug(f"Excluding Schedule item: {task.name}")
                continue
            
            # Create new task with tomorrow's date
            carryover_task = Task(
                id="",  # Will be assigned when created in Notion
                name=task.name,
                status=False,  # Fresh start - reset to uncompleted
                next_reminder=new_date,
                priority_level=task.priority_level,
                category=task.category
            )
            
            carryover_tasks.append(carryover_task)
        
        # Log summary
        carried_over = len(carryover_tasks)
        console.print(f"✓ {carried_over} tasks prepared for carryover, {excluded_count} schedule items excluded", style="green")
        
        if carryover_tasks:
            # Display carryover summary by category
            categories = categorize_tasks_by_category(carryover_tasks)
            
            table = Table(title=f"Carryover Tasks - {format_date_for_display(new_date)}")
            table.add_column("Category", style="cyan")
            table.add_column("Tasks", style="yellow")
            table.add_column("Sample Tasks", style="dim", max_width=40)
            
            for category, category_tasks in categories.items():
                sample_tasks = [task.name for task in category_tasks[:2]]
                sample_text = ", ".join(sample_tasks)
                if len(category_tasks) > 2:
                    sample_text += f" ... (+{len(category_tasks) - 2} more)"
                
                table.add_row(
                    category,
                    str(len(category_tasks)),
                    sample_text
                )
            
            console.print(table)
        
        return carryover_tasks
    
    async def create_database_entries(self, carryover_tasks: List[Task]) -> List[str]:
        """Create database entries for carryover tasks in Notion."""
        
        if not carryover_tasks:
            console.print("No carryover tasks to create", style="dim")
            return []
        
        self.logger.info(f"Creating {len(carryover_tasks)} database entries")
        created_ids = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating database entries...", total=len(carryover_tasks))
            
            for carryover_task in carryover_tasks:
                try:
                    # Create properties for the task
                    properties = create_task_properties(
                        name=carryover_task.name,
                        status=carryover_task.status,
                        next_reminder=carryover_task.next_reminder,
                        priority_level=carryover_task.priority_level,
                        category=carryover_task.category
                    )
                    
                    # Create in Notion
                    response = await self.notion.create_database_item(
                        self.config.plan_ai_database_id,
                        properties
                    )
                    
                    created_ids.append(response['id'])
                    progress.advance(task, 1)
                    
                except Exception as e:
                    self.logger.error(f"Failed to create task '{carryover_task.name}': {e}")
                    console.print(f"⚠️  Failed to create task: {carryover_task.name}", style="yellow")
                    continue
        
        console.print(f"✅ Created {len(created_ids)} database entries", style="green")
        return created_ids
    
    def analyze_task_patterns(self, tasks: List[Task]) -> Dict[str, Any]:
        """Analyze patterns in uncompleted tasks for insights."""
        
        if not tasks:
            return {"total": 0, "insights": []}
        
        categories = categorize_tasks_by_category(tasks)
        priority_distribution = {}
        
        for task in tasks:
            priority = task.priority_level or "No Priority"
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        insights = []
        
        # Category insights
        if len(categories) > 3:
            insights.append(f"Tasks span {len(categories)} categories - consider focusing")
        
        max_category = max(categories.items(), key=lambda x: len(x[1]))
        if len(max_category[1]) > len(tasks) * 0.4:
            insights.append(f"Heavy focus on {max_category[0]} ({len(max_category[1])} tasks)")
        
        # Priority insights
        high_priority = priority_distribution.get("High", 0)
        if high_priority > 5:
            insights.append(f"{high_priority} high-priority tasks - review priorities")
        
        no_priority = priority_distribution.get("No Priority", 0)
        if no_priority > 3:
            insights.append(f"{no_priority} tasks lack priority - consider prioritizing")
        
        return {
            "total": len(tasks),
            "categories": dict(categories),
            "priorities": priority_distribution,
            "insights": insights
        }

    def get_task_summary_stats(self, tasks: List[Task]) -> Dict[str, int]:
        """Get summary statistics for tasks."""
        
        stats = {
            "total": len(tasks),
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
            "no_priority": 0,
            "by_category": {}
        }
        
        for task in tasks:
            # Count by priority
            priority = task.priority_level or "No Priority"
            if priority == "High":
                stats["high_priority"] += 1
            elif priority == "Medium":
                stats["medium_priority"] += 1
            elif priority == "Low":
                stats["low_priority"] += 1
            else:
                stats["no_priority"] += 1
            
            # Count by category
            category = task.category or "Uncategorized"
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        return stats