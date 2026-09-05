# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import random
import logging
import asyncio
import aiohttp
import requests
from typing import Dict, List, Tuple, Optional, Any
from pyrogram import Client
from pyrogram.raw.functions.channels import GetForumTopics, CreateForumTopic
from pyrogram.errors import RPCError, FloodWait

logger = logging.getLogger("TopicUtils")

def clean_item_name(name: str) -> str:
    """Cleans up item name while preserving regional language characters (Gujarati, Hindi, etc.)"""
    # Remove leading emoji prefixes and separators
    name = re.sub(r'^[📄🎥📝🖼️📕🎬📂📁\s\-\:]+', '', name)
    # Remove unwanted trailing/leading symbols
    name = name.strip(" :-\t\r\n")
    # Clean up illegal filesystem chars for when used as filename
    safe_name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return safe_name if safe_name else "Resource"

def parse_course_txt(file_path: str) -> Dict[str, Any]:
    """
    Parses both structured (.txt with 📁 / 📂 folder breadcrumbs) and flat text files.
    
    Topic Grouping Rule:
      - Ignores 'Home'.
      - Forum Topic Name is the Middle / Subject folder (e.g. ભુગોળ, ઈતિહાસ, etc.).
      - Chapter Title is the 3rd part / chapter subfolder (e.g. પૃથ્વીનો ઉદભવ તેમજ પૃથ્વીની આંતરિક સંરચના).
      - Flat files get assigned to a single 'General' topic and chapter.
    """
    content = ""
    # Try multiple encodings
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
            break
        except Exception:
            continue
            
    if not content:
        raise ValueError("Could not read file content or file is empty.")

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    
    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None
    
    # Check if this file has structured folder headers
    has_folder_headers = any(line.startswith(('📁', '📂', 'Folder:')) for line in lines)
    
    global_index = 0
    pdf_count = 0
    video_count = 0
    img_count = 0
    other_count = 0

    for line in lines:
        if line.startswith(('📁', '📂', 'Folder:')):
            raw_path = re.sub(r'^(📁|📂|Folder:)\s*', '', line).strip()
            # Split breadcrumbs by '»', '>', or '/'
            parts = [p.strip() for p in re.split(r'»|>|/', raw_path) if p.strip()]
            # Filter out 'Home'
            clean_parts = [p for p in parts if p.lower() != 'home']
            if not clean_parts:
                clean_parts = ['General']
                
            if len(clean_parts) == 1:
                topic_name = clean_parts[0]
                chapter_title = clean_parts[0]
            else:
                topic_name = clean_parts[0]  # Subject (middle folder)
                chapter_title = ' » '.join(clean_parts[1:])  # Chapter / Subfolder
                
            current_chapter = {
                'topic_name': topic_name,
                'chapter_title': chapter_title,
                'full_path': raw_path,
                'items': []
            }
            chapters.append(current_chapter)
            
        elif line.startswith(('──', '==', '--', '┄┄', '━━')):
            # Divider line, ignore
            continue
            
        elif '://' in line:
            # Resource item
            m = re.match(r'^(?:[📄🎥📝🖼️📕🎬\s]*)(.*?)\s*:\s*(https?://\S+)', line)
            if m:
                raw_name = m.group(1).strip()
                item_url = m.group(2).strip()
            else:
                p = line.split('://', 1)
                raw_name = p[0].strip(' :📄🎥📝🖼️📕🎬')
                protocol = 'http://' if p[0].endswith('http') else 'https://'
                item_url = protocol + p[1].strip()
                
            clean_name = clean_item_name(raw_name)
            
            # Determine type
            url_lower = item_url.lower()
            if '.pdf' in url_lower:
                item_type = 'pdf'
                pdf_count += 1
            elif any(ext in url_lower for ext in ('.png', '.jpg', '.jpeg', '.webp')):
                item_type = 'image'
                img_count += 1
            elif any(x in url_lower for x in ('.mp4', '.mkv', '.m3u8', '.mpd', 'drm', 'v2', 'youtu', 'encrypted.m')):
                item_type = 'video'
                video_count += 1
            else:
                item_type = 'other'
                other_count += 1
                
            global_index += 1
            item = {
                'index': global_index,
                'index_str': str(global_index).zfill(3),
                'raw_name': raw_name,
                'clean_name': clean_name,
                'url': item_url,
                'type': item_type,
                'topic_name': current_chapter['topic_name'] if current_chapter else 'General',
                'chapter_title': current_chapter['chapter_title'] if current_chapter else 'General'
            }
            
            if current_chapter is None:
                current_chapter = {
                    'topic_name': 'General',
                    'chapter_title': 'General',
                    'full_path': 'General',
                    'items': []
                }
                chapters.append(current_chapter)
                
            current_chapter['items'].append(item)

    # Filter out empty chapters if any
    chapters = [ch for ch in chapters if ch['items']]

    # Build topic-level grouping
    topics_dict: Dict[str, List[Dict[str, Any]]] = {}
    for ch in chapters:
        t_name = ch['topic_name']
        if t_name not in topics_dict:
            topics_dict[t_name] = []
        topics_dict[t_name].append(ch)

    stats = {
        'total_items': global_index,
        'total_chapters': len(chapters),
        'total_topics': len(topics_dict),
        'pdf': pdf_count,
        'video': video_count,
        'image': img_count,
        'other': other_count,
        'is_structured': has_folder_headers
    }
    
    return {
        'chapters': chapters,
        'topics_dict': topics_dict,
        'stats': stats
    }


