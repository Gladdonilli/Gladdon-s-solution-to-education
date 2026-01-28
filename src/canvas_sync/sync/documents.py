"""Document sync module for downloading course materials.

Syncs:
- Canvas files (PDFs, documents) organized by folder/week
- CS 225 materials (labs, lectures, MPs) from course website
"""

import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError

from canvas_sync.api.auth import get_canvas_client
from canvas_sync.config import DEFAULT_VAULT_PATH
from canvas_sync.db.models import get_db, get_selected_courses, get_sync_state, set_sync_state


def normalize_folder_name(name: str) -> str:
    """Normalize folder names for consistency (e.g., 'Week1' -> 'week 1')."""
    # Handle 'Week1', 'Week 1', 'week1' patterns
    match = re.match(r'[Ww]eek\s*(\d+)', name)
    if match:
        return f"week {match.group(1)}"
    return name.lower().strip()


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of a file for change detection."""
    if not filepath.exists():
        return ""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def sync_canvas_files(course_id: int, vault_path: str, target_dir: str) -> tuple[int, int]:
    """Sync all files from a Canvas course to local folder.
    
    Args:
        course_id: Canvas course ID
        vault_path: Path to Obsidian vault (for DB access)
        target_dir: Local directory to sync files to (e.g., 'stat 410')
    
    Returns:
        Tuple of (synced_count, skipped_count)
    """
    canvas = get_canvas_client(vault_path)
    course = canvas.get_course(course_id)
    conn = get_db(vault_path)
    
    synced = 0
    skipped = 0
    
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    try:
        folders = list(course.get_folders())
        
        for folder in folders:
            folder_name = normalize_folder_name(folder.name)
            
            # Skip system folders
            if folder_name in ('course files', 'course_image', 'unfiled'):
                continue
            
            folder_path = target_path / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            
            try:
                files = list(folder.get_files())
                
                for file in files:
                    file_name = file.display_name
                    local_path = folder_path / file_name
                    
                    # Check if already synced (by content hash)
                    canvas_id = file.id
                    existing = get_sync_state(conn, canvas_id, 'file')
                    
                    # Get remote file info
                    remote_hash = getattr(file, 'md5', '') or ''
                    remote_updated = getattr(file, 'updated_at', '')
                    
                    # Skip if already synced and unchanged
                    if existing and existing.get('content_hash') == remote_hash:
                        skipped += 1
                        continue
                    
                    # Download the file
                    try:
                        download_url = file.url
                        urlretrieve(download_url, str(local_path))
                        
                        # Update sync state
                        set_sync_state(
                            conn,
                            canvas_id=canvas_id,
                            canvas_type='file',
                            course_id=course_id,
                            file_path=str(local_path),
                            content_hash=remote_hash or get_file_hash(local_path),
                            canvas_updated_at=remote_updated,
                            synced_at=datetime.now().isoformat(),
                        )
                        
                        logging.info(f"Downloaded: {folder_name}/{file_name}")
                        synced += 1
                        
                    except Exception as e:
                        logging.warning(f"Failed to download {file_name}: {e}")
                        
            except Exception as e:
                logging.warning(f"Failed to access folder {folder.name}: {e}")
                
    except Exception as e:
        logging.error(f"Failed to sync files for course {course_id}: {e}")
    
    conn.close()
    return synced, skipped


def scrape_cs225_materials(target_dir: str) -> tuple[int, int]:
    """Scrape CS 225 course website for all materials.
    
    Downloads:
    - Labs from /labs/
    - MPs from /mps/
    - Lectures/resources from main pages
    
    Returns:
        Tuple of (synced_count, skipped_count)
    """
    base_url = "https://courses.grainger.illinois.edu/cs225/sp2026"
    target_path = Path(target_dir)
    
    synced = 0
    skipped = 0
    
    # Create subdirectories
    (target_path / "labs").mkdir(parents=True, exist_ok=True)
    (target_path / "mps").mkdir(parents=True, exist_ok=True)
    (target_path / "resources").mkdir(parents=True, exist_ok=True)
    
    # Scrape schedule page for links
    try:
        with urlopen(f"{base_url}/assignments/") as response:
            html = response.read().decode('utf-8')
            
            # Find all lab and MP links
            lab_pattern = re.compile(r'href="(/cs225/sp2026/labs/[^"]+)"')
            mp_pattern = re.compile(r'href="(/cs225/sp2026/mps/[^"]+)"')
            
            lab_links = set(lab_pattern.findall(html))
            mp_links = set(mp_pattern.findall(html))
            
            # Create markdown index files for each lab/MP
            for link in lab_links:
                lab_name = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                if lab_name and lab_name != 'labs':
                    index_path = target_path / "labs" / f"{lab_name}.md"
                    if not index_path.exists():
                        full_url = f"https://courses.grainger.illinois.edu{link}"
                        content = f"""---
