#!/usr/bin/env python3
"""
Leviathan Super Brain Dev Team v4.3 — LEAN BUILD
=================================================
Credit-efficient: single-model routing by default, multi-model only when critical.
Gemma 3 (free) = all I/O. Opus = architecture ONLY. Grok = engineering workhorse.
Discord bot + Web UI dual interface.

Cost tiers:
  Chat        → Gemma (FREE)
  Research    → DeepSeek ($0.27/M in, $1.10/M out — cheapest paid)
  Code/Debug  → Grok solo ($3/M — workhorse)
  Review      → Grok + Codex parallel ($3 + $2.50 — no Opus)
  Architecture→ Opus solo ($15/M — reserved for design decisions only)
  Synthesis   → Gemma (FREE)
"""

import os
import json
import time
import re
import logging
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import requests
from flask import Flask, render_template_string, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BRAIN] %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ─── API Configuration ────────────────────────────────────────

API_KEYS = {
    'anthropic': os.environ.get('ANTHROPIC_API_KEY', ''),
    'openai': os.environ.get('OPENAI_API_KEY', ''),
    'deepseek': os.environ.get('DEEPSEEK_API_KEY', ''),
    'xai': os.environ.get('XAI_API_KEY', ''),
    'openrouter': os.environ.get('OPENROUTER_API_KEY', ''),
}

# ─── Model Definitions ────────────────────────────────────────

MODELS = {
    'gemma': {
        'name': 'Gemma 3 27B',
        'role': 'Chat Bridge + Synthesis',
        'provider': 'openrouter',
        'model': 'google/gemma-3-27b-it',
        'max_tokens': 1000,
        'cost': 'free',
    },
    'grok': {
        'name': 'Grok',
        'role': 'Lead Engineer + Debugger + Reviewer (2M context)',
        'provider': 'xai',
        'model': 'grok-3',
        'max_tokens': 1500,
        'cost': 'paid',
    },
    'codex': {
        'name': 'Codex',
        'role': 'Engineer + Reviewer',
        'provider': 'openai',
        'model': 'gpt-4o',
        'max_tokens': 1500,
        'cost': 'paid',
    },
    'opus': {
        'name': 'Opus',
        'role': 'Architect (design decisions only)',
        'provider': 'anthropic',
        'model': 'claude-opus-4-6-20251101',
        'max_tokens': 1500,
        'cost': 'paid',
    },
    'deepseek': {
        'name': 'DeepSeek',
        'role': 'Research + Reasoning',
        'provider': 'deepseek',
        'model': 'deepseek-chat',
        'max_tokens': 1500,
        'cost': 'paid',
    },
}

# ─── Unified API Client ───────────────────────────────────────

