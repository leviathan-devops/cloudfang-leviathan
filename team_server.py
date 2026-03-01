#!/usr/bin/env python3
"""
Leviathan Cloud OS - Multi-Model AI Development Team Server
A unified Flask application that orchestrates 5 specialist AI agents
across different frontier models to provide comprehensive software engineering support.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from flask import Flask, render_template_string, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# API Configuration
API_KEYS = {
    'anthropic': os.environ.get('ANTHROPIC_API_KEY', ''),
    'deepseek': os.environ.get('DEEPSEEK_API_KEY', ''),
    'xai': os.environ.get('XAI_API_KEY', ''),
    'google': os.environ.get('GOOGLE_API_KEY', ''),
    'openrouter': os.environ.get('OPENROUTER_API_KEY', ''),
}

# API Endpoints
API_ENDPOINTS = {
    'anthropic': 'https://api.anthropic.com/v1/messages',
    'deepseek': 'https://api.deepseek.com/chat/completions',
    'xai': 'https://api.x.ai/v1/chat/completions',
    'google': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
}

# Token tracking per request
token_usage = threading.local()


class AgentConfig:
    """Configuration for each specialist agent."""

    ARCHITECT = {
        'name': 'Architect',
        'model': 'claude-sonnet-4-5-20250929',
        'provider': 'anthropic',
        'system_prompt': """You are the Chief Architect of the Leviathan Cloud OS development team. Your role is to:
- Design system architecture and high-level technical solutions
- Make strategic decisions about technology choices and system design patterns
- Identify architectural risks and scalability concerns
- Propose modular, maintainable system structures
- Consider cross-cutting concerns like security, performance, and fault tolerance

When responding:
1. Provide a clear architectural vision
2. Explain key design decisions
3. Identify dependencies and integration points
4. Suggest implementation order
5. Flag architectural concerns

For Leviathan Cloud OS context: We're building a cloud operating system with distributed computing,
containerization, and microservices architecture. Think at the system level, not implementation details.""",
        'token_limit': 8000,
    }

    ENGINEER = {
        'name': 'Lead Engineer',
        'model': 'deepseek-chat',
        'provider': 'deepseek',
        'system_prompt': """You are the Lead Engineer of the Leviathan Cloud OS development team. Your role is to:
- Write production-quality code and implementations
- Handle technical implementation details
- Create concrete code solutions and examples
- Optimize for performance and efficiency
- Follow best practices and design patterns

When responding:
1. Provide working code examples
2. Explain implementation approach
3. Handle edge cases and error conditions
4. Consider performance implications
5. Suggest testing strategies

For Leviathan Cloud OS context: Focus on practical implementation of cloud OS features,
including resource management, scheduling, networking, and system calls. Write clear, maintainable code.""",
        'token_limit': 8000,
    }

    REVIEWER = {
        'name': 'Code Reviewer',
        'model': 'grok-3',
        'provider': 'xai',
        'system_prompt': """You are the Code Reviewer of the Leviathan Cloud OS development team. Your role is to:
- Review code for bugs, inefficiencies, and architectural issues
- Ensure code quality, readability, and maintainability
- Catch edge cases and potential runtime issues
- Verify compliance with coding standards
- Suggest improvements and optimizations

When responding:
1. Identify potential bugs and issues
2. Point out code quality concerns
3. Suggest specific improvements
4. Highlight security vulnerabilities
5. Rate overall code quality

For Leviathan Cloud OS context: Review system-level code, looking for issues with concurrency,
memory management, resource handling, and cloud infrastructure concerns.""",
        'token_limit': 8000,
    }

    RESEARCHER = {
        'name': 'Researcher',
        'model': 'gemini-2.0-flash',
        'provider': 'google',
        'system_prompt': """You are the Researcher of the Leviathan Cloud OS development team. Your role is to:
- Research technologies, libraries, and frameworks
- Gather context on best practices and standards
- Document findings and create learning materials
- Analyze competing solutions and approaches
- Provide technical background and context

When responding:
1. Share relevant research findings
2. Cite sources and references
3. Compare different approaches
4. Explain background concepts
5. Suggest additional resources

