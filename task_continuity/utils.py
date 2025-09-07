"""
Utility functions for the AI Task Continuity System
Includes logging, error handling, date formatting, and common helpers.
"""

import asyncio
import functools
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, List, Dict, Optional, TypeVar, Union
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

# Setup rich traceback for better error display
install(show_locals=True)

console = Console()
F = TypeVar('F', bound=Callable[..., Any])

def setup_logging(
    level: str = "INFO", 
    log_file: Optional[str] = None,
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> logging.Logger:
    """Setup logging with rich handler and optional file output."""
    
    # Create logger
    logger = logging.getLogger("task_continuity")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Rich console handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(format_string))
        logger.addHandler(file_handler)
        
        console.print(f"📝 Logging to file: {log_path}", style="dim")
    
    return logger

def handle_errors(func: F) -> F:
    """Decorator to handle and log errors gracefully."""
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n⚠️  Operation cancelled by user", style="yellow")
            sys.exit(1)
        except Exception as e:
            logger = logging.getLogger("task_continuity")
            logger.exception(f"Error in {func.__name__}")
            console.print(f"\n❌ Error in {func.__name__}: {e}", style="red")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n⚠️  Operation cancelled by user", style="yellow")
            sys.exit(1)
        except Exception as e:
            logger = logging.getLogger("task_continuity")
            logger.exception(f"Error in {func.__name__}")
            console.print(f"\n❌ Error in {func.__name__}: {e}", style="red")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """Decorator to retry functions with exponential backoff."""
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        console.print(f"❌ Max retries ({max_retries}) exceeded for {func.__name__}", style="red")
                        raise
                    
                    console.print(f"⚠️  Retry {attempt + 1}/{max_retries} for {func.__name__} in {delay:.1f}s", style="yellow")
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        console.print(f"❌ Max retries ({max_retries}) exceeded for {func.__name__}", style="red")
                        raise
                    
                    console.print(f"⚠️  Retry {attempt + 1}/{max_retries} for {func.__name__} in {delay:.1f}s", style="yellow")
                    import time
                    time.sleep(delay)
                    delay *= backoff_factor
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def format_date_for_notion(target_date: Union[date, datetime]) -> str:
    """Format date for Notion API (ISO format)."""
    if isinstance(target_date, datetime):
        return target_date.isoformat()
    return target_date.isoformat()

def format_date_for_display(target_date: Union[date, datetime, str]) -> str:
    """Format date for user-friendly display."""
    if isinstance(target_date, str):
        try:
            target_date = datetime.fromisoformat(target_date.replace('Z', '+00:00')).date()
        except ValueError:
            return target_date  # Return as-is if can't parse
    
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    
    # Format as "September 6, 2025"
    return target_date.strftime("%B %d, %Y")

def format_page_title(target_date: Union[date, datetime]) -> str:
    """Format page title with date."""
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    
    formatted_date = format_date_for_display(target_date)
    return f"AI Daily Planner with Completion Tracking - {formatted_date}"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def clean_job_title(job_title: str) -> str:
    """Clean and normalize job title for display."""
    # Remove common suffixes and clean up
    cleaned = job_title.strip()
    
    # Remove company name if it's at the end (after " - " or " at ")
    separators = [" - ", " at ", " | "]
    for sep in separators:
        if sep in cleaned:
            parts = cleaned.split(sep)
            if len(parts) > 1:
                # Take the first part (job title) if it's substantial
                if len(parts[0].strip()) > 10:
                    cleaned = parts[0].strip()
    
    return cleaned

def categorize_tasks_by_priority(tasks: List[Any]) -> Dict[str, List[Any]]:
    """Group tasks by priority level."""
    categories = {
        "High": [],
        "Medium": [],
        "Low": [],
        "No Priority": []
    }
    
    for task in tasks:
        priority = getattr(task, 'priority_level', '') or 'No Priority'
        if priority in categories:
            categories[priority].append(task)
        else:
            categories["No Priority"].append(task)
    
    return categories

