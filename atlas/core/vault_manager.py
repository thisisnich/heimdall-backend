"""
Vault Manager - Enhanced vault integration for Heimdall-Obsidian sync
Handles GitHub-based vault operations with real-time sync
"""

import os
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import requests
from markitdown import MarkItDown

class VaultManager:
    def __init__(self, vault_path: str = "/tmp/heimdall-vault"):
        self.vault_path = Path(vault_path)
        self.config_path = self.vault_path / ".heimdall-config.yaml"
        self.config = self.load_config()
        self.md = MarkItDown()
        
    def load_config(self) -> Dict:
        """Load vault configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def save_config(self):
        """Save vault configuration"""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def add_content(self, content: str, filename: str, folder: str = "00-RAW", 
                   classification: Optional[Dict] = None) -> Dict:
        """Add content to vault with automatic classification"""
        
        # Auto-classify if not provided
        if not classification:
            classification = self.classify_content(content, filename)
        
        # Create Obsidian note
        note_content = self.create_obsidian_note(content, classification, filename)
        
        # Determine target path
        target_folder = classification.get('folder', folder)
        target_path = self.vault_path / target_folder
        
        # Ensure folder exists
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Write file
        note_filename = f"{Path(filename).stem}.md"
        note_path = target_path / note_filename
        
        # Handle duplicates
        counter = 1
        while note_path.exists():
            note_filename = f"{Path(filename).stem}_{counter}.md"
            note_path = target_path / note_filename
            counter += 1
        
        note_path.write_text(note_content, encoding='utf-8')
        
        # Git commit
        self.git_commit(f"Add {note_filename} to {target_folder}")
        
        return {
            'status': 'success',
            'path': str(note_path.relative_to(self.vault_path)),
            'classification': classification,
            'vault_url': self.get_vault_file_url(note_path)
        }
    
    def process_document(self, file_path: str, original_filename: str = None) -> Dict:
        """Process document using MarkItDown"""
        try:
            result = self.md.convert(file_path)
            filename = original_filename or Path(file_path).name
            
            # Classify and add to vault
            classification = self.classify_content(result.text_content, filename)
            
            return self.add_content(
                result.text_content,
                filename,
                classification=classification
            )
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def process_youtube(self, url: str) -> Dict:
        """Process YouTube content"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            import re
            
            # Extract video ID
            video_id = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)', url)
            if not video_id:
                return {'status': 'error', 'error': 'Invalid YouTube URL'}
            
            video_id = video_id.group(1)
            
            # Get transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = ' '.join([entry['text'] for entry in transcript])
            
            # Get video metadata
            try:
                import requests
                response = requests.get(f"https://noembed.com/embed?url={url}")
                metadata = response.json() if response.status_code == 200 else {}
                title = metadata.get('title', f'YouTube Video {video_id}')
            except:
                title = f'YouTube Video {video_id}'
            
            # Create content with metadata
            content = f"""# {title}

**Source:** {url}
**Video ID:** {video_id}
**Processed:** {datetime.now().isoformat()}

## Transcript

{transcript_text}

## Summary

*Auto-generated summary will be added by Heimdall*
"""
            
            # Classify and add to vault
            classification = self.classify_content(content, title)
            classification['type'] = 'youtube'
            
            return self.add_content(
                content,
                f"{title}.md",
                classification=classification
            )
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def process_instagram(self, url: str) -> Dict:
        """Process Instagram content"""
        try:
            # Basic Instagram processing - would need instaloader for full functionality
            content = f"""# Instagram Post

**Source:** {url}
**Processed:** {datetime.now().isoformat()}

## Content

*Instagram content extraction would require additional setup*

## Notes

Add manual notes about this post here.
"""
            
            # Classify and add to vault
            classification = self.classify_content(content, "Instagram Post")
            classification['type'] = 'instagram'
            
            return self.add_content(
                content,
                "Instagram_Post.md",
                classification=classification
            )
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def classify_content(self, content: str, filename: str) -> Dict:
        """Smart classification into PARA structure with school notes support"""
        content_lower = content.lower()
        filename_upper = filename.upper()
        
        # Enhanced classification with confidence scoring
        scores = {
            '01-PROJECTS': 0,
            '02-AREAS': 0,
            '03-RESOURCES': 0,
            '04-ARCHIVE': 0,
            '00-RAW': 0
        }
        
        # Project indicators (enhanced for school)
        project_keywords = [
            'project', 'deadline', 'goal', 'deliverable', 'milestone', 'timeline', 'task', 'assignment',
            'lab', 'homework', 'quiz', 'exam', 'test', 'presentation', 'fyp', 'submit', 'due'
        ]
        scores['01-PROJECTS'] = sum(1 for keyword in project_keywords if keyword in content_lower)
        
        # Area indicators (enhanced for learning)
        area_keywords = [
            'area', 'responsibility', 'role', 'ongoing', 'maintain', 'manage', 'oversee',
            'learning', 'study', 'course', 'module', 'lecture', 'understanding', 'concept', 'theory'
        ]
        scores['02-AREAS'] = sum(1 for keyword in area_keywords if keyword in content_lower)
        
        # Resource indicators (enhanced for reference)
        resource_keywords = [
            'reference', 'resource', 'guide', 'tutorial', 'documentation', 'notes', 'learning',
            'formula', 'example', 'sample', 'cheat sheet', 'summary', 'review', 'textbook'
        ]
        scores['03-RESOURCES'] = sum(1 for keyword in resource_keywords if keyword in content_lower)
        
        # Archive indicators (more restrictive for active courses)
        archive_keywords = ['completed', 'finished', 'archived', 'historical', 'old', 'past']
        # Don't treat year numbers as archive indicators for course notes
        if not any(code in filename_upper or code in content_lower for code in course_codes):
            archive_keywords.extend(['2023', '2024'])
        scores['04-ARCHIVE'] = sum(1 for keyword in archive_keywords if keyword in content_lower)
        
        # Special handling for course codes
        course_codes = ['EGE353', 'EGE321', 'EGE351', 'EGE322', 'EGE301', 'EGE320']
        if any(code in filename_upper or code in content_lower for code in course_codes):
            # For active course notes, prefer RESOURCES unless clearly project work
            if scores['01-PROJECTS'] >= 2:
                scores['01-PROJECTS'] += 3  # Strong project signal (labs, assignments)
            else:
                scores['03-RESOURCES'] += 5  # Default to resources for course notes
                scores['04-ARCHIVE'] = 0  # Don't archive active course notes
        
        # Determine best folder
        best_folder = max(scores, key=scores.get)
        confidence = scores[best_folder] / max(sum(scores.values()), 1)
        
        # Map to types
        folder_to_type = {
            '01-PROJECTS': 'project',
            '02-AREAS': 'area',
            '03-RESOURCES': 'resource',
            '04-ARCHIVE': 'archive',
            '00-RAW': 'raw'
        }
        
        # If confidence is low, default to RAW
        if confidence < 0.3:
            best_folder = '00-RAW'
        
        # Extract course info if present
        course_info = self.extract_course_info(content, filename)
        
        return {
            'folder': best_folder,
            'type': folder_to_type[best_folder],
            'confidence': confidence,
            'scores': scores,
            'course_info': course_info
        }
    
    def extract_course_info(self, content: str, filename: str) -> Dict:
        """Extract course information from content"""
        course_codes = ['EGE353', 'EGE321', 'EGE351', 'EGE322', 'EGE301', 'EGE320']
        course_names = {
            'EGE353': 'Autonomous Mobile Robotics',
            'EGE321': 'Wireless Communication & Networking',
            'EGE351': 'Automation Systems & Control',
            'EGE322': 'IOT System Project',
            'EGE301': 'Communication & Workplace Success',
            'EGE320': 'Embedded System Design & Technology'
        }
        
        filename_upper = filename.upper()
        content_upper = content.upper()
        
        for code in course_codes:
            if code in filename_upper or code in content_upper:
                return {
                    'code': code,
                    'name': course_names.get(code, 'Unknown Course'),
                    'detected': True
                }
        
        return {'code': None, 'name': None, 'detected': False}
    
    def create_obsidian_note(self, content: str, classification: Dict, filename: str) -> str:
        """Create Obsidian-formatted note with frontmatter"""
        now = datetime.now().isoformat()
        title = Path(filename).stem
        
        # Enhanced frontmatter
        frontmatter = f"""---
created: {now}
type: {classification['type']}
source: {filename}
vault: {classification['folder']}
confidence: {classification.get('confidence', 0)}
tags: []
---

# {title}

> **Source:** {filename}
> **Type:** {classification['type']}
> **Confidence:** {classification.get('confidence', 0):.2f}
> **Processed:** {now}

{content}

## Metadata

- **Classification:** {classification['folder']}
- **Auto-generated:** Yes
- **Last updated:** {now}

---

*This note was automatically generated by Heimdall*
"""
        
        return frontmatter
    
    def git_commit(self, message: str = None):
        """Commit changes to git"""
        try:
            if not message:
                message = f"Auto-sync {datetime.now().isoformat()}"
            
            subprocess.run(['git', 'add', '.'], check=True, cwd=self.vault_path)
            subprocess.run(['git', 'commit', '-m', message], check=True, cwd=self.vault_path)
            subprocess.run(['git', 'push', 'origin', 'master'], check=True, cwd=self.vault_path)
            
            return {'status': 'success', 'message': 'Changes pushed to GitHub'}
            
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_vault_file_url(self, file_path: Path) -> str:
        """Get GitHub URL for vault file"""
        repo_url = "https://github.com/thisisnich/heimdall-vault"
        relative_path = file_path.relative_to(self.vault_path)
        return f"{repo_url}/blob/master/{relative_path}"
    
    def search_vault(self, query: str) -> List[Dict]:
        """Search vault content"""
        results = []
        query_lower = query.lower()
        
        # Search through all markdown files
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name.startswith('.'):
                continue
                
            try:
                content = md_file.read_text(encoding='utf-8')
                if query_lower in content.lower():
                    relative_path = md_file.relative_to(self.vault_path)
                    results.append({
                        'file': str(relative_path),
                        'path': str(md_file),
                        'url': self.get_vault_file_url(md_file),
                        'matches': content.count(query)
                    })
            except Exception as e:
                continue
        
        return sorted(results, key=lambda x: x['matches'], reverse=True)
    
    def get_vault_stats(self) -> Dict:
        """Get vault statistics"""
        stats = {
            'total_files': 0,
            'by_folder': {},
            'by_type': {},
            'last_updated': None
        }
        
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name.startswith('.'):
                continue
                
            stats['total_files'] += 1
            
            # Count by folder
            folder = md_file.parent.name
            stats['by_folder'][folder] = stats['by_folder'].get(folder, 0) + 1
            
            # Try to extract type from frontmatter
            try:
                content = md_file.read_text(encoding='utf-8')
                if 'type:' in content:
                    type_match = content.split('type:')[1].split('\n')[0].strip()
                    stats['by_type'][type_match] = stats['by_type'].get(type_match, 0) + 1
            except:
                pass
        
        return stats
