"""
Page Generation System for AI Task Continuity System
Creates structured Notion pages using templates and dynamic content.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import Config
from notion_api import NotionClient, Task, Job
from utils import (
    format_date_for_display,
    format_page_title,
    format_deadline_urgency,
    clean_job_title,
    categorize_tasks_by_category,
    create_checkbox_markdown,
    create_priority_badge,
    NOTION_BLOCKS
)

console = Console()
logger = logging.getLogger("task_continuity")

class PageGenerator:
    """Generates Notion pages using templates and dynamic content."""
    
    def __init__(self, notion_client: NotionClient, config: Config):
        self.notion = notion_client
        self.config = config
        self.logger = logging.getLogger("task_continuity.generator")
        self.template = self._load_template()
    
    def _load_template(self) -> Dict[str, Any]:
        """Load the daily page template."""
        template_path = Path(__file__).parent / "templates" / "daily_page.json"
        
        try:
            with open(template_path, 'r') as f:
                template = json.load(f)
            self.logger.info(f"Loaded template version {template.get('template_version', 'unknown')}")
            return template
        except Exception as e:
            self.logger.error(f"Failed to load template: {e}")
            raise
    
    def generate_page_content(
        self, 
        carryover_tasks: List[Task], 
        feature_jobs: List[Job], 
        target_date: date
    ) -> Dict[str, Any]:
        """Generate complete page content structure."""
        
        self.logger.info(f"Generating page content for {target_date}")
        
        # Organize tasks by category
        task_categories = categorize_tasks_by_category(carryover_tasks)
        
        # Create the complete page structure
        page_content = {
            "title": format_page_title(target_date),
            "date": target_date,
            "formatted_date": format_date_for_display(target_date),
            "carryover_tasks": carryover_tasks,
            "feature_jobs": feature_jobs,
            "task_categories": task_categories,
            "blocks": self._generate_notion_blocks(task_categories, feature_jobs, target_date)
        }
        
        # Log generation summary
        console.print(f"📝 Generated page content:", style="blue")
        console.print(f"   • {len(carryover_tasks)} carryover tasks", style="dim")
        console.print(f"   • {len(feature_jobs)} feature jobs", style="dim") 
        console.print(f"   • {len(task_categories)} task categories", style="dim")
        console.print(f"   • {len(page_content['blocks'])} content blocks", style="dim")
        
        return page_content
    
    def _generate_notion_blocks(
        self, 
        task_categories: Dict[str, List[Task]], 
        feature_jobs: List[Job], 
        target_date: date
    ) -> List[Dict[str, Any]]:
        """Generate all Notion blocks for the page."""
        
        blocks = []
        
        # Main content in two columns
        left_column_blocks = self._create_left_column_blocks(task_categories, feature_jobs)
        right_column_blocks = self._create_right_column_blocks(task_categories)
        
        # Create column layout
        column_list = {
            "object": "block",
            "type": "column_list",
            "column_list": {
                "children": [
                    {
                        "object": "block",
                        "type": "column",
                        "column": {
                            "children": left_column_blocks
                        }
                    },
                    {
                        "object": "block", 
                        "type": "column",
                        "column": {
                            "children": right_column_blocks
                        }
                    }
                ]
            }
        }
        
        blocks.append(column_list)
        
        # Add divider
        blocks.append(NOTION_BLOCKS["divider"])
        
        # Add embedded databases
        blocks.extend(self._create_database_blocks())
        
        return blocks
    
    def _create_left_column_blocks(
        self, 
        task_categories: Dict[str, List[Task]], 
        feature_jobs: List[Job]
    ) -> List[Dict[str, Any]]:
        """Create blocks for the left column."""
        
        blocks = []
        
        # Priorities callout
        priorities_tasks = task_categories.get("Priorities", [])
        priorities_content = self._format_tasks_as_checkboxes(priorities_tasks)
        if not priorities_content:
            priorities_content = "No priority tasks for today"
        
        blocks.append(self._create_callout_block(
            "🎯", "Priorities", priorities_content
        ))
        
        # Daily Habits callout
        habits_tasks = task_categories.get("Daily Habits", [])
        habits_content = self._format_tasks_as_checkboxes(habits_tasks)
        if not habits_content:
            habits_content = "No daily habits defined"
            
        blocks.append(self._create_callout_block(
            "🔄", "Daily Habits", habits_content
        ))
        
        # Strategic Notes callout (empty for user input)
        blocks.append(self._create_callout_block(
            "📝", "Strategic Notes", "Key insights and strategic thinking for today..."
        ))
        
        # Feature Jobs callout
        jobs_content = self._format_feature_jobs(feature_jobs)
        if not jobs_content:
            jobs_content = "No priority jobs selected today"
            
        blocks.append(self._create_callout_block(
            "💼", "Feature Jobs", jobs_content
        ))
        
        return blocks
    
    def _create_right_column_blocks(
        self, 
        task_categories: Dict[str, List[Task]]
    ) -> List[Dict[str, Any]]:
        """Create blocks for the right column."""
        
        blocks = []
        
        # Schedule callout (empty - user fills in daily)
        blocks.append(self._create_callout_block(
            "⏰", "Schedule", "Day-specific time blocks (don't carry over)"
        ))
        
        # Tasks heading
        blocks.append(NOTION_BLOCKS["heading_2"]("Tasks"))
        
        # Task categories
        categories_to_show = [
            ("Application Focus", "📋"),
            ("Research & Learning", "📚"), 
            ("Networking", "🤝"),
            ("Pipeline Development", "🔧")
        ]
        
        for category_name, icon in categories_to_show:
            category_tasks = task_categories.get(category_name, [])
            content = self._format_tasks_as_checkboxes(category_tasks)
            if not content:
                content = f"No {category_name.lower()} tasks for today"
            
            blocks.append(self._create_callout_block(
                icon, category_name, content
            ))
        
        # Add any uncategorized tasks
        uncategorized = []
        for category, tasks in task_categories.items():
            if category not in ["Priorities", "Daily Habits", "Application Focus", 
                               "Research & Learning", "Networking", "Pipeline Development", 
                               "Schedule"]:
                uncategorized.extend(tasks)
        
        if uncategorized:
            content = self._format_tasks_as_checkboxes(uncategorized)
            blocks.append(self._create_callout_block(
                "❓", "Other Tasks", content
            ))
        
        return blocks
    
    def _create_database_blocks(self) -> List[Dict[str, Any]]:
        """Create embedded database blocks."""
        
        blocks = []
        
        # Plan AI Database
        blocks.append({
            "object": "block",
            "type": "child_database",
            "child_database": {
                "title": "Plan AI - Active Tasks Only",
                "database_id": self.config.plan_ai_database_id
            }
        })
        
        # Job Tracker Database  
        blocks.append({
            "object": "block",
            "type": "child_database",
            "child_database": {
                "title": "Job Tracker", 
                "database_id": self.config.job_tracker_database_id
            }
        })
        
        return blocks
    
    def _create_callout_block(self, icon: str, title: str, content: str) -> Dict[str, Any]:
        """Create a callout block with title and content."""
        
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"{title}\n\n{content}"
                        }
                    }
                ],
                "icon": {
                    "emoji": icon
                },
                "color": "default"
            }
        }
    
    def _format_tasks_as_checkboxes(self, tasks: List[Task]) -> str:
        """Format tasks as checkbox list."""
        
        if not tasks:
            return ""
        
        formatted_tasks = []
        for task in tasks:
            checkbox = create_checkbox_markdown(task.name, task.status)
            formatted_tasks.append(checkbox)
        
        return "\n".join(formatted_tasks)
    
    def _format_feature_jobs(self, jobs: List[Job]) -> str:
        """Format feature jobs with deadline and priority info."""
        
        if not jobs:
            return ""
        
        formatted_jobs = []
        for job in jobs:
            # Clean job title
            clean_title = clean_job_title(job.name)
            
            # Format deadline
            deadline_str = "No deadline"
            if job.deadline:
                deadline_str = format_deadline_urgency(job.deadline)
            
            # Format priority badge
            priority_str = create_priority_badge(job.priority) if job.priority else ""
            
            # Create checkbox format
            job_text = f"{clean_title}"
            if deadline_str != "No deadline":
                job_text += f" (Deadline: {deadline_str})"
            if priority_str:
                job_text += f" [{priority_str}]"
            
            checkbox = create_checkbox_markdown(job_text, False)
            formatted_jobs.append(checkbox)
        
        return "\n".join(formatted_jobs)
    
    async def create_tomorrow_page(
        self, 
        page_content: Dict[str, Any], 
        target_date: date
    ) -> str:
        """Create the tomorrow's page in Notion and return URL."""
        
        self.logger.info(f"Creating Notion page for {target_date}")
        
        try:
            # Create the page
            response = await self.notion.create_page(
                parent_id=self.config.daily_planner_parent_id,
                title=page_content["title"],
                content=page_content["blocks"]
            )
            
            # Extract page URL
            page_id = response["id"]
            page_url = f"https://notion.so/{page_id.replace('-', '')}"
            
            self.logger.info(f"Successfully created page: {page_url}")
            return page_url
            
        except Exception as e:
            self.logger.error(f"Failed to create page: {e}")
            console.print(f"❌ Failed to create Notion page: {e}", style="red")
            raise
    
    def preview_page_content(self, page_content: Dict[str, Any]) -> str:
        """Generate a text preview of the page content for review."""
        
        preview_lines = []
        preview_lines.append(f"# {page_content['title']}")
        preview_lines.append("")
        
        # Left column preview
        preview_lines.append("## Left Column")
        preview_lines.append("")
        
        # Priorities
        priorities = [t for t in page_content['carryover_tasks'] if t.category == "Priorities"]
        preview_lines.append("### 🎯 Priorities")
        if priorities:
            for task in priorities:
                preview_lines.append(f"- ☐ {task.name}")
        else:
            preview_lines.append("- No priority tasks")
        preview_lines.append("")
        
        # Daily Habits
        habits = [t for t in page_content['carryover_tasks'] if t.category == "Daily Habits"]
        preview_lines.append("### 🔄 Daily Habits")
        if habits:
            for task in habits:
                preview_lines.append(f"- ☐ {task.name}")
        else:
            preview_lines.append("- No daily habits")
        preview_lines.append("")
        
        # Feature Jobs
        preview_lines.append("### 💼 Feature Jobs")
        if page_content['feature_jobs']:
            for job in page_content['feature_jobs']:
                clean_title = clean_job_title(job.name)
                deadline = format_deadline_urgency(job.deadline) if job.deadline else "No deadline"
                priority = create_priority_badge(job.priority) if job.priority else ""
                
                job_line = f"- ☐ {clean_title}"
                if deadline != "No deadline":
                    job_line += f" (Deadline: {deadline})"
                if priority:
                    job_line += f" [{priority}]"
                preview_lines.append(job_line)
        else:
            preview_lines.append("- No feature jobs selected")
        preview_lines.append("")
        
        # Right column preview
        preview_lines.append("## Right Column")
        preview_lines.append("")
        
        # Task categories
        categories = [
            ("Application Focus", "📋"),
            ("Research & Learning", "📚"),
            ("Networking", "🤝"), 
            ("Pipeline Development", "🔧")
        ]
        
        for category_name, icon in categories:
            preview_lines.append(f"### {icon} {category_name}")
            category_tasks = page_content['task_categories'].get(category_name, [])
            if category_tasks:
                for task in category_tasks:
                    preview_lines.append(f"- ☐ {task.name}")
            else:
                preview_lines.append(f"- No {category_name.lower()} tasks")
            preview_lines.append("")
        
        # Summary stats
        preview_lines.append("## Summary")
        preview_lines.append(f"- Total carryover tasks: {len(page_content['carryover_tasks'])}")
        preview_lines.append(f"- Feature jobs: {len(page_content['feature_jobs'])}")
        preview_lines.append(f"- Task categories: {len(page_content['task_categories'])}")
        
        return "\n".join(preview_lines)