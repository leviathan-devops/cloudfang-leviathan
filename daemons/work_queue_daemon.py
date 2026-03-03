"""
Work Queue Daemon — Autonomous Feature Builder
Scans PENDING_FEATURES.md for designed-but-not-coded features
Auto-assigns to coding sub-agents during idle periods

Corrective Action 1 from Behavioral Audit (2026-03-01)
"""
import os
import re
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("work_queue_daemon")

class WorkQueueDaemon:
    """
    Monitors idle periods and auto-spawns coding agents for pending features.
    Scans PENDING_FEATURES.md every 5 minutes.
    """
    
    SCAN_INTERVAL = 300  # 5 minutes
    IDLE_THRESHOLD = 600  # 10 minutes of idle before triggering
    MAX_CONCURRENT_BUILDERS = 3
    PENDING_FEATURES_PATH = "memory/PENDING_FEATURES.md"
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.last_activity = datetime.now()
        self.active_builders = []
        self.feature_queue = []
        
    def parse_pending_features(self, content: str) -> list:
        """Parse PENDING_FEATURES.md into structured feature objects."""
        features = []
        current = {}
        
        for line in content.split('\n'):
            if line.startswith('## Feature:'):
                if current:
                    features.append(current)
                current = {'name': line.replace('## Feature:', '').strip()}
            elif line.startswith('- Status:'):
                current['status'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Priority:'):
                current['priority'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Estimated Effort:'):
                current['effort'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Blocker:'):
                blocker = line.split(':', 1)[1].strip()
                current['blocked'] = blocker.lower() not in ['none', 'n/a', '']
                current['blocker'] = blocker
                
        if current:
            features.append(current)
            
        return features
    
    def prioritize(self, features: list) -> list:
        """Sort features by priority, filter out blocked/in-progress."""
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        
        eligible = [
            f for f in features 
            if f.get('status') == 'designed' 
            and not f.get('blocked', False)
        ]
        
        return sorted(eligible, key=lambda f: priority_order.get(f.get('priority', 'P3'), 3))
    
    def is_idle(self) -> bool:
        """Check if system has been idle longer than threshold."""
        return (datetime.now() - self.last_activity).total_seconds() > self.IDLE_THRESHOLD
    
    def can_spawn_builders(self) -> bool:
        """Check if we can spawn more builder agents."""
        return len(self.active_builders) < self.MAX_CONCURRENT_BUILDERS
    
    async def spawn_builder(self, feature: dict):
        """Spawn a coding sub-agent for a feature."""
        logger.info(f"[WORK QUEUE] Spawning builder for: {feature['name']}")
        
        # Update feature status
        feature['status'] = 'in-progress'
        feature['assigned_at'] = datetime.now().isoformat()
        
        self.active_builders.append({
            'feature': feature['name'],
            'started': datetime.now(),
            'status': 'building'
        })
        
        # In production: send to CTO agent for task breakdown
        # CTO spawns coding sub-agents via Hydra pod
        logger.info(f"[WORK QUEUE] Builder spawned for: {feature['name']}")
        
    async def check_builder_progress(self):
        """Check on active builders and update status."""
        for builder in self.active_builders:
            elapsed = (datetime.now() - builder['started']).total_seconds()
            logger.info(f"[WORK QUEUE] Builder '{builder['feature']}' running for {elapsed:.0f}s")
    
    async def run(self):
        """Main daemon loop."""
        logger.info("[WORK QUEUE] Daemon started. Scanning every 5 minutes.")
        
        while True:
            try:
                if self.is_idle() and self.can_spawn_builders():
                    # Read PENDING_FEATURES.md
                    if os.path.exists(self.PENDING_FEATURES_PATH):
                        with open(self.PENDING_FEATURES_PATH) as f:
                            content = f.read()
                        
                        features = self.parse_pending_features(content)
                        queue = self.prioritize(features)
                        
                        if queue:
                            top = queue[0]
                            logger.info(f"[WORK QUEUE] Top feature: {top['name']} ({top.get('priority', 'P3')})")
                            await self.spawn_builder(top)
                        else:
                            logger.info("[WORK QUEUE] No eligible features in queue.")
                    else:
                        logger.warning("[WORK QUEUE] PENDING_FEATURES.md not found!")
                
                await self.check_builder_progress()
                
            except Exception as e:
                logger.error(f"[WORK QUEUE] Error: {e}")
            
            await asyncio.sleep(self.SCAN_INTERVAL)


# Standalone runner
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    daemon = WorkQueueDaemon(
        api_url=os.environ.get("API_URL", "https://cloudfang-sandbox-production.up.railway.app"),
        api_key=os.environ.get("API_KEY", "leviathan-test-key-2026")
    )
    asyncio.run(daemon.run())