class ForumManager:
    """Manages Telegram Forum Topic discovery, creation, and caching."""
    def __init__(self, bot: Client, bot_token: str = ""):
        self.bot = bot
        self.bot_token = bot_token
        # Cache: {chat_id: {normalized_topic_name: thread_id}}
        self.cache: Dict[str, Dict[str, int]] = {}

    async def init_chat(self, chat_id: Any) -> bool:
        """Initializes forum topic cache by scanning existing topics in the group."""
        chat_key = str(chat_id)
        if chat_key not in self.cache:
            self.cache[chat_key] = {}

        try:
            peer = await self.bot.resolve_peer(chat_id)
            offset_topic = 0
            while True:
                res = await self.bot.invoke(GetForumTopics(
                    channel=peer,
                    offset_date=0,
                    offset_id=0,
                    offset_topic=offset_topic,
                    limit=100
                ))
                if not hasattr(res, 'topics') or not res.topics:
                    break
                for t in res.topics:
                    if hasattr(t, 'title') and hasattr(t, 'id'):
                        norm_title = t.title.strip().lower()
                        self.cache[chat_key][norm_title] = t.id
                if len(res.topics) < 100:
                    break
                offset_topic = res.topics[-1].id
            logger.info(f"Loaded {len(self.cache[chat_key])} existing forum topics for chat {chat_key}")
            return True
        except Exception as e:
            logger.warning(f"Could not load forum topics via MTProto for {chat_key}: {e}")
            return False

    async def get_or_create_topic(self, chat_id: Any, topic_name: str) -> Optional[int]:
        """
        Checks if topic already exists; if yes, returns its thread_id.
        If not, creates the topic and returns the new thread_id.
        """
        chat_key = str(chat_id)
        if chat_key not in self.cache:
            self.cache[chat_key] = {}

        norm_name = topic_name.strip().lower()
        if norm_name in self.cache[chat_key]:
            return self.cache[chat_key][norm_name]

        # Topic not found in cache, attempt to create via Telegram Bot API
        clean_title = topic_name.strip()[:128]
        new_thread_id = None

        if self.bot_token:
            try:
                api_url = f"https://api.telegram.org/bot{self.bot_token}/createForumTopic"
                payload = {"chat_id": chat_id, "name": clean_title}
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        data = await resp.json()
                        if data.get("ok"):
                            new_thread_id = data["result"]["message_thread_id"]
                        else:
                            logger.error(f"Bot API createForumTopic error: {data.get('description')}")
            except Exception as e:
                logger.error(f"Error calling createForumTopic via HTTP: {e}")

        # Fallback to Pyrogram MTProto CreateForumTopic if Bot API failed
        if not new_thread_id:
            try:
                peer = await self.bot.resolve_peer(chat_id)
                rnd = random.randint(100000, 99999999)
                res = await self.bot.invoke(CreateForumTopic(
                    channel=peer,
                    title=clean_title,
                    random_id=rnd
                ))
                # Search for created message id in updates
                if hasattr(res, 'updates'):
                    for u in res.updates:
                        if hasattr(u, 'message') and hasattr(u.message, 'id'):
                            new_thread_id = u.message.id
                            break
            except Exception as e:
                logger.error(f"Error calling CreateForumTopic via MTProto: {e}")

        if new_thread_id:
            self.cache[chat_key][norm_name] = new_thread_id
            return new_thread_id
            
        return None