type: lab
course: CS 225
url: {full_url}
synced_at: {datetime.now().isoformat()}
---

# {lab_name}

[Open Lab Page]({full_url})
"""
                        index_path.write_text(content, encoding='utf-8')
                        synced += 1
                    else:
                        skipped += 1
            
            for link in mp_links:
                mp_name = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                if mp_name and mp_name != 'mps':
                    index_path = target_path / "mps" / f"{mp_name}.md"
                    if not index_path.exists():
                        full_url = f"https://courses.grainger.illinois.edu{link}"
                        content = f"""---
type: mp
course: CS 225
url: {full_url}
synced_at: {datetime.now().isoformat()}
---

# {mp_name}

[Open MP Page]({full_url})
"""
                        index_path.write_text(content, encoding='utf-8')
                        synced += 1
                    else:
                        skipped += 1
                        
    except URLError as e:
        logging.warning(f"Failed to scrape CS 225 calendar: {e}")
    
    # Also scrape resources page
    try:
        with urlopen(f"{base_url}/resources/") as response:
            html = response.read().decode('utf-8')
            
            # Find PDF links
            pdf_pattern = re.compile(r'href="([^"]+\.pdf)"')
            pdf_links = set(pdf_pattern.findall(html))
            
            for link in pdf_links:
                pdf_name = link.split('/')[-1]
                pdf_path = target_path / "resources" / pdf_name
                
                if not pdf_path.exists():
                    try:
                        full_url = link if link.startswith('http') else f"{base_url}/resources/{link}"
                        urlretrieve(full_url, str(pdf_path))
                        synced += 1
                        logging.info(f"Downloaded CS 225 resource: {pdf_name}")
                    except Exception as e:
                        logging.warning(f"Failed to download {pdf_name}: {e}")
                else:
                    skipped += 1
                    
    except URLError as e:
        logging.warning(f"Failed to scrape CS 225 resources: {e}")
    
    return synced, skipped


def sync_sped117_pages(course_id: int, vault_path: str, target_dir: str) -> tuple[int, int]:
    """Sync SPED 117 module pages as markdown files.
    
    Creates markdown files for each week's readings and overview pages.
    """
    canvas = get_canvas_client(vault_path)
    course = canvas.get_course(course_id)
    conn = get_db(vault_path)
    
    synced = 0
    skipped = 0
    
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    try:
        modules = list(course.get_modules())
        
        for module in modules:
            # Extract week number
            week_match = re.search(r'Week\s*(\d+)', module.name)
            if not week_match:
                continue
                
            week_num = week_match.group(1)
            week_dir = target_path / f"week {week_num}"
            week_dir.mkdir(parents=True, exist_ok=True)
            
            items = list(module.get_module_items())
            
            for item in items:
                item_type = getattr(item, 'type', '')
                title = getattr(item, 'title', '')
                
                if item_type == 'Page':
                    # Fetch page content
                    try:
                        page_url = getattr(item, 'page_url', '')
                        if page_url:
                            page = course.get_page(page_url)
                            page_body = getattr(page, 'body', '') or ''
                            
                            # Convert to markdown (basic HTML stripping)
                            # Remove HTML tags for simple conversion
                            text_content = re.sub(r'<[^>]+>', '', page_body)
                            text_content = text_content.strip()
                            
                            file_name = re.sub(r'[^\w\s-]', '', title).strip()
                            file_path = week_dir / f"{file_name}.md"
                            
                            # Check if changed
                            content_hash = hashlib.md5(text_content.encode()).hexdigest()
                            canvas_id = item.id
                            existing = get_sync_state(conn, canvas_id, 'page')
                            
                            if existing and existing.get('content_hash') == content_hash:
                                skipped += 1
                                continue
                            
                            md_content = f"""---