For Leviathan Cloud OS context: Research cloud OS patterns, distributed systems concepts,
containerization technologies, and infrastructure management approaches. Provide comprehensive context.""",
        'token_limit': 8000,
    }

    QA = {
        'name': 'QA Engineer',
        'model': 'deepseek-reasoner',
        'provider': 'deepseek',
        'system_prompt': """You are the QA Engineer of the Leviathan Cloud OS development team. Your role is to:
- Design comprehensive testing strategies
- Identify edge cases and failure scenarios
- Think deeply about system behavior under stress
- Plan for failure modes and recovery
- Ensure robustness and reliability

When responding:
1. Outline testing strategy
2. Identify critical edge cases
3. Describe failure scenarios
4. Plan for stress testing
5. Suggest monitoring and alerting

For Leviathan Cloud OS context: Focus on testing distributed systems, resource constraints,
network failures, and cloud infrastructure reliability. Think deeply about what could go wrong.""",
        'token_limit': 8000,
    }


class APIClient:
    """Unified client for making API calls to different providers."""

    @staticmethod
    def call_anthropic(system_prompt, user_message, max_tokens=2000):
        """Call Claude via Anthropic API."""
        if not API_KEYS['anthropic']:
            return None, "Anthropic API key not configured"

        try:
            response = requests.post(
                API_ENDPOINTS['anthropic'],
                headers={
                    'x-api-key': API_KEYS['anthropic'],
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': 'claude-sonnet-4-5-20250929',
                    'max_tokens': max_tokens,
                    'system': system_prompt,
                    'messages': [{'role': 'user', 'content': user_message}],
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            token_info = {
                'input': data.get('usage', {}).get('input_tokens', 0),
                'output': data.get('usage', {}).get('output_tokens', 0),
            }

            text = data['content'][0]['text']
            return text, token_info
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            return None, f"Anthropic error: {str(e)}"

    @staticmethod
    def call_deepseek(system_prompt, user_message, model='deepseek-chat', max_tokens=2000):
        """Call DeepSeek via DeepSeek API."""
        if not API_KEYS['deepseek']:
            return None, "DeepSeek API key not configured"

        try:
            response = requests.post(
                API_ENDPOINTS['deepseek'],
                headers={
                    'Authorization': f'Bearer {API_KEYS["deepseek"]}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'max_tokens': max_tokens,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_message},
                    ],
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            token_info = {
                'input': data.get('usage', {}).get('prompt_tokens', 0),
                'output': data.get('usage', {}).get('completion_tokens', 0),
            }

            text = data['choices'][0]['message']['content']
            return text, token_info
        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            return None, f"DeepSeek error: {str(e)}"

    @staticmethod
    def call_xai(system_prompt, user_message, max_tokens=2000):
        """Call Grok via xAI API."""
        if not API_KEYS['xai']:
            return None, "xAI API key not configured"

        try:
            response = requests.post(
                API_ENDPOINTS['xai'],
                headers={
                    'Authorization': f'Bearer {API_KEYS["xai"]}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'grok-3',
                    'max_tokens': max_tokens,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_message},
                    ],
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            token_info = {
                'input': data.get('usage', {}).get('prompt_tokens', 0),
                'output': data.get('usage', {}).get('completion_tokens', 0),
            }

            text = data['choices'][0]['message']['content']
            return text, token_info
        except Exception as e:
            logger.error(f"xAI API error: {str(e)}")
            return None, f"xAI error: {str(e)}"

    @staticmethod
    def call_google(system_prompt, user_message, max_tokens=2000):
        """Call Gemini via Google AI API."""
        if not API_KEYS['google']:
            return None, "Google API key not configured"

        try:
            response = requests.post(
                f"{API_ENDPOINTS['google']}?key={API_KEYS['google']}",
                headers={'Content-Type': 'application/json'},
                json={
                    'contents': [
                        {
                            'parts': [
                                {'text': system_prompt},
                                {'text': user_message},
                            ]
                        }
                    ],
                    'generationConfig': {
                        'maxOutputTokens': max_tokens,
                    },
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            token_info = {
                'input': 0,
                'output': 0,
            }

            if 'candidates' in data and data['candidates']:
                text = data['candidates'][0]['content']['parts'][0]['text']
                return text, token_info
            else:
                return None, "No valid response from Google API"
        except Exception as e:
            logger.error(f"Google API error: {str(e)}")
            return None, f"Google error: {str(e)}"


class Orchestrator:
    """Orchestrates the multi-model AI development team."""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)

    def decide_agents(self, user_message):
        """Decide which agents should be involved based on the user's message."""
        if not API_KEYS['deepseek']:
            # Default to all agents if we can't call orchestrator
            return {
                'agents': ['architect', 'engineer', 'reviewer', 'researcher', 'qa'],
                'task_descriptions': {
                    'architect': 'Provide architectural guidance',
                    'engineer': 'Implement the solution',
                    'reviewer': 'Review code quality',
                    'researcher': 'Research relevant context',
                    'qa': 'Plan testing and quality assurance',
                }
            }

        try:
            prompt = f"""You are the orchestrator of a 5-model AI development team for Leviathan Cloud OS.
Given the user's message, decide which team members should be involved.

Team members:
- architect: For system design and architecture decisions
- engineer: For code implementation
- reviewer: For code review and quality assurance
- researcher: For research and documentation
- qa: For testing strategy and edge case analysis

User message: {user_message}

Return a JSON object with:
{{
  "agents": ["architect", "engineer", ...],
  "task_descriptions": {{
    "agent_name": "specific task for this agent",
    ...
  }}
}}

Only include agents that are actually needed. Be selective."""

            response, _ = APIClient.call_deepseek(
                system_prompt="You are a task orchestrator. Return only valid JSON.",
                user_message=prompt,
                model='deepseek-chat',
                max_tokens=500,
            )

            if response:
                try:
                    # Extract JSON from response
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response[json_start:json_end]
                        result = json.loads(json_str)
                        return result
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse orchestrator response: {str(e)}")
        except Exception as e:
            logger.error(f"Orchestrator decision error: {str(e)}")

        # Default fallback
        return {
            'agents': ['architect', 'engineer', 'reviewer', 'researcher', 'qa'],
            'task_descriptions': {
                'architect': 'Provide architectural guidance',
                'engineer': 'Implement the solution',
                'reviewer': 'Review code quality',
                'researcher': 'Research relevant context',
                'qa': 'Plan testing and quality assurance',
            }
        }

    def call_agent(self, agent_name, task_description, user_message):
        """Call a single agent and return its response."""
        agent_config = getattr(AgentConfig, agent_name.upper(), None)
        if not agent_config:
            return {
                'agent': agent_name,
                'response': f"Unknown agent: {agent_name}",
                'tokens': {'input': 0, 'output': 0},
                'error': True,
            }

        # Prepare the prompt for this agent
        agent_task = f"{task_description}\n\nUser request: {user_message}"

        try:
            provider = agent_config['provider']

            if provider == 'anthropic':
                text, token_info = APIClient.call_anthropic(
                    agent_config['system_prompt'],
                    agent_task,
                    max_tokens=agent_config['token_limit'],
                )
            elif provider == 'deepseek':
                text, token_info = APIClient.call_deepseek(
                    agent_config['system_prompt'],
                    agent_task,
                    model=agent_config['model'],
                    max_tokens=agent_config['token_limit'],
                )
            elif provider == 'xai':
                text, token_info = APIClient.call_xai(
                    agent_config['system_prompt'],
                    agent_task,
                    max_tokens=agent_config['token_limit'],
                )
            elif provider == 'google':
                text, token_info = APIClient.call_google(
                    agent_config['system_prompt'],
                    agent_task,
                    max_tokens=agent_config['token_limit'],
                )
            else:
                return {
                    'agent': agent_name,
                    'response': f"Unknown provider: {provider}",
                    'tokens': {'input': 0, 'output': 0},
                    'error': True,
                }

            if text is None:
                return {
                    'agent': agent_name,
                    'response': f"Error: {token_info}",
                    'tokens': {'input': 0, 'output': 0},
                    'error': True,
                }

            return {
                'agent': agent_name,
                'response': text,
                'tokens': token_info if isinstance(token_info, dict) else {'input': 0, 'output': 0},
                'error': False,
            }
        except Exception as e:
            logger.error(f"Error calling agent {agent_name}: {str(e)}")
            return {
                'agent': agent_name,
                'response': f"Error: {str(e)}",
                'tokens': {'input': 0, 'output': 0},
                'error': True,
            }

    def synthesize_responses(self, user_message, agent_responses):
        """Synthesize multiple agent responses into a unified response."""
        if not agent_responses or all(r.get('error') for r in agent_responses):
            return {
                'content': "I encountered errors while processing your request. Please check the API keys and try again.",
                'agents_involved': [],
            }

        # Build synthesis prompt
        synthesis_prompt = f"User request: {user_message}\n\n"
        synthesis_prompt += "Team responses:\n"

        agents_involved = []
        for response in agent_responses:
            if not response.get('error'):
                agent = response['agent']
                agents_involved.append(f"{AgentConfig.__dict__.get(agent.upper(), {}).get('name', agent)}")
                synthesis_prompt += f"\n{agent.upper()}:\n{response['response']}\n"

        synthesis_system = """You are a senior engineering lead synthesizing responses from a specialized AI development team.
Your job is to combine diverse perspectives into a single, coherent response that sounds like one experienced engineering team speaking.

Guidelines:
1. Synthesize the different perspectives into a unified voice
2. Highlight key insights from each team member
3. Resolve any contradictions thoughtfully
4. Present actionable recommendations
5. Maintain technical depth while being clear
6. Don't just concatenate responses - actually synthesize them"""

        try:
            synthesized, _ = APIClient.call_deepseek(
                synthesis_system,
                synthesis_prompt,
                model='deepseek-chat',
                max_tokens=3000,
            )

            if synthesized:
                return {
                    'content': synthesized,
                    'agents_involved': list(set(agents_involved)),
                }
        except Exception as e:
            logger.error(f"Synthesis error: {str(e)}")

        # Fallback: combine responses
        combined = "Development team response:\n\n"
        for response in agent_responses:
            if not response.get('error'):
                combined += f"• {response['agent'].upper()}: {response['response']}\n\n"

        return {
            'content': combined,
            'agents_involved': agents_involved,
        }

    def process_message(self, user_message):
        """Process a user message through the team."""
        start_time = time.time()

        # Step 1: Decide which agents to involve
        logger.info(f"Processing message: {user_message[:100]}...")
        orchestration = self.decide_agents(user_message)
        agents_to_call = orchestration.get('agents', [])
        task_descriptions = orchestration.get('task_descriptions', {})

        logger.info(f"Involving agents: {agents_to_call}")

        # Step 2: Call agents in parallel
        futures = {}
        for agent in agents_to_call:
            task = task_descriptions.get(agent, 'Provide your perspective')
            future = self.executor.submit(
                self.call_agent,
                agent,
                task,
                user_message,
            )
            futures[future] = agent

        # Collect results
        agent_responses = []
        for future in as_completed(futures):
            try:
                response = future.result(timeout=35)
                agent_responses.append(response)
            except Exception as e:
                agent = futures[future]
                logger.error(f"Agent {agent} failed: {str(e)}")
                agent_responses.append({
                    'agent': agent,
                    'response': f"Error: {str(e)}",
                    'tokens': {'input': 0, 'output': 0},
                    'error': True,
                })

        # Step 3: Synthesize responses
        synthesized = self.synthesize_responses(user_message, agent_responses)

        # Calculate total tokens
        total_tokens = {
            'input': sum(r.get('tokens', {}).get('input', 0) for r in agent_responses),
            'output': sum(r.get('tokens', {}).get('output', 0) for r in agent_responses),
        }

        elapsed = time.time() - start_time

        return {
            'response': synthesized['content'],
            'agents_involved': synthesized['agents_involved'],
            'timestamp': datetime.now().isoformat(),
            'processing_time': f"{elapsed:.2f}s",
            'tokens': total_tokens,
        }