def call_model(model_key, system_prompt, user_message, max_tokens=None):
    """Call any model. Returns (text, token_info) or (None, error_string)."""
    cfg = MODELS[model_key]
    provider = cfg['provider']
    model = cfg['model']
    mt = max_tokens or cfg['max_tokens']

    try:
        if provider == 'openrouter':
            resp = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={'Authorization': f'Bearer {API_KEYS["openrouter"]}', 'Content-Type': 'application/json'},
                json={'model': model, 'max_tokens': mt, 'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message},
                ]},
                timeout=25,
            )
            resp.raise_for_status()
            d = resp.json()
            return d['choices'][0]['message']['content'], {
                'input': d.get('usage', {}).get('prompt_tokens', 0),
                'output': d.get('usage', {}).get('completion_tokens', 0),
            }

        elif provider == 'anthropic':
            resp = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={'x-api-key': API_KEYS['anthropic'], 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
                json={'model': model, 'max_tokens': mt, 'system': system_prompt,
                      'messages': [{'role': 'user', 'content': user_message}]},
                timeout=30,
            )
            resp.raise_for_status()
            d = resp.json()
            return d['content'][0]['text'], {
                'input': d.get('usage', {}).get('input_tokens', 0),
                'output': d.get('usage', {}).get('output_tokens', 0),
            }

        elif provider == 'openai':
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {API_KEYS["openai"]}', 'Content-Type': 'application/json'},
                json={'model': model, 'max_tokens': mt, 'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message},
                ]},
                timeout=25,
            )
            resp.raise_for_status()
            d = resp.json()
            return d['choices'][0]['message']['content'], {
                'input': d.get('usage', {}).get('prompt_tokens', 0),
                'output': d.get('usage', {}).get('completion_tokens', 0),
            }

        elif provider == 'xai':
            resp = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={'Authorization': f'Bearer {API_KEYS["xai"]}', 'Content-Type': 'application/json'},
                json={'model': model, 'max_tokens': mt, 'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message},
                ]},
                timeout=25,
            )
            resp.raise_for_status()
            d = resp.json()
            return d['choices'][0]['message']['content'], {
                'input': d.get('usage', {}).get('prompt_tokens', 0),
                'output': d.get('usage', {}).get('completion_tokens', 0),
            }

        elif provider == 'deepseek':
            resp = requests.post(
                'https://api.deepseek.com/chat/completions',
                headers={'Authorization': f'Bearer {API_KEYS["deepseek"]}', 'Content-Type': 'application/json'},
                json={'model': model, 'max_tokens': mt, 'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message},
                ]},
                timeout=25,
            )
            resp.raise_for_status()
            d = resp.json()
            return d['choices'][0]['message']['content'], {
                'input': d.get('usage', {}).get('prompt_tokens', 0),
                'output': d.get('usage', {}).get('completion_tokens', 0),
            }

    except Exception as e:
        logger.error(f"[{model_key}] API error: {e}")
        return None, str(e)


# ─── Core Pipeline ─────────────────────────────────────────────

executor = ThreadPoolExecutor(max_workers=5)

# Task classification keywords (instant, no LLM call)
CODE_KEYWORDS = ['code', 'implement', 'build', 'write', 'function', 'class', 'api', 'endpoint', 'script', 'fix',
                 'create', 'make', 'bot', 'server', 'handler', 'module', 'component', 'refactor', 'deploy',
                 'docker', 'python', 'rust', 'javascript', 'typescript', 'go', 'sql']
ARCH_KEYWORDS = ['design', 'architect', 'structure', 'system', 'scale', 'infra', 'pattern', 'plan', 'stack',
                 'microservice', 'pipeline', 'diagram']
RESEARCH_KEYWORDS = ['research', 'compare', 'explain', 'what is', 'how does', 'best practice', 'alternative',
                     'library', 'framework', 'benchmark', 'why', 'difference', 'tradeoff']
REVIEW_KEYWORDS = ['review', 'audit', 'check', 'bug', 'security', 'vulnerability', 'test', 'edge case']
DEBUG_KEYWORDS = ['debug', 'error', 'crash', 'trace', 'stacktrace', 'exception', 'broken', 'failing', 'diagnose', 'root cause', 'scan']


def classify_task(msg):
    """Instant lean classification. Single-model default, multi only when critical."""
    m = msg.lower()
    token_estimate = len(msg.split())

    # Large input (>500 words) → Grok ingests (2M context)
    if token_estimate > 500:
        return 'large_input', ['grok']

    has_code = any(kw in m for kw in CODE_KEYWORDS)
    has_arch = any(kw in m for kw in ARCH_KEYWORDS)
    has_research = any(kw in m for kw in RESEARCH_KEYWORDS)
    has_review = any(kw in m for kw in REVIEW_KEYWORDS)
    has_debug = any(kw in m for kw in DEBUG_KEYWORDS)

    # Pure chat → Gemma only (FREE)
    if not has_code and not has_arch and not has_research and not has_review and not has_debug:
        return 'chat', []

    # Architecture → Opus SOLO (the only task Opus touches)
    if has_arch and not has_code:
        return 'architecture', ['opus']

    # Code review → Grok + Codex (NO Opus — too expensive for review)
    if has_review:
        return 'review', ['grok', 'codex']

    # Debug → Grok SOLO (2M context scans everything)
    if has_debug:
        return 'debug', ['grok']

    # Research → DeepSeek SOLO (cheapest paid model)
    if has_research and not has_code:
        return 'research', ['deepseek']

    # Code → Grok SOLO (single engineer, not dual)
    if has_code:
        return 'code', ['grok']

    # Default → DeepSeek (cheapest paid fallback)
    return 'general', ['deepseek']


