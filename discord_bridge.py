#!/usr/bin/env python3
"""
Leviathan Discord Bridge — Cloud & Brain Bots
==============================================
Bridges DISCORD_BOT_TOKEN_CLOUD and DISCORD_BOT_TOKEN_BRAIN to the
OpenFang kernel API. Each bot runs its own Discord gateway connection
and forwards messages to the appropriate agent via HTTP API.

This exists because the upstream OpenFang binary (v0.2.3) does not include
our extra_discord multi-bot routing code. The CTO bot connects natively
through the kernel's built-in Discord adapter; Cloud and Brain use this bridge.

Architecture:
  Discord Gateway (Cloud) → discord_bridge.py → POST /api/agents/{cloud_id}/message
  Discord Gateway (Brain) → discord_bridge.py → POST /api/agents/{brain_id}/message
"""

import asyncio
import os
import sys
import logging
import json
import aiohttp
import discord
from discord import Intents

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
log = logging.getLogger('discord_bridge')

API_URL = os.environ.get('OPENFANG_API_URL', 'http://localhost:4200')
API_KEY = os.environ.get('OPENFANG_API_KEY', 'leviathan-test-key-2026')
GUILD_ID = int(os.environ.get('DISCORD_GUILD_ID', '1475947548811202613'))


async def get_agent_id(session: aiohttp.ClientSession, agent_name: str) -> str | None:
    """Fetch agent ID by name from the kernel API."""
    try:
        async with session.get(
            f'{API_URL}/api/agents',
            headers={'Authorization': f'Bearer {API_KEY}'}
        ) as resp:
            if resp.status == 200:
                agents = await resp.json()
                for a in agents:
                    if a['name'] == agent_name:
                        return a['id']
    except Exception as e:
        log.error(f'Failed to fetch agent ID for {agent_name}: {e}')
    return None


async def send_to_agent(
    session: aiohttp.ClientSession,
    agent_id: str,
    content: str,
    author: str,
    channel_name: str = '',
    reply_context: str = ''
) -> str | None:
    """Send a message to an agent via the kernel API and return the response."""
    # Build the message with context
    parts = []
    if channel_name:
        parts.append(f'[#{channel_name}]')
    if reply_context:
        parts.append(reply_context)
    parts.append(f'{author}: {content}')
    full_message = ' '.join(parts)

    try:
        async with session.post(
            f'{API_URL}/api/agents/{agent_id}/message',
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            },
            json={'message': full_message},
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('response', '')
            else:
                text = await resp.text()
                log.error(f'Agent API returned {resp.status}: {text[:200]}')
    except asyncio.TimeoutError:
        log.error(f'Agent {agent_id} timed out after 120s')
    except Exception as e:
        log.error(f'Failed to send to agent {agent_id}: {e}')
    return None


