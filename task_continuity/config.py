"""
Configuration management for AI Task Continuity System
Handles environment variables, database IDs, and system settings.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import validator
from pydantic_settings import BaseSettings
from rich.console import Console

console = Console()

class Config(BaseSettings):
    """Configuration settings loaded from environment variables."""
    
    # Notion API Configuration
    notion_api_key: str
    plan_ai_database_id: str = "2656a6667ea28002b856c2fbf3f16a80"
    job_tracker_database_id: str = "2666a6667ea28074a138ffb541b4e3c9"
    daily_planner_parent_id: str = "2356a6667ea280efb26aea8e14d4990a"
    
    # Job Filtering Keywords (prioritized order)
    job_keywords_research: List[str] = ["Research", "Researcher", "Research Scientist"]
    job_keywords_ai_ml: List[str] = ["AI", "Machine Learning", "Deep Learning", "ML Engineer", "AI Engineer"]
    job_keywords_internship: List[str] = ["Internship", "Intern", "Summer"]
    job_keywords_engineer: List[str] = ["Engineer", "Developer", "Software"]
    
    # System Settings
    max_feature_jobs: int = 4
    notion_rate_limit: float = 0.34  # Seconds between requests (3 req/sec)
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @validator('notion_api_key')
    def validate_notion_key(cls, v):
        if not v or not v.startswith('secret_'):
            raise ValueError('notion_api_key must be provided and start with "secret_"')
        return v
        
    @validator('plan_ai_database_id', 'job_tracker_database_id', 'daily_planner_parent_id')
    def validate_notion_ids(cls, v):
        if not v or len(v) != 32:
            raise ValueError('Notion IDs must be 32 characters long')
        return v
    
    def __init__(self, **kwargs):
        # Load environment variables
        env_file = Path('.env')
        if env_file.exists():
            load_dotenv(env_file)
            console.print(f"✓ Loaded environment from {env_file}", style="dim green")
        else:
            console.print("⚠️  No .env file found, using environment variables", style="yellow")
            
        super().__init__(**kwargs)
    
    @property
    def all_job_keywords(self) -> List[str]:
        """Get all job keywords in priority order."""
        return (self.job_keywords_research + 
                self.job_keywords_ai_ml + 
                self.job_keywords_internship + 
                self.job_keywords_engineer)
    
    def get_job_category_priority(self, job_title: str) -> int:
        """Get priority score for a job based on title (lower = higher priority)."""
        job_title_lower = job_title.lower()
        
        # Research = 1 (highest priority)
        if any(keyword.lower() in job_title_lower for keyword in self.job_keywords_research):
            return 1
            
        # AI/ML = 2
        if any(keyword.lower() in job_title_lower for keyword in self.job_keywords_ai_ml):
            return 2
            
        # Internship = 3
        if any(keyword.lower() in job_title_lower for keyword in self.job_keywords_internship):
            return 3
            
        # Engineer = 4
        if any(keyword.lower() in job_title_lower for keyword in self.job_keywords_engineer):
            return 4
            
        # Other = 5 (lowest priority)
        return 5
    
    def get_priority_level_score(self, priority: str) -> int:
        """Convert priority level to numeric score (lower = higher priority)."""
        priority_map = {
            "High Prior": 1,
            "Mid Prior": 2,
            "Low Prior": 3,
            "": 4  # No priority set
        }
        return priority_map.get(priority, 4)

def create_sample_env():
    """Create a sample .env file for user reference."""
    env_content = """# AI Task Continuity System Configuration
# Copy this to .env and fill in your actual values

# Notion API Key (get from https://www.notion.so/my-integrations)
NOTION_API_KEY=secret_your_api_key_here

# Database IDs (extract from Notion URLs)
PLAN_AI_DATABASE_ID=2656a6667ea28002b856c2fbf3f16a80
JOB_TRACKER_DATABASE_ID=2666a6667ea28074a138ffb541b4e3c9
DAILY_PLANNER_PARENT_ID=2356a6667ea280efb26aea8e14d4990a

# Optional: System Settings
MAX_FEATURE_JOBS=4
LOG_LEVEL=INFO
"""
    
    sample_file = Path('.env.sample')
    with open(sample_file, 'w') as f:
        f.write(env_content)
    
    console.print(f"📝 Created {sample_file} - copy to .env and configure", style="blue")

if __name__ == "__main__":
    # Create sample env file
    create_sample_env()
    
    # Test configuration loading
    try:
        config = Config()
        console.print("✅ Configuration loaded successfully", style="green")
        console.print(f"Job categories: {len(config.all_job_keywords)} keywords", style="dim")
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("Run: python config.py to create .env.sample", style="yellow")