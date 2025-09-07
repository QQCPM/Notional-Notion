# 🚀 AI Task Continuity System

**Automated daily planning that scans uncompleted tasks, intelligently selects priority job applications, and generates tomorrow's organized daily plan.**

Transform your daily planning from 15+ minutes of manual work to 2-3 minutes of automated efficiency with smart task carryover and job prioritization.

## ✨ Features

- **🔄 Smart Task Carryover**: Automatically carries over uncompleted tasks (excluding Schedule items)
- **💼 Intelligent Job Selection**: Prioritizes AI/Research roles with deadline awareness  
- **📋 Interactive Review**: Terminal-based editing before publishing
- **🎯 Category Organization**: Maintains task organization across Priorities, Daily Habits, etc.
- **⚡ Robust Error Handling**: Retry logic and rate limiting for Notion API
- **📊 Insightful Analytics**: Task pattern analysis and progress tracking

## 🏗️ Architecture

```
task_continuity/
├── main.py                 # Entry point - python main.py
├── config.py              # Configuration management
├── notion_client.py       # Notion API wrapper with rate limiting
├── task_processor.py      # Core business logic
├── page_generator.py      # Page structure creation
├── cli_interface.py       # Interactive user interface
├── utils.py              # Helper functions and utilities
├── templates/
│   └── daily_page.json   # Page structure template
├── requirements.txt      # Python dependencies
├── .env.sample          # Configuration template
└── README.md           # This file
```

## 🚀 Quick Start

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

## 🎯 How It Works

### Data Flow
```
Today's Uncompleted Tasks → Smart Job Selection → Tomorrow's Page Generation → User Review → Publication
```

### Core Workflow

1. **📊 Task Collection**: Scans Plan AI database for uncompleted tasks scheduled for today
2. **💼 Job Analysis**: Analyzes Job Tracker for AI/Research opportunities with intelligent prioritization  
3. **⚡ Smart Carryover**: Creates tomorrow's tasks (excluding Schedule items) with fresh status
4. **📝 Page Generation**: Builds structured Notion page with callouts and embedded databases
5. **👀 Interactive Review**: Terminal interface for editing tasks and jobs before publishing
6. **🚀 Publication**: Creates tomorrow's page and database entries atomically

### Job Prioritization Logic

Jobs are scored and ranked by:
1. **Category Priority**: Research > AI/ML > Internship > Engineer  
2. **Priority Level**: High Prior > Mid Prior > Low Prior
3. **Deadline Urgency**: Sooner deadlines = higher priority
4. **Keyword Matching**: AI, Machine Learning, Research, etc.

## 🖥️ Usage

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

### Example Session
```
🚀 AI Task Continuity System
✓ Configuration loaded
✓ Notion API connection validated  
📅 Processing tasks from 2025-09-06 → 2025-09-07

🔍 Scanning uncompleted tasks...
Found 8 uncompleted tasks

💼 Analyzing job opportunities...
Selected 4 priority jobs

⚡ Processing task carryover...
Prepared 7 tasks for carryover, 1 schedule item excluded

📝 Generating tomorrow's page...

👀 Review Phase
🎛️  What would you like to do?
   preview  - 📋 View full preview
   tasks    - ✏️  Edit tasks  
   jobs     - 💼 Edit feature jobs
   add      - ➕ Add new task
   remove   - ➖ Remove task
   approve  - ✅ Approve & publish
   cancel   - ❌ Cancel

Your choice: approve

✅ Tomorrow's plan ready!
🔗 https://notion.so/your-page-url-here
```

## 🔧 Advanced Configuration

### Custom Job Keywords

Modify `config.py` to customize job filtering:

```python
job_keywords_research = ["Research", "Researcher", "Research Scientist", "PhD"]
job_keywords_ai_ml = ["AI", "Machine Learning", "Deep Learning", "NLP", "Computer Vision"]  
```

### Rate Limiting

Adjust API rate limiting in `.env`:
```bash
NOTION_RATE_LIMIT=0.34  # 3 requests per second
MAX_RETRIES=3
RETRY_DELAY=1.0
```

### Logging

Enable file logging:
```bash
LOG_LEVEL=DEBUG
LOG_FILE=logs/task_continuity.log
```

## 🛠️ Development

### Project Structure

- **main.py**: Entry point and orchestration
- **config.py**: Configuration management with validation
- **notion_client.py**: Robust API wrapper with retry logic
- **task_processor.py**: Core business logic for carryover and job selection
- **page_generator.py**: Template-based page creation
- **cli_interface.py**: Interactive terminal interface
- **utils.py**: Shared utilities and helpers

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

## 📊 Expected Database Structure

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

## ⚠️ Troubleshooting

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

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG
python main.py
```

## 🔄 Roadmap

### Phase 1 (Current) - Terminal MVP ✅
- [x] Core workflow automation  
- [x] Interactive terminal interface
- [x] Robust error handling
- [x] Smart job prioritization

### Phase 2 - Web Interface  
- [ ] Web dashboard for editing
- [ ] Notion button integration
- [ ] Background processing with queues

### Phase 3 - Analytics & Intelligence
- [ ] Historical task completion analytics
- [ ] AI-powered task prioritization
- [ ] Calendar integration
- [ ] Team collaboration features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for daily productivity optimization
- Designed for AI/ML job search workflows  
- Inspired by Getting Things Done (GTD) methodology

---

**Made with ❤️ for productive daily planning**

*Transform your daily planning from chaos to clarity with intelligent automation.*