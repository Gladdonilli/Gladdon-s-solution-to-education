"""Daily update module for course sync with CS 225 scraping and TODO generation."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from canvas_sync.api.auth import get_canvas_client
from canvas_sync.config import DEFAULT_VAULT_PATH
from canvas_sync.db.models import (
    get_config,
    get_db,
    get_selected_courses,
    set_config,
)
from canvas_sync.sync.assignments import sync_assignments
from canvas_sync.sync.calendar import sync_calendar_events
from canvas_sync.sync.documents import sync_all_documents


def scrape_cs225_assignments(vault_path: str) -> list[dict[str, Any]]:
    """Scrape CS 225 course website for assignments.
    
    Returns list of assignment dicts with name, type, title, due_date, url.
    """
    import re
    from urllib.request import urlopen
    from html.parser import HTMLParser
    
    assignments = []
    base_url = "https://courses.grainger.illinois.edu/cs225/sp2026"
    
    class AssignmentParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_assignment = False
            self.current = {}
            self.assignments = []
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            # Look for assignment links in the schedule/assignments page
            if tag == 'a' and 'href' in attrs_dict:
                href = attrs_dict.get('href', '')
                if href and ('/mps/' in href or '/labs/' in href):
                    self.current['url'] = base_url + href if href.startswith('/') else href
                    if '/mps/' in href:
                        self.current['type'] = 'mp'
                    elif '/labs/' in href:
                        self.current['type'] = 'lab'
                    self.in_assignment = True
                    
        def handle_data(self, data):
            if self.in_assignment and data.strip():
                # Parse assignment name and due date
                text = data.strip()
                if self.current.get('url') and not self.current.get('title'):
                    self.current['title'] = text
                # Look for date patterns
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May)\s+\d{1,2}', text)
                if date_match:
                    self.current['due_date'] = date_match.group()
                    
        def handle_endtag(self, tag):
            if self.in_assignment and tag == 'a':
                if self.current.get('url') and self.current.get('title'):
                    self.assignments.append(self.current.copy())
                self.current = {}
                self.in_assignment = False
    
    try:
        # Fetch assignments page
        with urlopen(f"{base_url}/assignments/") as response:
            html = response.read().decode('utf-8')
            parser = AssignmentParser()
            parser.feed(html)
            assignments = parser.assignments
    except Exception as e:
        logging.warning(f"Failed to scrape CS 225: {e}")
    
    return assignments


def fetch_sped117_weekly_tasks(course_id: int, vault_path: str) -> list[dict[str, Any]]:
    """Fetch SPED 117 weekly module tasks from Canvas.
    
    Pattern: Each week has Overview, Readings, Discussion (original), 
    Discussion (replies), Assignment N.
    """
    tasks = []
    
    try:
        canvas = get_canvas_client(vault_path)
        course = canvas.get_course(course_id)
        
        for module in course.get_modules():
            if 'Week' in module.name:
                week_num = None
                for word in module.name.split():
                    if word.isdigit():
                        week_num = int(word)
                        break
                
                if week_num:
                    items = list(module.get_module_items())
                    for item in items:
                        task = {
                            'week': week_num,
                            'module_name': module.name,
                            'title': getattr(item, 'title', ''),
                            'type': getattr(item, 'type', ''),
                            'content_id': getattr(item, 'content_id', None),
                        }
                        tasks.append(task)
    except Exception as e:
        logging.warning(f"Failed to fetch SPED 117 modules: {e}")
    
    return tasks


def generate_todo_markdown(vault_path: str) -> str:
    """Generate interactive TODO.md with all course deadlines."""
    conn = get_db(vault_path)
    canvas = get_canvas_client(vault_path)
    
    # Collect all assignments with due dates
    all_tasks = []
    
    # Fetch Canvas assignments
    selected = get_selected_courses(conn)
    for course_info in selected:
        course_id = course_info['course_id']
        course_name = course_info['course_name']
        
        try:
            course = canvas.get_course(course_id)
            for assignment in course.get_assignments(include=['submission']):
                due = getattr(assignment, 'due_at', None)
                if due:
                    submission = getattr(assignment, 'submission', None)
                    status = getattr(submission, 'workflow_state', 'pending') if submission else 'pending'
                    
                    all_tasks.append({
                        'course': course_name.split('-')[1].strip() if '-' in course_name else course_name,
                        'name': assignment.name,
                        'due': due,
                        'status': status,
                        'url': getattr(assignment, 'html_url', ''),
                    })
        except Exception as e:
            logging.warning(f"Failed to fetch assignments for {course_name}: {e}")
    
    # Add CS 225 assignments
    cs225_assignments = scrape_cs225_assignments(vault_path)
    for a in cs225_assignments:
        all_tasks.append({
            'course': 'CS 225',
            'name': a.get('title', a.get('name', 'Unknown')),
            'due': a.get('due_date', ''),
            'status': 'pending',
            'url': a.get('url', ''),
        })
    
    conn.close()
    
    # Sort by due date
    all_tasks.sort(key=lambda x: x.get('due', '') or '9999')
    
    # Generate markdown
    now = datetime.now()
    md = f"""---