SYSTEM_PROMPTS = {
    'grok': "Lead engineer + debugger. 2M context. Code first, minimal prose. Production-ready.",
    'codex': "Engineer + reviewer. Clean code, spot bugs. Concise.",
    'opus': "System architect. Design decisions, tradeoffs, component boundaries. No code unless asked.",
    'deepseek': "Researcher. Technical analysis, comparisons, reasoning. Concise.",
}


def run_pipeline(user_message):
    """Main pipeline: classify → execute → review → present."""
    start = time.time()
    task_type, models_needed = classify_task(user_message)

    result = {
        'task_type': task_type,
        'models_used': [],
        'tokens': {'input': 0, 'output': 0},
    }

    # ─── CHAT ONLY: Gemma handles it, zero paid tokens ───
    if task_type == 'chat':
        text, tokens = call_model('gemma',
            "Leviathan dev team interface. Direct, concise answers.",
            user_message, max_tokens=800)
        result['response'] = text or "I'm here. What do you need?"
        result['models_used'] = ['Gemma 3']
        if isinstance(tokens, dict):
            result['tokens'] = tokens
        result['processing_time'] = f"{time.time() - start:.2f}s"
        return result

    # ─── LARGE INPUT: Grok ingests, summarizes, distributes ───
    if task_type == 'large_input':
        text, tokens = call_model('grok',
            "You received a large input. Analyze it thoroughly. Provide a structured summary and action plan.",
            user_message, max_tokens=2000)
        result['response'] = text or "Failed to process large input."
        result['models_used'] = ['Grok']
        if isinstance(tokens, dict):
            result['tokens'] = tokens
        result['processing_time'] = f"{time.time() - start:.2f}s"
        return result

    # ─── TASK EXECUTION: Call heavy models in parallel ───
    futures = {}
    for model_key in models_needed:
        sp = SYSTEM_PROMPTS.get(model_key, "Provide your expert analysis.")
        future = executor.submit(call_model, model_key, sp, user_message)
        futures[future] = model_key

    responses = {}
    try:
        for future in as_completed(futures, timeout=30):
            model_key = futures[future]
            try:
                text, tokens = future.result(timeout=3)
                if text:
                    responses[model_key] = text
                    result['models_used'].append(MODELS[model_key]['name'])
                    if isinstance(tokens, dict):
                        result['tokens']['input'] += tokens.get('input', 0)
                        result['tokens']['output'] += tokens.get('output', 0)
            except Exception as e:
                logger.warning(f"[{model_key}] failed: {e}")
    except TimeoutError:
        logger.warning("Parallel execution timeout, using collected responses")

    if not responses:
        result['response'] = "All models timed out. Try a simpler request."
        result['processing_time'] = f"{time.time() - start:.2f}s"
        return result

    # ─── CODE REVIEW PIPELINE (for code tasks with 2+ responses) ───
    if task_type == 'code' and len(responses) >= 2:
        # Quick cross-review: each model's code gets checked by the other
        # Use Gemma to synthesize (free) instead of burning paid tokens
        combined = "\n\n".join(f"[{MODELS[k]['name']}]:\n{v}" for k, v in responses.items())
        review_text, _ = call_model('gemma',
            "Merge engineer outputs into one clean solution. Keep code blocks. Concise.",
            f"Task: {user_message}\n\nOutputs:\n{combined}",
            max_tokens=1500)
        result['response'] = review_text or combined
        result['models_used'].append('Gemma 3 (synthesis)')
    elif len(responses) > 1:
        # Multiple non-code responses: Gemma synthesizes (free)
        combined = "\n\n".join(f"[{MODELS[k]['name']}]:\n{v}" for k, v in responses.items())
        synth_text, _ = call_model('gemma',
            "Merge these into one concise answer.",
            f"Task: {user_message}\n\nResponses:\n{combined}",
            max_tokens=1200)
        result['response'] = synth_text or combined
        result['models_used'].append('Gemma 3 (synthesis)')
    else:
        # Single response: pass through
        result['response'] = list(responses.values())[0]

    result['processing_time'] = f"{time.time() - start:.2f}s"
    return result


