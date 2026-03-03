"""
Scribe Auto-Generation Module
Monitors git commits and auto-generates changelog entries.
Corrective Action 4 from Behavioral Audit.
"""
import subprocess
import json
from datetime import datetime

class ScribeAutoGen:
    """
    Automated changelog generation from git commits.
    Eliminates manual changelog maintenance.
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        
    def get_recent_commits(self, since: str = "1 week ago") -> list:
        """Get commits since a given date."""
        result = subprocess.run(
            ['git', '-C', self.repo_path, 'log', f'--since={since}',
             '--format=%H|%an|%s|%ai', '--no-merges'],
            capture_output=True, text=True
        )
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|', 3)
                commits.append({
                    'hash': parts[0][:7],
                    'author': parts[1],
                    'message': parts[2],
                    'date': parts[3]
                })
        return commits
    
    def categorize_commit(self, message: str) -> str:
        """Categorize a commit message."""
        msg = message.lower()
        if any(w in msg for w in ['fix', 'bug', 'patch', 'hotfix']):
            return 'Bug Fix'
        elif any(w in msg for w in ['feat', 'add', 'new', 'implement']):
            return 'Feature'
        elif any(w in msg for w in ['refactor', 'clean', 'improve', 'optimize']):
            return 'Improvement'
        elif any(w in msg for w in ['doc', 'readme', 'changelog']):
            return 'Documentation'
        elif any(w in msg for w in ['security', 'guard', 'protect', 'firewall']):
            return 'Security'
        elif any(w in msg for w in ['test', 'spec', 'check']):
            return 'Testing'
        return 'Other'
    
    def generate_changelog(self, since: str = "1 week ago") -> str:
        """Generate a changelog entry from recent commits."""
        commits = self.get_recent_commits(since)
        
        if not commits:
            return "No commits found in the specified period."
        
        # Group by category
        categories = {}
        for commit in commits:
            cat = self.categorize_commit(commit['message'])
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(commit)
        
        # Format
        lines = [f"# Changelog — Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        for cat, cat_commits in sorted(categories.items()):
            lines.append(f"## {cat}")
            for c in cat_commits:
                lines.append(f"- [{c['hash']}] {c['message']} ({c['author']})")
            lines.append("")
        
        lines.append(f"Total: {len(commits)} commits")
        return '\n'.join(lines)