type: todo_master
synced_at: {now.isoformat()}
---

# Course TODO List

> **Last Updated**: {now.strftime('%B %d, %Y at %I:%M %p')}

---

## All Tasks

"""
    
    for task in all_tasks:
        checkbox = "[ ]" if task['status'] not in ('submitted', 'graded') else "[x]"
        course = task['course']
        name = task['name']
        due = task.get('due', 'No date')
        url = task.get('url', '')
        
        if url:
            md += f"- {checkbox} **{course}**: {name} — Due {due} — [Link]({url})\n"
        else:
            md += f"- {checkbox} **{course}**: {name} — Due {due}\n"
    
    md += """
---

## Notes

- **STAT 410**: Submit via Gradescope using LaTeX
- **CS 225**: Assignments via GitHub + PrairieLearn
- **SPED 117**: You're in **Group D (Jordan)** — discussions are group-level
- Click checkboxes to mark items complete!
"""
    
    return md


def run_daily_update(vault_path: str | None = None) -> dict[str, Any]:
    """Run daily update: sync all courses and regenerate TODO.md.
    
    Returns dict with sync results.
    """
    if vault_path is None:
        vault_path = str(DEFAULT_VAULT_PATH)
    
    conn = get_db(vault_path)
    selected = get_selected_courses(conn)
    
    results = {
        'started_at': datetime.now().isoformat(),
        'assignments_synced': 0,
        'events_synced': 0,
        'skipped': 0,
        'errors': [],
        'courses_synced': [],
    }
    
    # Sync Canvas courses
    for course in selected:
        try:
            a_count, a_skipped = sync_assignments(course['course_id'], vault_path)
            results['assignments_synced'] += a_count
            results['skipped'] += a_skipped
            results['courses_synced'].append(course['course_name'])
        except Exception as e:
            error_msg = f"Assignments for {course['course_name']}: {e}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    # Sync calendar events
    try:
        course_ids = [c['course_id'] for c in selected]
        e_count, e_skipped = sync_calendar_events(course_ids, vault_path)
        results['events_synced'] += e_count
        results['skipped'] += e_skipped
    except Exception as e:
        error_msg = f"Calendar events: {e}"
        logging.error(error_msg)
        results['errors'].append(error_msg)
    
    # Sync all course documents (PDFs, pages, materials)
    try:
        base_path = str(Path(vault_path).parent)
        doc_results = sync_all_documents(base_path)
        results['documents'] = doc_results['courses']
        results['documents_synced'] = doc_results['total_synced']
        results['documents_skipped'] = doc_results['total_skipped']
        if doc_results['errors']:
            results['errors'].extend(doc_results['errors'])
    except Exception as e:
        error_msg = f"Document sync: {e}"
        logging.error(error_msg)
        results['errors'].append(error_msg)
        results['documents_synced'] = 0
    
    # Scrape CS 225 and generate TODO
    try:
        todo_md = generate_todo_markdown(vault_path)
        todo_path = Path(vault_path) / "UIUC education" / "TODO.md"
        todo_path.parent.mkdir(parents=True, exist_ok=True)
        todo_path.write_text(todo_md, encoding='utf-8')
        results['todo_generated'] = True
    except Exception as e:
        error_msg = f"TODO generation: {e}"
        logging.error(error_msg)
        results['errors'].append(error_msg)
        results['todo_generated'] = False
    
    results['completed_at'] = datetime.now().isoformat()
    
    # Save sync status
    set_config(conn, 'last_sync_at', datetime.now().isoformat())
    set_config(conn, 'last_sync_status', json.dumps(results))
    conn.close()
    
    return results


if __name__ == "__main__":
    # Allow running directly: python -m canvas_sync.sync.daily_update
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("Running daily update...")
    results = run_daily_update()
    
    print(f"\nSync completed:")
    print(f"  Assignments synced: {results['assignments_synced']}")
    print(f"  Events synced: {results['events_synced']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  TODO generated: {results.get('todo_generated', False)}")
    
    if results['errors']:
        print(f"\nErrors:")
        for err in results['errors']:
            print(f"  - {err}")
        sys.exit(1)
