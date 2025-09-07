"""
Robust Notion API client wrapper with rate limiting, error handling, and retry logic.
Designed specifically for the AI Task Continuity System.
"""

import asyncio
import time
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

import requests
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from utils import retry_with_exponential_backoff, format_date_for_notion

console = Console()

@dataclass
class Task:
    """Represents a task from the Plan AI database."""
    id: str
    name: str
    status: bool
    next_reminder: Optional[date]
    priority_level: str
    category: str
    
    @classmethod
    def from_notion_page(cls, page: Dict[str, Any]) -> 'Task':
        """Create Task from Notion page data."""
        props = page['properties']
        
        # Extract date from Next reminder
        next_reminder = None
        if props.get('Next reminder') and props['Next reminder'].get('date'):
            date_str = props['Next reminder']['date']['start']
            next_reminder = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        
        return cls(
            id=page['id'],
            name=props['Name']['title'][0]['plain_text'] if props['Name']['title'] else '',
            status=props.get('Status', {}).get('checkbox', False),
            next_reminder=next_reminder,
            priority_level=props.get('Priority Level', {}).get('select', {}).get('name', ''),
            category=props.get('Category', {}).get('select', {}).get('name', '')
        )

@dataclass
class Job:
    """Represents a job from the Job Tracker database."""
    id: str
    name: str
    deadline: Optional[date]
    priority: str
    application_link: Optional[str]
    
    @classmethod
    def from_notion_page(cls, page: Dict[str, Any]) -> 'Job':
        """Create Job from Notion page data."""
        props = page['properties']
        
        # Extract deadline
        deadline = None
        if props.get('Deadline') and props['Deadline'].get('date'):
            date_str = props['Deadline']['date']['start']
            deadline = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        
        # Extract application link
        app_link = None
        if props.get('Application Link') and props['Application Link'].get('url'):
            app_link = props['Application Link']['url']
        
        return cls(
            id=page['id'],
            name=props['Name']['title'][0]['plain_text'] if props['Name']['title'] else '',
            deadline=deadline,
            priority=props.get('Priority', {}).get('select', {}).get('name', ''),
            application_link=app_link
        )