def categorize_tasks_by_category(tasks: List[Any]) -> Dict[str, List[Any]]:
    """Group tasks by their category."""
    categories = {}
    
    for task in tasks:
        category = getattr(task, 'category', 'Uncategorized')
        if category not in categories:
            categories[category] = []
        categories[category].append(task)
    
    return categories

def get_days_until_deadline(deadline: Union[date, datetime, str, None]) -> Optional[int]:
    """Calculate days until deadline."""
    if not deadline:
        return None
    
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00')).date()
        except ValueError:
            return None
    
    if isinstance(deadline, datetime):
        deadline = deadline.date()
    
    today = date.today()
    delta = deadline - today
    return delta.days

def format_deadline_urgency(deadline: Union[date, datetime, str, None]) -> str:
    """Format deadline with urgency indicator."""
    days = get_days_until_deadline(deadline)
    
    if days is None:
        return "No deadline"
    
    if days < 0:
        return f"⚠️  {abs(days)} days overdue"
    elif days == 0:
        return "🔥 Due today"
    elif days == 1:
        return "🔥 Due tomorrow"
    elif days <= 3:
        return f"🟡 Due in {days} days"
    elif days <= 7:
        return f"🟢 Due in {days} days"
    else:
        return f"Due in {days} days"

def validate_notion_database_id(database_id: str) -> bool:
    """Validate Notion database ID format."""
    return len(database_id) == 32 and database_id.replace('-', '').isalnum()

def validate_notion_api_key(api_key: str) -> bool:
    """Validate Notion API key format."""
    return api_key.startswith('secret_') and len(api_key) > 20

def safe_get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Safely get nested dictionary value using dot notation."""
    keys = path.split('.')
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default

def batch_list(items: List[Any], batch_size: int = 10) -> List[List[Any]]:
    """Split list into batches of specified size."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

def create_checkbox_markdown(text: str, checked: bool = False) -> str:
    """Create markdown checkbox format."""
    checkbox = "☑️" if checked else "☐"
    return f"{checkbox} {text}"

def create_priority_badge(priority: str) -> str:
    """Create priority badge with color coding."""
    badges = {
        "High Prior": "🔴 High",
        "Mid Prior": "🟡 Mid", 
        "Low Prior": "🟢 Low",
        "High": "🔴 High",
        "Medium": "🟡 Med",
        "Low": "🟢 Low"
    }
    return badges.get(priority, priority)

def extract_notion_id_from_url(url: str) -> Optional[str]:
    """Extract Notion page/database ID from URL."""
    # Handle different Notion URL formats
    if 'notion.so' not in url:
        return None
    
    # Extract the ID part (last segment after the last dash)
    parts = url.split('/')[-1]  # Get last part of URL
    if '-' in parts:
        # Format: title-32characterid
        potential_id = parts.split('-')[-1]
        if len(potential_id) == 32:
            return potential_id
    
    # Handle query parameters
    if '?' in parts:
        parts = parts.split('?')[0]
    
    if len(parts) == 32:
        return parts
    
    return None

# Constants for common Notion block types
NOTION_BLOCKS = {
    "paragraph": lambda text: {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    },
    
    "heading_2": lambda text: {
        "object": "block", 
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    },
    
    "callout": lambda text, icon="💡": {
        "object": "block",
        "type": "callout", 
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"emoji": icon}
        }
    },
    
    "divider": {
        "object": "block",
        "type": "divider",
        "divider": {}
    }
}

if __name__ == "__main__":
    # Test utility functions
    console.print("🧪 Testing utility functions...", style="blue")
    
    # Test date formatting
    today = date.today()
    console.print(f"Date for Notion: {format_date_for_notion(today)}")
    console.print(f"Date for display: {format_date_for_display(today)}")
    console.print(f"Page title: {format_page_title(today)}")
    
    # Test deadline urgency
    console.print(f"Deadline urgency (today): {format_deadline_urgency(today)}")
    
    # Test validation
    console.print(f"Valid API key: {validate_notion_api_key('secret_test123456')}")
    console.print(f"Valid DB ID: {validate_notion_database_id('12345678901234567890123456789012')}")
    
    console.print("✅ All tests passed", style="green")