type: page
course: SPED 117
week: {week_num}
title: {title}
synced_at: {datetime.now().isoformat()}
---

# {title}

{text_content}
"""
                            file_path.write_text(md_content, encoding='utf-8')
                            
                            set_sync_state(
                                conn,
                                canvas_id=canvas_id,
                                canvas_type='page',
                                course_id=course_id,
                                file_path=str(file_path),
                                content_hash=content_hash,
                                canvas_updated_at=None,
                                synced_at=datetime.now().isoformat(),
                            )
                            
                            synced += 1
                            logging.info(f"Synced page: Week {week_num}/{title}")
                            
                    except Exception as e:
                        logging.warning(f"Failed to fetch page {title}: {e}")
                        
                elif item_type == 'ExternalUrl':
                    # Save external URL as markdown link
                    url = getattr(item, 'external_url', '')
                    if url:
                        file_name = re.sub(r'[^\w\s-]', '', title).strip()
                        file_path = week_dir / f"{file_name}.md"
                        
                        if not file_path.exists():
                            md_content = f"""---
type: external_link
course: SPED 117
week: {week_num}
title: {title}
url: {url}
synced_at: {datetime.now().isoformat()}
---

# {title}

[Open Link]({url})
"""
                            file_path.write_text(md_content, encoding='utf-8')
                            synced += 1
                        else:
                            skipped += 1
                            
    except Exception as e:
        logging.error(f"Failed to sync SPED 117 pages: {e}")
    
    conn.close()
    return synced, skipped


def sync_all_documents(base_path: str | None = None) -> dict[str, Any]:
    """Sync all course documents.
    
    Args:
        base_path: Base path for syncing (defaults to project root)
    
    Returns:
        Dict with sync results per course
    """
    if base_path is None:
        base_path = str(Path(DEFAULT_VAULT_PATH).parent)
    
    vault_path = str(DEFAULT_VAULT_PATH)
    
    results = {
        'started_at': datetime.now().isoformat(),
        'courses': {},
        'total_synced': 0,
        'total_skipped': 0,
        'errors': [],
    }
    
    # STAT 410 - Canvas files
    try:
        synced, skipped = sync_canvas_files(
            course_id=65270,
            vault_path=vault_path,
            target_dir=str(Path(base_path) / "stat 410")
        )
        results['courses']['STAT 410'] = {'synced': synced, 'skipped': skipped}
        results['total_synced'] += synced
        results['total_skipped'] += skipped
    except Exception as e:
        results['errors'].append(f"STAT 410: {e}")
    
    # SPED 117 - Canvas pages and links
    try:
        synced, skipped = sync_sped117_pages(
            course_id=64369,
            vault_path=vault_path,
            target_dir=str(Path(base_path) / "sped 117")
        )
        results['courses']['SPED 117'] = {'synced': synced, 'skipped': skipped}
        results['total_synced'] += synced
        results['total_skipped'] += skipped
    except Exception as e:
        results['errors'].append(f"SPED 117: {e}")
    
    # CS 225 - Web scraping
    try:
        synced, skipped = scrape_cs225_materials(
            target_dir=str(Path(base_path) / "cs 225")
        )
        results['courses']['CS 225'] = {'synced': synced, 'skipped': skipped}
        results['total_synced'] += synced
        results['total_skipped'] += skipped
    except Exception as e:
        results['errors'].append(f"CS 225: {e}")
    
    results['completed_at'] = datetime.now().isoformat()
    
    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("Syncing all course documents...")
    results = sync_all_documents()
    
    print(f"\nSync completed:")
    for course, data in results['courses'].items():
        print(f"  {course}: {data['synced']} synced, {data['skipped']} skipped")
    
    print(f"\nTotal: {results['total_synced']} synced, {results['total_skipped']} skipped")
    
    if results['errors']:
        print(f"\nErrors:")
        for err in results['errors']:
            print(f"  - {err}")
        sys.exit(1)
