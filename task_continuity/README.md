# AI Task Continuity System

**Automated daily planning that scans uncompleted tasks, intelligently selects priority job applications, and generates tomorrow's organized daily plan.**

Transform your daily planning from 15+ minutes of manual work to 2-3 minutes of automated efficiency with smart task carryover and job prioritization.

## Features

- **Smart Task Carryover**: Automatically carries over uncompleted tasks (excluding Schedule items)
- **Intelligent Job Selection**: Prioritizes AI/Research roles with deadline awareness  
- **Interactive Review**: Terminal-based editing before publishing
- **Category Organization**: Maintains task organization across Priorities, Daily Habits, etc.
- **Robust Error Handling**: Retry logic and rate limiting for Notion API
- **Insightful Analytics**: Task pattern analysis and progress tracking

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd task_continuity

# Install dependencies
pip install -r requirements.txt

# Create configuration file
cp .env.sample .env
```

### 2. Notion Setup

#### Create Notion Integration
1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Name it "Task Continuity System"
4. Copy the **Internal Integration Token** (starts with `secret_`)

#### Get Database IDs
1. Open your **Plan AI - Active Tasks Only** database in Notion
2. Copy the URL from your browser address bar
3. Extract the 32-character database ID from the URL
4. Repeat for your **Job Tracker** database

#### Get Parent Page ID  
1. Open the page where you want daily planners created
2. Copy the URL and extract the 32-character page ID

#### Grant Permissions
1. Open each database in Notion
2. Click "..." → "Add connections" 
3. Select your "Task Continuity System" integration

### 3. Configuration

Edit `.env` with your actual values:

```bash
# Required - Get from https://www.notion.so/my-integrations  
NOTION_API_KEY=secret_your_api_key_here

# Required - Extract from Notion database URLs
PLAN_AI_DATABASE_ID=your_plan_ai_database_id_here
JOB_TRACKER_DATABASE_ID=your_job_tracker_database_id_here
DAILY_PLANNER_PARENT_ID=your_daily_planner_parent_id_here

# Optional settings
MAX_FEATURE_JOBS=4
LOG_LEVEL=INFO
```

### 4. Run the System

```bash
python main.py
```

## How It Works

### Data Flow
```
Today's Uncompleted Tasks → Smart Job Selection → Tomorrow's Page Generation → User Review → Publication
```

### Core Workflow

1. **Task Collection**: Scans Plan AI database for uncompleted tasks scheduled for today
2. **Job Analysis**: Analyzes Job Tracker for AI/Research opportunities with intelligent prioritization  
3. **Smart Carryover**: Creates tomorrow's tasks (excluding Schedule items) with fresh status
4. **Page Generation**: Builds structured Notion page with callouts and embedded databases
5. **Interactive Review**: Terminal interface for editing tasks and jobs before publishing
6. **Publication**: Creates tomorrow's page and database entries atomically

### Job Prioritization Logic

Jobs are scored and ranked by:
1. **Category Priority**: Research > AI/ML > Internship > Engineer  
2. **Priority Level**: High Prior > Mid Prior > Low Prior
3. **Deadline Urgency**: Sooner deadlines = higher priority
4. **Keyword Matching**: AI, Machine Learning, Research, etc.

## sage

### Basic Usage
```bash
# Generate tomorrow's plan
python main.py
```

### Interactive Commands

During the review phase, you can:
- `preview` - View full page preview
- `tasks` - Edit carryover tasks (remove, change priority/category)
- `jobs` - Edit feature jobs (remove, reorder)
- `add` - Add new tasks
- `remove` - Remove specific tasks  
- `approve` - Publish the plan
- `cancel` - Cancel operation



## 🔧 Advanced Configuration


### Key Design Principles

1. **Reliability**: Comprehensive error handling and retry logic
2. **User Control**: Interactive review before any changes
3. **Template-Driven**: JSON templates for easy page structure changes  
4. **Rate Limiting**: Respects Notion API limits (3 requests/second)
5. **Data Safety**: Never deletes original data, only creates new entries

### Testing Configuration

Test your configuration:
```bash
# Test config loading
python config.py

# Test Notion connection  
python -c "import asyncio; from config import Config; from notion_api import NotionClient; asyncio.run(NotionClient(Config().notion_api_key).validate_connection())"
```

## Expected Database Structure

### Plan AI - Active Tasks Only

Required fields:
- **Name** (Title): Task description
- **Status** (Checkbox): ☑️ = Done, ☐ = Not Done  
- **Next reminder** (Date): When this task is scheduled
- **Priority Level** (Select): High, Medium, Low
- **Category** (Select): Priorities, Daily Habits, Application Focus, Research & Learning, Networking, Pipeline Development, Schedule

### Job Tracker

Required fields:
- **Name** (Title): Job title/company
- **Deadline** (Date): Application deadline
- **Priority** (Select): High Prior, Mid Prior, Low Prior  
- **Application Link** (URL): Direct link to application (optional)

## Troubleshooting

### Common Issues

**"Database not found" error**
- Verify database ID is correct (32 characters)
- Ensure integration has access to the database
- Check that database fields match expected structure

**"No access to database" error**  
- Add integration to database: Database → "..." → "Add connections"
- Verify API key is correct and starts with "secret_"

**Rate limiting issues**
- System includes automatic rate limiting  
- Increase delays in config if needed
- Check Notion API status if persistent issues

**Empty results**
- Verify date filters in database views
- Check that tasks have proper "Next reminder" dates
- Ensure Status field is properly configured as checkbox
