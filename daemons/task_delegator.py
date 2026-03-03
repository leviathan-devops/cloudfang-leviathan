"""
CTO Task Delegation Module
Decision tree for what the CTO handles vs what gets delegated to sub-agents.
Corrective Action 3 from Behavioral Audit.
"""

class TaskDelegator:
    """
    Determines whether a task should be handled by the CTO directly
    or delegated to sub-agents.
    
    Rule: CTO handles ONLY architecture decisions, strategic planning,
    and high-complexity problem-solving. Everything else is delegated.
    """
    
    DELEGATE_PATTERNS = [
        'pdf', 'generate', 'format', 'template', 'changelog',
        'documentation', 'readme', 'report', 'summary',
        'copy', 'move', 'rename', 'delete', 'cleanup',
        'test', 'lint', 'check', 'verify', 'validate',
        'install', 'setup', 'configure', 'deploy',
    ]
    
    CTO_PATTERNS = [
        'architect', 'design', 'strategy', 'decision',
        'trade-off', 'priority', 'roadmap', 'vision',
        'crisis', 'incident', 'security', 'breach',
        'budget', 'cost', 'optimize', 'scale',
    ]
    
    @staticmethod
    def should_delegate(task_description: str) -> dict:
        """
        Returns delegation decision with reasoning.
        
        Returns:
            {
                'delegate': bool,
                'reason': str,
                'suggested_agent': str
            }
        """
        task_lower = task_description.lower()
        
        # Check if it matches CTO patterns
        for pattern in TaskDelegator.CTO_PATTERNS:
            if pattern in task_lower:
                return {
                    'delegate': False,
                    'reason': f'Architecture/strategy task (matched: {pattern})',
                    'suggested_agent': 'CTO'
                }
        
        # Check if it matches delegation patterns
        for pattern in TaskDelegator.DELEGATE_PATTERNS:
            if pattern in task_lower:
                return {
                    'delegate': True,
                    'reason': f'Routine/repetitive task (matched: {pattern})',
                    'suggested_agent': 'sub-agent'
                }
        
        # Default: estimate complexity
        word_count = len(task_description.split())
        if word_count < 20:
            return {
                'delegate': True,
                'reason': 'Simple task (short description)',
                'suggested_agent': 'sub-agent'
            }
        
        return {
            'delegate': False,
            'reason': 'Complex task requiring CTO analysis',
            'suggested_agent': 'CTO'
        }