class NotionClient:
    """Enhanced Notion API client with robust error handling and rate limiting."""
    
    def __init__(self, api_key: str, rate_limit_delay: float = 0.34):
        self.client = Client(auth=api_key)
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0.0
        
    async def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    @retry_with_exponential_backoff(max_retries=3)
    async def validate_connection(self) -> bool:
        """Validate Notion API connection and permissions."""
        try:
            await self._rate_limit()
            # Test connection by listing users
            response = self.client.users.list()
            console.print("🔗 Notion API connection validated", style="dim green")
            return True
        except Exception as e:
            console.print(f"❌ Notion API connection failed: {e}", style="red")
            raise
    
    @retry_with_exponential_backoff(max_retries=3)
    async def get_database_items(
        self, 
        database_id: str, 
        filters: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get all items from a Notion database with optional filtering and sorting."""
        
        await self._rate_limit()
        
        query_params = {}
        if filters:
            query_params['filter'] = filters
        if sorts:
            query_params['sorts'] = sorts
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"Querying database {database_id[:8]}...", total=None)
                
                response = self.client.databases.query(database_id, **query_params)
                results = response['results']
                
                # Handle pagination
                while response.get('has_more'):
                    await self._rate_limit()
                    response = self.client.databases.query(
                        database_id, 
                        start_cursor=response['next_cursor'],
                        **query_params
                    )
                    results.extend(response['results'])
                
                progress.update(task, completed=True)
                return results
                
        except APIResponseError as e:
            if e.status == 404:
                console.print(f"❌ Database not found: {database_id}", style="red")
                console.print("Check database ID and Notion integration permissions", style="yellow")
            elif e.status == 403:
                console.print(f"❌ No access to database: {database_id}", style="red")
                console.print("Grant integration access to this database in Notion", style="yellow")
            else:
                console.print(f"❌ API Error: {e.status} - {e.body}", style="red")
            raise
        except Exception as e:
            console.print(f"❌ Unexpected error querying database: {e}", style="red")
            raise
    
    async def get_tasks_by_date(self, database_id: str, target_date: date) -> List[Task]:
        """Get tasks scheduled for a specific date."""
        
        # Create date filter
        date_filter = {
            "property": "Next reminder",
            "date": {
                "equals": format_date_for_notion(target_date)
            }
        }
        
        pages = await self.get_database_items(database_id, filters=date_filter)
        return [Task.from_notion_page(page) for page in pages]
    
    async def get_uncompleted_tasks_by_date(self, database_id: str, target_date: date) -> List[Task]:
        """Get uncompleted tasks scheduled for a specific date."""
        
        # Compound filter: date matches AND status is false
        compound_filter = {
            "and": [
                {
                    "property": "Next reminder",
                    "date": {
                        "equals": format_date_for_notion(target_date)
                    }
                },
                {
                    "property": "Status",
                    "checkbox": {
                        "equals": False
                    }
                }
            ]
        }
        
        pages = await self.get_database_items(database_id, filters=compound_filter)
        return [Task.from_notion_page(page) for page in pages]
    
    async def get_all_jobs(self, database_id: str) -> List[Job]:
        """Get all jobs from the Job Tracker database."""
        
        # Sort by deadline (ascending) and priority
        sorts = [
            {
                "property": "Deadline",
                "direction": "ascending"
            },
            {
                "property": "Priority",
                "direction": "ascending"
            }
        ]
        
        pages = await self.get_database_items(database_id, sorts=sorts)
        return [Job.from_notion_page(page) for page in pages]
    
    @retry_with_exponential_backoff(max_retries=3)
    async def create_database_item(
        self, 
        database_id: str, 
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new item in a Notion database."""
        
        await self._rate_limit()
        
        try:
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            console.print(f"✓ Created database item: {properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}", style="dim green")
            return response
            
        except APIResponseError as e:
            console.print(f"❌ Failed to create database item: {e.status} - {e.body}", style="red")
            raise
        except Exception as e:
            console.print(f"❌ Unexpected error creating database item: {e}", style="red")
            raise
    
    @retry_with_exponential_backoff(max_retries=3)
    async def create_page(
        self, 
        parent_id: str, 
        title: str, 
        content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a new Notion page."""
        
        await self._rate_limit()
        
        try:
            response = self.client.pages.create(
                parent={"page_id": parent_id},
                properties={
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                },
                children=content
            )
            console.print(f"✓ Created page: {title}", style="green")
            return response
            
        except APIResponseError as e:
            console.print(f"❌ Failed to create page: {e.status} - {e.body}", style="red")
            raise
        except Exception as e:
            console.print(f"❌ Unexpected error creating page: {e}", style="red")
            raise
    
    @retry_with_exponential_backoff(max_retries=3)
    async def update_page(
        self, 
        page_id: str, 
        properties: Dict[str, Any] = None,
        content: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update an existing Notion page."""
        
        await self._rate_limit()
        
        try:
            # Update properties if provided
            if properties:
                response = self.client.pages.update(page_id, properties=properties)
                
            # Append content if provided
            if content:
                self.client.blocks.children.append(page_id, children=content)
                
            console.print("✓ Updated page successfully", style="dim green")
            return response if properties else {"success": True}
            
        except APIResponseError as e:
            console.print(f"❌ Failed to update page: {e.status} - {e.body}", style="red")
            raise
        except Exception as e:
            console.print(f"❌ Unexpected error updating page: {e}", style="red")
            raise

# Utility functions for creating Notion properties
def create_task_properties(
    name: str,
    status: bool = False,
    next_reminder: Optional[date] = None,
    priority_level: str = "",
    category: str = ""
) -> Dict[str, Any]:
    """Create properties dict for Plan AI task."""
    
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": name
                    }
                }
            ]
        },
        "Status": {
            "checkbox": status
        }
    }
    
    if next_reminder:
        properties["Next reminder"] = {
            "date": {
                "start": format_date_for_notion(next_reminder)
            }
        }
    
    if priority_level:
        properties["Priority Level"] = {
            "select": {
                "name": priority_level
            }
        }
    
    if category:
        properties["Category"] = {
            "select": {
                "name": category
            }
        }
    
    return properties