# Initialize orchestrator
orchestrator = Orchestrator()

# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leviathan Cloud OS - AI Dev Team</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            overflow: hidden;
        }

        .container {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        header {
            background: linear-gradient(135deg, #1a1f3a 0%, #0f1729 100%);
            border-bottom: 1px solid #2a3550;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
        }

        h1 {
            font-size: 24px;
            font-weight: 600;
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .message {
            display: flex;
            gap: 12px;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .message.user {
            justify-content: flex-end;
        }

        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 8px;
            line-height: 1.5;
            font-size: 14px;
            word-wrap: break-word;
        }

        .user .message-content {
            background: linear-gradient(135deg, #7c3aed, #5b21b6);
            color: white;
        }

        .assistant .message-content {
            background: #1a2332;
            border: 1px solid #2a3550;
        }

        .message-label {
            font-size: 11px;
            color: #888;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .agents-badge {
            font-size: 10px;
            color: #00d4ff;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #2a3550;
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }

        .agent-tag {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            padding: 2px 6px;
            border-radius: 3px;
        }

        .input-container {
            background: #0f1729;
            border-top: 1px solid #2a3550;
            padding: 16px 20px;
            display: flex;
            gap: 10px;
        }

        .input-wrapper {
            flex: 1;
            display: flex;
            gap: 10px;
        }

        input[type="text"] {
            flex: 1;
            background: #1a2332;
            border: 1px solid #2a3550;
            color: #e0e0e0;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.2s;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #7c3aed;
            box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1);
        }

        button {
            background: linear-gradient(135deg, #7c3aed, #5b21b6);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            font-size: 14px;
            transition: transform 0.2s, opacity 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
            opacity: 0.9;
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .loading {
            display: flex;
            gap: 6px;
            align-items: center;
        }

        .loading-dot {
            width: 6px;
            height: 6px;
            background: #00d4ff;
            border-radius: 50%;
            animation: pulse 1.4s infinite;
        }

        .loading-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .loading-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 0.3;
            }
            50% {
                opacity: 1;
            }
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            gap: 20px;
            color: #666;
        }

        .empty-state h2 {
            font-size: 20px;
            color: #888;
        }

        .empty-state p {
            font-size: 14px;
            color: #666;
        }

        .scrollbar {
            scrollbar-width: thin;
            scrollbar-color: #2a3550 transparent;
        }

        .scrollbar::-webkit-scrollbar {
            width: 6px;
        }

        .scrollbar::-webkit-scrollbar-track {
            background: transparent;
        }

        .scrollbar::-webkit-scrollbar-thumb {
            background: #2a3550;
            border-radius: 3px;
        }

        .scrollbar::-webkit-scrollbar-thumb:hover {
            background: #3a4560;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Leviathan Cloud OS</h1>
            <div class="subtitle">Multi-Model AI Development Team</div>
        </header>

        <div class="messages-container scrollbar" id="messagesContainer">
            <div class="empty-state">
                <h2>Welcome to the Dev Team</h2>
                <p>Start a conversation about your Leviathan Cloud OS project</p>
            </div>
        </div>

        <div class="input-container">
            <div class="input-wrapper">
                <input
                    type="text"
                    id="messageInput"
                    placeholder="Ask your development team anything..."
                    autocomplete="off"
                >
                <button id="sendButton" onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        const messagesContainer = document.getElementById('messagesContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');

        // Load messages from localStorage
        function loadMessages() {
            const saved = localStorage.getItem('teamMessages');
            if (saved) {
                const messages = JSON.parse(saved);
                messagesContainer.innerHTML = '';
                messages.forEach(msg => addMessageToDOM(msg, false));
                scrollToBottom();
            }
        }

        // Save messages to localStorage
        function saveMessages() {
            const messages = [];
            document.querySelectorAll('.message').forEach(el => {
                const isUser = el.classList.contains('user');
                const content = el.querySelector('.message-content').textContent;
                messages.push({ isUser, content });
            });
            localStorage.setItem('teamMessages', JSON.stringify(messages));
        }

        // Add message to DOM
        function addMessageToDOM(msg, save = true) {
            if (messagesContainer.querySelector('.empty-state')) {
                messagesContainer.innerHTML = '';
            }

            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msg.isUser ? 'user' : 'assistant'}`;

            const label = document.createElement('div');
            label.className = 'message-label';
            label.textContent = msg.isUser ? 'You' : 'Dev Team';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = msg.content;

            messageDiv.appendChild(label);
            messageDiv.appendChild(contentDiv);

            if (msg.agents) {
                const badge = document.createElement('div');
                badge.className = 'agents-badge';
                msg.agents.forEach(agent => {
                    const tag = document.createElement('div');
                    tag.className = 'agent-tag';
                    tag.textContent = agent;
                    badge.appendChild(tag);
                });
                contentDiv.appendChild(badge);
            }

            messagesContainer.appendChild(messageDiv);

            if (save) {
                saveMessages();
            }
        }

        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            // Add user message
            addMessageToDOM({ isUser: true, content: message });
            messageInput.value = '';
            messageInput.focus();
            sendButton.disabled = true;
            scrollToBottom();

            // Add loading indicator
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant';
            loadingDiv.innerHTML = `
                <div class="message-label">Dev Team</div>
                <div class="message-content">
                    <div class="loading">
                        <div class="loading-dot"></div>
                        <div class="loading-dot"></div>
                        <div class="loading-dot"></div>
                    </div>
                </div>
            `;
            messagesContainer.appendChild(loadingDiv);
            scrollToBottom();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message }),
                });

                const data = await response.json();
                messagesContainer.removeChild(loadingDiv);

                if (data.error) {
                    addMessageToDOM({
                        isUser: false,
                        content: `Error: ${data.error}`,
                        agents: [],
                    });
                } else {
                    addMessageToDOM({
                        isUser: false,
                        content: data.response,
                        agents: data.agents_involved || [],
                    });
                }
            } catch (error) {
                messagesContainer.removeChild(loadingDiv);
                addMessageToDOM({
                    isUser: false,
                    content: `Network error: ${error.message}`,
                    agents: [],
                });
            }

            sendButton.disabled = false;
            scrollToBottom();
        }

        // Event listeners
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Load messages on page load
        loadMessages();
    </script>
</body>
</html>"""


@app.route('/')
def index():
    """Serve the main chat UI."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chat messages."""
    try:
        data = request.json
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        logger.info(f"Chat request: {user_message[:100]}...")

        # Process message through orchestrator
        result = orchestrator.process_message(user_message)

        return jsonify({
            'response': result['response'],
            'agents_involved': result['agents_involved'],
            'timestamp': result['timestamp'],
            'processing_time': result['processing_time'],
            'tokens': result['tokens'],
        })
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/status')
def status():
    """Status endpoint with configuration info."""
    api_keys_status = {
        'anthropic': bool(API_KEYS['anthropic']),
        'deepseek': bool(API_KEYS['deepseek']),
        'xai': bool(API_KEYS['xai']),
        'google': bool(API_KEYS['google']),
        'openrouter': bool(API_KEYS['openrouter']),
    }

    return jsonify({
        'status': 'operational',
        'timestamp': datetime.now().isoformat(),
        'api_keys_configured': api_keys_status,
        'agents': [
            'architect',
            'engineer',
            'reviewer',
            'researcher',
            'qa',
        ],
        'description': 'Multi-Model AI Development Team for Leviathan Cloud OS',
    })


def main():
    """Main entry point."""
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    logger.info("=" * 70)
    logger.info("Leviathan Cloud OS - Multi-Model AI Development Team")
    logger.info("=" * 70)
    logger.info(f"Starting server on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info("")
    logger.info("Team Members:")
    logger.info("  - Architect (Claude via Anthropic)")
    logger.info("  - Lead Engineer (DeepSeek)")
    logger.info("  - Code Reviewer (Grok via xAI)")
    logger.info("  - Researcher (Gemini via Google)")
    logger.info("  - QA Engineer (DeepSeek Reasoner)")
    logger.info("")
    logger.info("Endpoints:")
    logger.info("  - http://localhost:{}/            (Web UI)".format(port))
    logger.info("  - http://localhost:{}/api/chat     (Chat API)".format(port))
    logger.info("  - http://localhost:{}/health       (Health check)".format(port))
    logger.info("  - http://localhost:{}/status       (Status)".format(port))
    logger.info("=" * 70)

    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    main()
