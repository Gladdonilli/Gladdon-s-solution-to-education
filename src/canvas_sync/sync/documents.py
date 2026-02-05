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
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

from canvas_sync.api.auth import get_canvas_client
from canvas_sync.config import DEFAULT_CANVAS_URL, DEFAULT_VAULT_PATH
from canvas_sync.db.models import (
    get_config,
    get_db,
    get_selected_courses,
    get_sync_state,
    set_sync_state,
)
from canvas_sync.sync.utils import html_to_markdown, sanitize_filename


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


def is_allowed_url(url: str, allowed_hosts: set[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    return host in allowed_hosts


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def download_to_path(url: str, destination: Path, timeout_seconds: int = 30) -> None:
    with urlopen(url, timeout=timeout_seconds) as response:
        destination.write_bytes(response.read())


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
    canvas_url = get_config(conn, "canvas_url") or DEFAULT_CANVAS_URL
    canvas_host = urlparse(canvas_url).hostname
    allowed_canvas_hosts = {canvas_host} if canvas_host else set()
    
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
                    safe_name = sanitize_filename(file_name)
                    local_path = folder_path / safe_name
                    folder_root = folder_path.resolve()
                    resolved_path = local_path.resolve()
                    if not resolved_path.is_relative_to(folder_root):
                        logging.warning("Skipping suspicious file name: %s", file_name)
                        skipped += 1
                        continue
                    
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
                        if not allowed_canvas_hosts or not is_allowed_url(
                            download_url, allowed_canvas_hosts
                        ):
                            logging.warning("Skipping untrusted download URL: %s", download_url)
                            skipped += 1
                            continue
                        download_to_path(download_url, local_path)
                        
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
                        
                        logging.info(f"Downloaded: {folder_name}/{safe_name}")
                        synced += 1
                        
                    except (HTTPError, URLError, OSError) as e:
                        logging.warning(f"Failed to download {safe_name}: {e}")
                        
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
    allowed_hosts = {"courses.grainger.illinois.edu"}
    
    synced = 0
    skipped = 0
    
    # Create subdirectories
    (target_path / "labs").mkdir(parents=True, exist_ok=True)
    (target_path / "mps").mkdir(parents=True, exist_ok=True)
    (target_path / "resources").mkdir(parents=True, exist_ok=True)
    
    # Scrape schedule page for links
    try:
        with urlopen(f"{base_url}/assignments/", timeout=30) as response:
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
                        if not is_allowed_url(full_url, allowed_hosts):
                            logging.warning("Skipping untrusted CS 225 URL: %s", full_url)
                            skipped += 1
                            continue
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
                        if not is_allowed_url(full_url, allowed_hosts):
                            logging.warning("Skipping untrusted CS 225 URL: %s", full_url)
                            skipped += 1
                            continue
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
        with urlopen(f"{base_url}/resources/", timeout=30) as response:
            html = response.read().decode('utf-8')
            
            # Find PDF links
            pdf_pattern = re.compile(r'href="([^"]+\.pdf)"')
            pdf_links = set(pdf_pattern.findall(html))
            
            for link in pdf_links:
                full_url = urljoin(f"{base_url}/resources/", link)
                if not is_allowed_url(full_url, allowed_hosts):
                    logging.warning("Skipping untrusted CS 225 URL: %s", full_url)
                    skipped += 1
                    continue
                pdf_name = sanitize_filename(Path(urlparse(full_url).path).name)
                if not pdf_name:
                    skipped += 1
                    continue
                pdf_path = target_path / "resources" / pdf_name
                resources_root = (target_path / "resources").resolve()
                resolved_path = pdf_path.resolve()
                if not resolved_path.is_relative_to(resources_root):
                    logging.warning("Skipping suspicious resource name: %s", pdf_name)
                    skipped += 1
                    continue
                
                if not pdf_path.exists():
                    try:
                        download_to_path(full_url, pdf_path)
                        synced += 1
                        logging.info(f"Downloaded CS 225 resource: {pdf_name}")
                    except (HTTPError, URLError, OSError) as e:
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
                            
                            text_content = html_to_markdown(page_body)
                            
                            file_name = sanitize_filename(title)
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
                            
                    except (HTTPError, URLError, OSError) as e:
                        logging.warning(f"Failed to fetch page {title}: {e}")
                        
                elif item_type == 'ExternalUrl':
                    # Save external URL as markdown link
                    url = getattr(item, 'external_url', '')
                    if url and is_http_url(url):
                        file_name = sanitize_filename(title)
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
                    elif url:
                        logging.warning("Skipping non-http external URL: %s", url)
                            
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