# ─── Flask Routes ──────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.json
        msg = data.get('message', '').strip()
        if not msg:
            return jsonify({'error': 'Empty message'}), 400
        result = run_pipeline(msg)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '4.3-lean', 'timestamp': datetime.now().isoformat()})


@app.route('/status')
def status():
    return jsonify({
        'version': '4.3-lean',
        'architecture': 'Gemma bridge + paid model execution',
        'models': {k: {'name': v['name'], 'role': v['role'], 'cost': v['cost']} for k, v in MODELS.items()},
        'api_keys': {k: bool(v) for k, v in API_KEYS.items()},
    })


# ─── Chat UI ──────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Leviathan Dev Team</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0e27;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}
header{background:#111830;border-bottom:1px solid #2a3550;padding:16px 20px}
h1{font-size:20px;background:linear-gradient(135deg,#00d4ff,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{font-size:11px;color:#666;margin-top:4px}
#msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:75%;padding:10px 14px;border-radius:8px;font-size:14px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}
.msg.u{align-self:flex-end;background:#5b21b6;color:#fff}
.msg.a{align-self:flex-start;background:#1a2332;border:1px solid #2a3550}
.meta{font-size:10px;color:#00d4ff;margin-top:6px;opacity:.7}
.bar{background:#111830;border-top:1px solid #2a3550;padding:12px 16px;display:flex;gap:8px}
.bar input{flex:1;background:#1a2332;border:1px solid #2a3550;color:#e0e0e0;padding:10px 14px;border-radius:6px;font-size:14px;outline:none}
.bar input:focus{border-color:#7c3aed}
.bar button{background:#7c3aed;border:none;color:#fff;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:14px}
.bar button:disabled{opacity:.4}
.dot{display:inline-block;width:6px;height:6px;background:#00d4ff;border-radius:50%;animation:p 1s infinite}
.dot:nth-child(2){animation-delay:.2s}.dot:nth-child(3){animation-delay:.4s}
@keyframes p{0%,100%{opacity:.2}50%{opacity:1}}
</style>
</head>
<body>
<header>
<h1>Leviathan Dev Team</h1>
<div class="sub">Gemma 3 (bridge) · Grok · Codex · Opus · DeepSeek</div>
</header>
<div id="msgs"></div>
<div class="bar">
<input id="inp" placeholder="Talk to your dev team..." autocomplete="off">
<button id="btn" onclick="send()">Send</button>
</div>
<script>
const msgs=document.getElementById('msgs'),inp=document.getElementById('inp'),btn=document.getElementById('btn');
function add(text,isUser,meta){
  const d=document.createElement('div');d.className='msg '+(isUser?'u':'a');
  d.textContent=text;
  if(meta){const m=document.createElement('div');m.className='meta';m.textContent=meta;d.appendChild(m)}
  msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;
}
async function send(){
  const m=inp.value.trim();if(!m)return;
  add(m,true);inp.value='';btn.disabled=true;
  const ld=document.createElement('div');ld.className='msg a';
  ld.innerHTML='<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  msgs.appendChild(ld);msgs.scrollTop=msgs.scrollHeight;
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
    const d=await r.json();msgs.removeChild(ld);
    const meta=d.models_used?.length?d.models_used.join(' · ')+' · '+d.processing_time:'';
    add(d.response||d.error||'No response',false,meta);
  }catch(e){msgs.removeChild(ld);add('Error: '+e.message,false)}
  btn.disabled=false;
}
inp.addEventListener('keypress',e=>{if(e.key==='Enter')send()});
</script>
</body>
</html>"""


@app.route('/')
def index():
    return HTML


# ─── Discord Bot ─────────────────────────────────────────────

DISCORD_TOKEN = os.environ.get('DISCORD_BOT_TOKEN_DEVTEAM', '')
DISCORD_GUILD_ID = 1477804209842815382

discord_bot = None

def start_discord_bot():
    """Run Discord bot in background thread alongside Flask."""
    global discord_bot
    if not DISCORD_TOKEN:
        logger.warning("No DISCORD_BOT_TOKEN_DEVTEAM set, skipping Discord bot")
        return

    try:
        import discord
    except ImportError:
        logger.error("discord.py not installed, skipping Discord bot")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    bot = discord.Client(intents=intents)
    discord_bot = bot

    @bot.event
    async def on_ready():
        logger.info(f"Discord bot connected as {bot.user} (ID: {bot.user.id})")
        guild = bot.get_guild(DISCORD_GUILD_ID)
        if guild:
            logger.info(f"Connected to guild: {guild.name}")
        else:
            logger.warning(f"Guild {DISCORD_GUILD_ID} not found — bot may not be invited yet")

    @bot.event
    async def on_message(message):
        # Ignore own messages
        if message.author == bot.user:
            return

        # Strip mentions if present
        content = message.content
        if bot.user in (message.mentions or []):
            content = content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        if content.startswith('!team'):
            content = content[5:].strip()

        if not content:
            await message.reply("What do you need? Send me a message and the dev team will handle it.")
            return

        # Show typing while processing
        async with message.channel.typing():
            # Run pipeline in thread pool (it uses blocking requests)
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(None, run_pipeline, content)
                response_text = result.get('response', 'No response generated.')
                models = result.get('models_used', [])
                proc_time = result.get('processing_time', '?')

                # Build footer
                footer = f"\n-# {' · '.join(models)} · {proc_time}" if models else ""

                full_response = response_text + footer

                # Discord max is 2000 chars — chunk if needed
                if len(full_response) <= 2000:
                    await message.reply(full_response)
                else:
                    # Send in chunks, reply first, then follow-up
                    chunks = []
                    while full_response:
                        if len(full_response) <= 2000:
                            chunks.append(full_response)
                            break
                        # Find a good split point
                        split_at = full_response.rfind('\n', 0, 1990)
                        if split_at < 500:
                            split_at = 1990
                        chunks.append(full_response[:split_at])
                        full_response = full_response[split_at:].lstrip()

                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply(chunk)
                        else:
                            await message.channel.send(chunk)

            except Exception as e:
                logger.error(f"Discord pipeline error: {e}", exc_info=True)
                await message.reply(f"Error processing your request: {str(e)[:200]}")

    def _run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(bot.start(DISCORD_TOKEN))
        except Exception as e:
            logger.error(f"Discord bot crashed: {e}", exc_info=True)

    thread = threading.Thread(target=_run_bot, daemon=True, name="discord-bot")
    thread.start()
    logger.info("Discord bot thread started")


# Auto-start Discord bot when module loads (works with gunicorn)
start_discord_bot()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Super Brain Dev Team v4.2 starting on :{port}")
    logger.info(f"Models: Gemma (bridge) + Grok + Codex + Opus + DeepSeek")
    logger.info(f"Discord: {'enabled' if DISCORD_TOKEN else 'disabled (no token)'}")
    app.run(host='0.0.0.0', port=port)