class BridgeBot(discord.Client):
    """Discord bot that bridges messages to an OpenFang agent."""

    def __init__(self, bot_name: str, agent_name: str, respond_policy: str = 'mention', **kwargs):
        """
        Args:
            bot_name: Display name for logging (e.g., "Cloud", "Brain")
            agent_name: OpenFang agent name (e.g., "neural-net", "brain")
            respond_policy: "all" = respond to all messages, "mention" = only @mentions/DMs,
                           "channels" = only in specific channel IDs
        """
        super().__init__(**kwargs)
        self.bot_name = bot_name
        self.agent_name = agent_name
        self.respond_policy = respond_policy
        self.agent_id: str | None = None
        self.http_session: aiohttp.ClientSession | None = None
        # Brain: only respond in these channels
        self.allowed_channels: set[int] = set()

    async def on_ready(self):
        log.info(f'{self.bot_name} bot ready: {self.user} (ID: {self.user.id})')
        self.http_session = aiohttp.ClientSession()
        # Resolve agent ID
        for attempt in range(10):
            self.agent_id = await get_agent_id(self.http_session, self.agent_name)
            if self.agent_id:
                log.info(f'{self.bot_name} → agent {self.agent_name} (ID: {self.agent_id})')
                break
            log.warning(f'{self.bot_name}: agent {self.agent_name} not found, retry {attempt+1}/10...')
            await asyncio.sleep(5)
        if not self.agent_id:
            log.error(f'{self.bot_name}: could not find agent {self.agent_name} after 10 retries')

    async def on_message(self, message: discord.Message):
        # Ignore own messages and other bots
        if message.author == self.user or message.author.bot:
            return

        # Guild filter
        if message.guild and message.guild.id != GUILD_ID:
            return

        # Check if we should respond
        should_respond = False

        if isinstance(message.channel, discord.DMChannel):
            should_respond = True
        elif self.respond_policy == 'all':
            # Cloud: respond to all guild messages
            should_respond = True
        elif self.respond_policy == 'mention':
            # Only respond to @mentions
            should_respond = self.user in message.mentions
        elif self.respond_policy == 'channels':
            # Brain: only respond in allowed channels
            should_respond = message.channel.id in self.allowed_channels

        if not should_respond:
            return

        if not self.agent_id:
            # Try to resolve again
            if self.http_session:
                self.agent_id = await get_agent_id(self.http_session, self.agent_name)
            if not self.agent_id:
                log.warning(f'{self.bot_name}: no agent_id, cannot respond')
                return

        # Build reply context from referenced message
        reply_context = ''
        if message.reference and message.reference.resolved:
            ref = message.reference.resolved
            if isinstance(ref, discord.Message):
                ref_content = ref.content[:200] if ref.content else ''
                reply_context = f'[Replying to @{ref.author.display_name}: "{ref_content}"]'

        # Get channel name
        channel_name = ''
        if hasattr(message.channel, 'name'):
            channel_name = message.channel.name

        # Show typing while processing
        async with message.channel.typing():
            response = await send_to_agent(
                self.http_session,
                self.agent_id,
                message.content,
                message.author.display_name,
                channel_name=channel_name,
                reply_context=reply_context
            )

        if response:
            # Split long messages (Discord 2000 char limit)
            chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
            for chunk in chunks:
                await message.channel.send(chunk)

    async def close(self):
        if self.http_session:
            await self.http_session.close()
        await super().close()


async def run_bridge():
    """Launch Cloud and Brain bots concurrently."""
    cloud_token = os.environ.get('DISCORD_BOT_TOKEN_CLOUD')
    brain_token = os.environ.get('DISCORD_BOT_TOKEN_BRAIN')

    if not cloud_token and not brain_token:
        log.warning('No DISCORD_BOT_TOKEN_CLOUD or DISCORD_BOT_TOKEN_BRAIN set. Bridge idle.')
        # Keep running so the process doesn't exit
        await asyncio.Event().wait()
        return

    intents = Intents.default()
    intents.message_content = True
    intents.guilds = True

    tasks = []

    if cloud_token:
        cloud_bot = BridgeBot(
            bot_name='Cloud',
            agent_name='neural-net',
            respond_policy='all',
            intents=intents
        )
        tasks.append(cloud_bot.start(cloud_token))
        log.info('Cloud bot bridge starting (respond_policy=all)')
    else:
        log.warning('DISCORD_BOT_TOKEN_CLOUD not set — Cloud bot disabled')

    if brain_token:
        brain_intents = Intents.default()
        brain_intents.message_content = True
        brain_intents.guilds = True
        brain_bot = BridgeBot(
            bot_name='Brain',
            agent_name='brain',
            respond_policy='channels',
            intents=brain_intents
        )
        # Brain only responds in #meta-prompting and #agent-prompting
        brain_bot.allowed_channels = {1476978586828411073, 1477054899161141402}
        tasks.append(brain_bot.start(brain_token))
        log.info('Brain bot bridge starting (channels: meta-prompting, agent-prompting)')
    else:
        log.warning('DISCORD_BOT_TOKEN_BRAIN not set — Brain bot disabled')

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        asyncio.run(run_bridge())
    except KeyboardInterrupt:
        log.info('Bridge shutting down')
    except Exception as e:
        log.error(f'Bridge crashed: {e}', exc_info=True)
        sys.exit(1)
