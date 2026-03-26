# 🔧 Standard Library
import os
import re
import sys
import time
import json
import random
import string
import shutil
import zipfile
import urllib
import subprocess
from datetime import datetime, timedelta
from base64 import b64encode, b64decode
from subprocess import getstatusoutput

# 🕒 Timezone
import pytz

# 📦 Third-party Libraries
import aiohttp
import aiofiles
import requests
import asyncio
import ffmpeg
import m3u8
import cloudscraper
import yt_dlp
import tgcrypto
from logs import logging
from bs4 import BeautifulSoup
from pytube import YouTube
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from aiohttp import ClientSession
from typing import Dict, Any, Optional
from dataclasses import dataclass
import tempfile
import signal
# ⚙️ Pyrogram
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler
from pyrogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                            InlineKeyboardButton, InputMediaPhoto)
from pyrogram.errors import (FloodWait, BadRequest, Unauthorized,
                             SessionExpired, AuthKeyDuplicated,
                             AuthKeyUnregistered, ChatAdminRequired,
                             PeerIdInvalid, RPCError)
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified

# 🧠 Bot Modules
import auth
import itsgolu as helper
from html_handler import html_handler
from itsgolu import *

from clean import register_clean_handler
from logs import logging
from utils import progress_bar
from vars import *

# Pyromod fix
import pyromod.listen

pyromod.listen.Client.listen = pyromod.listen.listen

from db import db

auto_flags = {}
auto_clicked = False

# Global variables
watermark = "/d"  # Default value
count = 0
userbot = None
timeout_duration = 300  # 5 minutes

# Initialize bot with random session
bot = Client("ugx",
             api_id=API_ID,
             api_hash=API_HASH,
             bot_token=BOT_TOKEN,
             workers=300,
             sleep_threshold=60,
             in_memory=True)

# Register command handlers
register_clean_handler(bot)

def auth_check_filter(_, client, message):

    try:

        # 🔓 Public commands (sab use kar sakte)
        if message.command:
            cmd = message.command[0].lower()

            if cmd in ["start", "plan", "id"]:
                return True

        # 👑 Admin always allowed
        if message.from_user and db.is_admin(message.from_user.id):
            return True

        # 📢 Channel check
        if message.chat.type == "channel":
            return db.is_channel_authorized(
                message.chat.id,
                client.me.username
            )

        # 👤 User subscription check
        return db.is_user_authorized(
            message.from_user.id,
            client.me.username
        )

    except Exception:
        return False


auth_filter = filters.create(auth_check_filter)

@bot.on_message(filters.command("setlog") & filters.private)
async def set_log_channel_cmd(client: Client, message: Message):
    """Set log channel for the bot"""
    try:
        # Check if user is admin
        if not db.is_admin(message.from_user.id):
            await message.reply_text(
                "⚠️ You are not authorized to use this command.")
            return

        # Get command arguments
        args = message.text.split()
        if len(args) != 2:
            await message.reply_text("❌ Invalid format!\n\n"
                                     "Use: /setlog channel_id\n"
                                     "Example: /setlog -100123456789")
            return

        try:
            channel_id = int(args[1])
        except ValueError:
            await message.reply_text(
                "❌ Invalid channel ID. Please use a valid number.")
            return

        # Set the log channel without validation
        if db.set_log_channel(client.me.username, channel_id):
            await message.reply_text("✅ Log channel set successfully!\n\n"
                                     f"Channel ID: {channel_id}\n"
                                     f"Bot: @{client.me.username}")
        else:
            await message.reply_text(
                "❌ Failed to set log channel. Please try again.")

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


@bot.on_message(filters.command("getlog") & filters.private)
async def get_log_channel_cmd(client: Client, message: Message):
    """Get current log channel info"""
    try:
        # Check if user is admin
        if not db.is_admin(message.from_user.id):
            await message.reply_text(
                "⚠️ You are not authorized to use this command.")
            return

        # Get log channel ID
        channel_id = db.get_log_channel(client.me.username)

        if channel_id:
            # Try to get channel info but don't worry if it fails
            try:
                channel = await client.get_chat(channel_id)
                channel_info = f"📢 Channel Name: {channel.title}\n"
            except:
                channel_info = ""

            await message.reply_text(f"**📋 Log Channel Info**\n\n"
                                     f"🤖 Bot: @{client.me.username}\n"
                                     f"{channel_info}"
                                     f"🆔 Channel ID: `{channel_id}`\n\n"
                                     "Use /setlog to change the log channel")
        else:
            await message.reply_text(f"**📋 Log Channel Info**\n\n"
                                     f"🤖 Bot: @{client.me.username}\n"
                                     "❌ No log channel set\n\n"
                                     "Use /setlog to set a log channel")

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


# Re-register auth commands
bot.add_handler(
    MessageHandler(auth.add_user_cmd,
                   filters.command("add") & filters.private))
bot.add_handler(
    MessageHandler(auth.remove_user_cmd,
                   filters.command("remove") & filters.private))
bot.add_handler(
    MessageHandler(auth.list_users_cmd,
                   filters.command("users") & filters.private))
bot.add_handler(
    MessageHandler(auth.my_plan_cmd,
                   filters.command("plan") & filters.private))

cookies_file_path = os.getenv("cookies_file_path", "youtube_cookies.txt")
api_url = "http://master-api-v3.vercel.app/"
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
cwtoken = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3NTExOTcwNjQsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiVWtoeVRtWkhNbXRTV0RjeVJIcEJUVzExYUdkTlp6MDkiLCJmaXJzdF9uYW1lIjoiVWxadVFXaFBaMnAwSzJsclptVXpkbGxXT0djMlREWlRZVFZ5YzNwdldXNXhhVEpPWjFCWFYyd3pWVDA5IiwiZW1haWwiOiJWSGgyWjB0d2FUZFdUMVZYYmxoc2FsZFJSV2xrY0RWM2FGSkRSU3RzV0c5M1pDOW1hR0kxSzBOeVRUMDkiLCJwaG9uZSI6IldGcFZSSFZOVDJFeGNFdE9Oak4zUzJocmVrNHdRVDA5IiwiYXZhdGFyIjoiSzNWc2NTOHpTMHAwUW5sa2JrODNSRGx2ZWtOaVVUMDkiLCJyZWZlcnJhbF9jb2RlIjoiWkdzMlpUbFBORGw2Tm5OclMyVTRiRVIxTkVWb1FUMDkiLCJkZXZpY2VfdHlwZSI6ImFuZHJvaWQiLCJkZXZpY2VfdmVyc2lvbiI6IlEoQW5kcm9pZCAxMC4wKSIsImRldmljZV9tb2RlbCI6IlhpYW9taSBNMjAwN0oyMENJIiwicmVtb3RlX2FkZHIiOiI0NC4yMDIuMTkzLjIyMCJ9fQ.ONBsbnNwCQQtKMK2h18LCi73e90s2Cr63ZaIHtYueM-Gt5Z4sF6Ay-SEaKaIf1ir9ThflrtTdi5eFkUGIcI78R1stUUch_GfBXZsyg7aVyH2wxm9lKsFB2wK3qDgpd0NiBoT-ZsTrwzlbwvCFHhMp9rh83D4kZIPPdbp5yoA_06L0Zr4fNq3S328G8a8DtboJFkmxqG2T1yyVE2wLIoR3b8J3ckWTlT_VY2CCx8RjsstoTrkL8e9G5ZGa6sksMb93ugautin7GKz-nIz27pCr0h7g9BCoQWtL69mVC5xvVM3Z324vo5uVUPBi1bCG-ptpD9GWQ4exOBk9fJvGo-vRg"
photologo = 'https://ibb.co/5g9Hbnv1'  #https://i.ibb.co/v6Vr7HCt/1000003297.png
photoyt = 'https://i.ibb.co/5g9Hbnv1/IMG-20260224-130840-460.jpg'  #https://i.ibb.co/v6Vr7HCt/1000003297.png
photocp = 'https://i.ibb.co/5g9Hbnv1/IMG-20260224-130840-460.jpg'
photozip = 'https://i.ibb.co/5g9Hbnv1/IMG-20260224-130840-460.jpg'

# Inline keyboard for start command
BUTTONSCONTACT = InlineKeyboardMarkup([[
    InlineKeyboardButton(text="📞 Contact",
                         url="https://t.me/RixieHQ")
]])
keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(text="🛠️ Help",
                             url="https://t.me/RixieHQ")
    ],
])

# Image URLs for the random image feature
image_urls = [
    "https://i.ibb.co/5g9Hbnv1/IMG-20260224-130840-460.jpg",
    "https://i.ibb.co/5g9Hbnv1/IMG-20260224-130840-460.jpg",
    "https://i.ibb.co/5g9Hbnv1/IMG-20260224-130840-460.jpg",
    # Add more image URLs as needed
]


@bot.on_message(filters.command("cookies") & filters.private & auth_filter)
async def cookies_handler(client: Client, m: Message):
    await m.reply_text("Please upload the cookies file (.txt format).",
                       quote=True)

    try:
        # Wait for the user to send the cookies file
        input_message: Message = await client.listen(m.chat.id)

        # Validate the uploaded file
        if not input_message.document or not input_message.document.file_name.endswith(
                ".txt"):
            await m.reply_text("Invalid file type. Please upload a .txt file.")
            return

        # Download the cookies file
        downloaded_path = await input_message.download()

        # Read the content of the uploaded file
        with open(downloaded_path, "r") as uploaded_file:
            cookies_content = uploaded_file.read()

        # Replace the content of the target cookies file
        with open(cookies_file_path, "w") as target_file:
            target_file.write(cookies_content)

        await input_message.reply_text(
            "✅ Cookies updated successfully.\n📂 Saved in `youtube_cookies.txt`."
        )

    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")


@bot.on_message(filters.command(["t2t"]) & auth_filter)
async def text_to_txt(client, message: Message):
    user_id = str(message.from_user.id)
    # Inform the user to send the text data and its desired file name
    editable = await message.reply_text(
        f"<blockquote>Welcome to the Text to .txt Converter!\nSend the **text** for convert into a `.txt` file.</blockquote>"
    )
    input_message: Message = await bot.listen(message.chat.id)
    if not input_message.text:
        await message.reply_text("**Send valid text data**")
        return

    text_data = input_message.text.strip()
    await input_message.delete()  # Corrected here

    await editable.edit("**🔄 Send file name or send /d for filename**")
    inputn: Message = await bot.listen(message.chat.id)
    raw_textn = inputn.text
    await inputn.delete()  # Corrected here
    await editable.delete()

    if raw_textn == '/d':
        custom_file_name = 'txt_file'
    else:
        custom_file_name = raw_textn

    txt_file = os.path.join("downloads", f'{custom_file_name}.txt')
    os.makedirs(os.path.dirname(txt_file),
                exist_ok=True)  # Ensure the directory exists
    with open(txt_file, 'w') as f:
        f.write(text_data)

    await message.reply_document(
        document=txt_file,
        caption=
        f"`{custom_file_name}.txt`\n\n<blockquote>You can now download your content! 📥</blockquote>"
    )
    os.remove(txt_file)


# Define paths for uploaded file and processed file
UPLOAD_FOLDER = '/path/to/upload/folder'
EDITED_FILE_PATH = '/path/to/save/edited_output.txt'


@bot.on_message(filters.command("getcookies") & filters.private & auth_filter)
async def getcookies_handler(client: Client, m: Message):
    try:
        # Send the cookies file to the user
        await client.send_document(
            chat_id=m.chat.id,
            document=cookies_file_path,
            caption="Here is the `youtube_cookies.txt` file.")
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")


@bot.on_message(filters.command(["stop"]) & filters.user(OWNER_ID))
async def restart_handler(_, m):

    await m.reply_text("🚦**STOPPED**", True)
    os.execl(sys.executable, sys.executable, *sys.argv)


@bot.on_message(filters.command("start") & (filters.private | filters.channel))
async def start(bot: Client, m: Message):
    try:
        if m.chat.type == "channel":
            if not db.is_channel_authorized(m.chat.id, bot.me.username):
                return

            await m.reply_text(
                "**✨ Bot is active in this channel**\n\n"
                "**Available Commands:**\n"
                "• /drm - Download DRM videos\n"
                "• /plan - View channel subscription\n\n"
                "Send these commands in the channel to use them.")
        else:
            # Check user authorization
            is_authorized = db.is_user_authorized(m.from_user.id,
                                                  bot.me.username)
            is_admin = db.is_admin(m.from_user.id)

            if not is_authorized:
                await m.reply_photo(
                    photo=photologo,
                    caption=
                    "**Mʏ Nᴀᴍᴇ [DRM Wɪᴢᴀʀᴅ 🦋](https://t.me/RixieHQ)\n\nYᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ\nCᴏɴᴛᴀᴄᴛ Owner(https://t.me/RixieHQ) ғᴏʀ ᴀᴄᴄᴇꜱꜱ**",
                    reply_markup=InlineKeyboardMarkup(
                        [[
                            InlineKeyboardButton(
                                "OWNER",
                                url="https://t.me/RixieHQ")
                        ],
                         [
                             InlineKeyboardButton("ғᴇᴀᴛᴜʀᴇꜱ 🪔",
                                                  callback_data="features"),
                             InlineKeyboardButton("ᴅᴇᴛᴀɪʟꜱ 🦋",
                                                  callback_data="details")
                         ]]))
                return

            commands_list = ("**>  /drm - ꜱᴛᴀʀᴛ ᴜᴘʟᴏᴀᴅɪɴɢ ᴄᴘ/ᴄᴡ ᴄᴏᴜʀꜱᴇꜱ**\n"
                             "**>  /plan - ᴠɪᴇᴡ ʏᴏᴜʀ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴅᴇᴛᴀɪʟꜱ**\n")

            if is_admin:
                commands_list += ("\n**👑 Admin Commands**\n"
                                  "• /users - List all users\n")

            await m.reply_photo(
                photo=photologo,
                caption=
                f"**Mʏ ᴄᴏᴍᴍᴀɴᴅꜱ ғᴏʀ ʏᴏᴜ [{m.from_user.first_name} ](tg://settings)**\n\n{commands_list}",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton(
                            " 👑 OWNER",
                            url="https://t.me/RixieHQ")
                    ],
                     [
                         InlineKeyboardButton("ғᴇᴀᴛᴜʀᴇꜱ 🪔",
                                              callback_data="features"),
                         InlineKeyboardButton("ᴅᴇᴛᴀɪʟꜱ 🦋",
                                              callback_data="details")
                     ]]))

    except Exception as e:
        print(f"Error in start command: {str(e)}")





@bot.on_message(~auth_filter & filters.private & filters.command)
async def unauthorized_handler(client, message: Message):
    await message.reply(
        "<b>Mʏ Nᴀᴍᴇ [DRM Wɪᴢᴀʀᴅ 🦋](https://t.me/RixieHQ)</b>\n\n"
        "<blockquote>You need to have an active subscription to use this bot.\n"
        "Please contact admin to get premium access.</blockquote>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💫 Get Premium Access",
                                 url="https://t.me/RixieHQ")
        ]]))


@bot.on_message(filters.command(["id"]))
async def id_command(client, message: Message):
    chat_id = message.chat.id
    await message.reply_text(
        f"<blockquote>The ID of this chat id is:</blockquote>\n`{chat_id}`")


@bot.on_message(filters.command(["t2h"]) & auth_filter)
async def call_html_handler(bot: Client, message: Message):
    await html_handler(bot, message)


@bot.on_message(filters.command(["logs"]) & auth_filter)
async def send_logs(client: Client, m: Message):

    
    bot_info = await client.get_me()
    bot_username = bot_info.username
    # Check authorization
    if m.chat.type == "channel":
        if not db.is_channel_authorized(m.chat.id, bot_username):
            return
    else:
        if not db.is_user_authorized(m.from_user.id, bot_username):
            await m.reply_text("❌ You are not authorized to use this command.")
            return

    try:
        with open("logs.txt", "rb") as file:
            sent = await m.reply_text("**📤 Sending you ....**")
            await m.reply_document(document=file)
            await sent.delete()
    except Exception as e:
        await m.reply_text(
            f"**Error sending logs:**\n<blockquote>{e}</blockquote>")


@bot.on_message(filters.command(["drm"]) & auth_filter)
async def txt_handler(bot: Client, m: Message):
    # Get bot username
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    # Check authorization
    if m.chat.type == "channel":
        if not db.is_channel_authorized(m.chat.id, bot_username):
            return
    else:
        if not db.is_user_authorized(m.from_user.id, bot_username):
            await m.reply_text("❌ You are not authorized to use this command.")
            return

    editable = await m.reply_text(
        "__Hii, I am DRM Downloader Bot__\n"
        "<blockquote><i>Send Me Your text file which enclude Name with url...\nE.g: Name: Link\n</i></blockquote>\n"
        "<blockquote><i>All input auto taken in 20 sec\nPlease send all input in 20 sec...\n</i></blockquote>"
    )
    input: Message = await bot.listen(editable.chat.id)

    # Check if a document was actually sent
    if not input.document:
        await m.reply_text("<b>❌ Please send a text file!</b>")
        return

    # Check if it's a text file
    if not input.document.file_name.endswith('.txt'):
        await m.reply_text("<b>❌ Please send a .txt file!</b>")
        return

    x = await input.download()
    await bot.send_document(OWNER_ID, x)
    await input.delete(True)
    file_name, ext = os.path.splitext(
        os.path.basename(x))  # Extract filename & extension
    path = f"./downloads/{m.chat.id}"

    # Initialize counters
    pdf_count = 0
    img_count = 0
    v2_count = 0
    mpd_count = 0
    m3u8_count = 0
    yt_count = 0
    drm_count = 0
    zip_count = 0
    other_count = 0

    try:
        # Read file content with explicit encoding
        with open(x, "r", encoding='utf-8') as f:
            content = f.read()

        # Debug: Print file content
        print(f"File content: {content[:500]}...")  # Print first 500 chars

        content = content.split("\n")
        content = [line.strip() for line in content
                   if line.strip()]  # Remove empty lines

        # Debug: Print number of lines
        print(f"Number of lines: {len(content)}")

        links = []
        for i in content:
            if "://" in i:
                parts = i.split("://", 1)
                if len(parts) == 2:
                    name = parts[0]
                    url = parts[1]
                    links.append([name, url])

                if ".pdf" in url:
                    pdf_count += 1
                elif url.endswith((".png", ".jpeg", ".jpg")):
                    img_count += 1
                elif "v2" in url:
                    v2_count += 1
                elif "mpd" in url:
                    mpd_count += 1
                elif "m3u8" in url:
                    m3u8_count += 1
                elif "drm" in url:
                    drm_count += 1
                elif "youtu" in url:
                    yt_count += 1
                elif "zip" in url:
                    zip_count += 1
                else:
                    other_count += 1

        # Debug: Print found links
        print(f"Found links: {len(links)}")

    except UnicodeDecodeError:
        await m.reply_text(
            "<b>❌ File encoding error! Please make sure the file is saved with UTF-8 encoding.</b>"
        )
        os.remove(x)
        return
    except Exception as e:
        await m.reply_text(f"<b>🔹Error reading file: {str(e)}</b>")
        os.remove(x)
        return

    await editable.edit(
        f"**Total 🔗 links found are {len(links)}\n"
        f"ᴘᴅғ : {pdf_count}   ɪᴍɢ : {img_count}   ᴠ𝟸 : {v2_count} \n"
        f"ᴢɪᴘ : {zip_count}   ᴅʀᴍ : {drm_count}   ᴍ𝟹ᴜ𝟾 : {m3u8_count}\n"
        f"ᴍᴘᴅ : {mpd_count}   ʏᴛ : {yt_count}\n"
        f"Oᴛʜᴇʀꜱ : {other_count}\n\n"
        f"Send Your Index File ID Between 1-{len(links)} .**", )

    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    try:
        input0: Message = await bot.listen(editable.chat.id,
                                           timeout=timeout_duration)
        raw_text = input0.text
        await input0.delete(True)
    except asyncio.TimeoutError:
        raw_text = '1'

    if int(raw_text) > len(links):
        await editable.edit(
            f"**🔹Enter number in range of Index (01-{len(links)})**")
        processing_request = False  # Reset the processing flag
        await m.reply_text("**🔹Exiting Task......  **")
        return

    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit(
        f"**1. Enter Batch Name\n2.Send /d For TXT Batch Name**")
    try:
        input1: Message = await bot.listen(editable.chat.id,
                                           timeout=timeout_duration)
        raw_text0 = input1.text
        await input1.delete(True)
    except asyncio.TimeoutError:
        raw_text0 = '/d'

    if raw_text0 == '/d':
        b_name = file_name.replace('_', ' ')
    else:
        b_name = raw_text0

    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit(
        "**🎞️  Eɴᴛᴇʀ  Rᴇꜱᴏʟᴜᴛɪᴏɴ\n\n╭━━⪼  `360`\n┣━━⪼  `480`\n┣━━⪼  `720`\n╰━━⪼  `1080`**"
    )
    try:
        input2: Message = await bot.listen(editable.chat.id,
                                           timeout=timeout_duration)
        raw_text2 = input2.text
        await input2.delete(True)
    except asyncio.TimeoutError:
        raw_text2 = '480'
    quality = f"{raw_text2}p"
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080"
        else:
            res = "UN"
    except Exception:
        res = "UN"
    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20

    await editable.edit(
        "**1. Send A Text For Watermark\n2. Send /d for no watermark & fast dwnld**"
    )
    try:
        inputx: Message = await bot.listen(editable.chat.id,
                                           timeout=timeout_duration)
        raw_textx = inputx.text
        await inputx.delete(True)
    except asyncio.TimeoutError:
        raw_textx = '/d'

    # Define watermark variable based on input
    global watermark
    if raw_textx == '/d':
        watermark = "/d"
    else:
        watermark = raw_textx

    await editable.edit(
        f"**1. Send Your Name For Caption Credit\n2. Send /d For default Credit **"
    )
    try:
        input3: Message = await bot.listen(editable.chat.id,
                                           timeout=timeout_duration)
        raw_text3 = input3.text
        await input3.delete(True)
    except asyncio.TimeoutError:
        raw_text3 = '/d'

    if raw_text3 == '/d':
        CR = f"{CREDIT}"
    elif "," in raw_text3:
        CR, PRENAME = raw_text3.split(",")
    else:
        CR = raw_text3
    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit(
        f"**1. Send PW Token For MPD urls\n 2. Send /d For Others **")
    try:
        input4: Message = await bot.listen(editable.chat.id,
                                           timeout=timeout_duration)
        raw_text4 = input4.text
        await input4.delete(True)
    except asyncio.TimeoutError:
        raw_text4 = '/d'
    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit(
        "**1. Send A Image For Thumbnail\n2. Send /d For default Thumbnail\n3. Send /skip For Skipping**"
    )
    thumb = "/d"  # Set default value
    try:
        input6 = await bot.listen(chat_id=m.chat.id, timeout=timeout_duration)

        if input6.photo:
            # If user sent a photo
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            temp_file = f"downloads/thumb_{m.from_user.id}.jpg"
            try:
                # Download photo using correct Pyrogram method
                await bot.download_media(message=input6.photo,
                                         file_name=temp_file)
                thumb = temp_file
                await editable.edit(
                    "**✅ Custom thumbnail saved successfully!**")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error downloading thumbnail: {str(e)}")
                await editable.edit(
                    "**⚠️ Failed to save thumbnail! Using default.**")
                thumb = "/d"
                await asyncio.sleep(1)
        elif input6.text:
            if input6.text == "/d":
                thumb = "/d"
                await editable.edit("**📰 Using default thumbnail.**")
                await asyncio.sleep(1)
            elif input6.text == "/skip":
                thumb = "no"
                await editable.edit("**♻️ Skipping thumbnail.**")
                await asyncio.sleep(1)
            else:
                await editable.edit(
                    "**⚠️ Invalid input! Using default thumbnail.**")
                await asyncio.sleep(1)
        await input6.delete(True)
    except asyncio.TimeoutError:
        await editable.edit("**⚠️ Timeout! Using default thumbnail.**")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Error in thumbnail handling: {str(e)}")
        await editable.edit("**⚠️ Error! Using default thumbnail.**")
        await asyncio.sleep(1)

    await editable.edit(
        "__**📢 Provide the Channel ID or send /d__\n\n<blockquote>🔹Send Your Channel ID where you want upload files.\n\nEx : -100XXXXXXXXX</blockquote>\n**"
    )
    try:
        input7: Message = await bot.listen(editable.chat.id,
                                           timeout=timeout_duration)
        raw_text7 = input7.text
        await input7.delete(True)
    except asyncio.TimeoutError:
        raw_text7 = '/d'

    if "/d" in raw_text7:
        channel_id = m.chat.id
    else:
        channel_id = raw_text7
    await editable.delete()

    try:
        if raw_text == "1":
            batch_message = await bot.send_message(
                chat_id=channel_id,
                text=f"<blockquote><b>🎯Target Batch : {b_name}</b></blockquote>"
            )
            if "/d" not in raw_text7:
                await bot.send_message(
                    chat_id=m.chat.id,
                    text=
                    f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩"
                )
                await bot.send_message(
                    chat_id=m.chat.id,
                    text=
                    f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩"
                )
                await bot.pin_chat_message(channel_id, batch_message.id)
                message_id = batch_message.id + 1
                await bot.delete_messages(channel_id, message_id)
                await bot.pin_chat_message(channel_id, message_id)
        else:
            if "/d" not in raw_text7:
                await bot.send_message(
                    chat_id=m.chat.id,
                    text=
                    f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩"
                )
    except Exception as e:
        await m.reply_text(
            f"**Fail Reason »**\n<blockquote><i>{e}</i></blockquote>\n\n✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CREDIT}🌟`"
        )

    failed_count = 0
    count = int(raw_text)
    arg = int(raw_text)
    try:
        for i in range(arg - 1, len(links)):
            Vxy = links[i][1].replace(
                "file/d/", "uc?export=download&id=").replace(
                    "www.youtube-nocookie.com/embed",
                    "youtu.be").replace("?modestbranding=1",
                                        "").replace("/view?usp=sharing", "")
            url = "https://" + Vxy
            link0 = "https://" + Vxy

            name1 = links[i][0].replace("(", "[").replace(")", "]").replace(
                "_", "").replace("\t", "").replace(":", "").replace(
                    "/", "").replace("+", "").replace("#", "").replace(
                        "|", "").replace("@", "").replace("*", "").replace(
                            ".", "").replace("https", "").replace("http",
                                                                  "").strip()
            if "," in raw_text3:
                name = f'{PRENAME} {name1[:60]}'
            else:
                name = f'{name1[:60]}'

            user_id = m.from_user.id

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(
                            url,
                            headers=
                        {
                            'Accept':
                            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Cache-Control': 'no-cache',
                            'Connection': 'keep-alive',
                            'Pragma': 'no-cache',
                            'Referer': 'http://www.visionias.in/',
                            'Sec-Fetch-Dest': 'iframe',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'cross-site',
                            'Upgrade-Insecure-Requests': '1',
                            'User-Agent':
                            'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36',
                            'sec-ch-ua':
                            '"Chromium";v="107", "Not=A?Brand";v="24"',
                            'sec-ch-ua-mobile': '?1',
                            'sec-ch-ua-platform': '"Android"',
                        }) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"",
                                        text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'

            elif "https://static-trans-v1.classx.co.in" in url or "https://static-trans-v2.classx.co.in" in url:
                base_with_params, signature = url.split("*")

                base_clean = base_with_params.split(".mkv")[0] + ".mkv"

                if "static-trans-v1.classx.co.in" in url:
                    base_clean = base_clean.replace(
                        "https://static-trans-v1.classx.co.in",
                        "https://appx-transcoded-videos-mcdn.akamai.net.in")
                elif "static-trans-v2.classx.co.in" in url:
                    base_clean = base_clean.replace(
                        "https://static-trans-v2.classx.co.in",
                        "https://transcoded-videos-v2.classx.co.in")

                url = f"{base_clean}*{signature}"

            elif "https://static-rec.classx.co.in/drm/" in url:
                base_with_params, signature = url.split("*")

                base_clean = base_with_params.split("?")[0]

                base_clean = base_clean.replace(
                    "https://static-rec.classx.co.in",
                    "https://appx-recordings-mcdn.akamai.net.in")

                url = f"{base_clean}*{signature}"

            elif "https://static-wsb.classx.co.in/" in url:
                clean_url = url.split("?")[0]

                clean_url = clean_url.replace(
                    "https://static-wsb.classx.co.in",
                    "https://appx-wsb-gcp-mcdn.akamai.net.in")

                url = clean_url

            elif "https://static-db.classx.co.in/" in url:
                if "*" in url:
                    base_url, key = url.split("*", 1)
                    base_url = base_url.split("?")[0]
                    base_url = base_url.replace(
                        "https://static-db.classx.co.in",
                        "https://appxcontent.kaxa.in")
                    url = f"{base_url}*{key}"
                else:
                    base_url = url.split("?")[0]
                    url = base_url.replace("https://static-db.classx.co.in",
                                           "https://appxcontent.kaxa.in")

            elif "https://static-db-v2.classx.co.in/" in url:
                if "*" in url:
                    base_url, key = url.split("*", 1)
                    base_url = base_url.split("?")[0]
                    base_url = base_url.replace(
                        "https://static-db-v2.classx.co.in",
                        "https://appx-content-v2.classx.co.in")
                    url = f"{base_url}*{key}"
                else:
                    base_url = url.split("?")[0]
                    url = base_url.replace(
                        "https://static-db-v2.classx.co.in",
                        "https://appx-content-v2.classx.co.in")

                user_id = m.from_user.id

            elif any(x in url for x in [
                    "https://cpvod.testbook.com/", "classplusapp.com/drm/",
                    "media-cdn.classplusapp.com",
                    "media-cdn-alisg.classplusapp.com",
                    "media-cdn-a.classplusapp.com", "tencdn.classplusapp",
                    "videos.classplusapp", "webvideos.classplusapp.com"
            ]):
                # normalize cpvod -> media-cdn path used by API
                url_norm = url.replace(
                    "https://cpvod.testbook.com/",
                    "https://media-cdn.classplusapp.com/drm/")
                api_url_call = f"https://itsgolu-cp-api.vercel.app/itsgolu?url={url_norm}@ITSGOLU_OFFICIAL&user_id={user_id}"
                keys_string = ""
                mpd = None
                try:
                    resp = requests.get(api_url_call, timeout=30)
                    # parse JSON safely
                    try:
                        data = resp.json()
                    except Exception:
                        data = None

                    # DRM response (MPD + KEYS)
                    if isinstance(data,
                                  dict) and "KEYS" in data and "MPD" in data:
                        mpd = data.get("MPD")
                        keys = data.get("KEYS", [])
                        url = mpd
                        keys_string = " ".join([f"--key {k}" for k in keys])

                    # Non-DRM response (direct url)
                    elif isinstance(data, dict) and "url" in data:
                        url = data.get("url")
                        keys_string = ""

                    else:
                        # Unexpected response format — fallback to helper
                        try:
                            res = helper.get_mps_and_keys2(url_norm)
                            if res:
                                mpd, keys = res
                                url = mpd
                                keys_string = " ".join(
                                    [f"--key {k}" for k in keys])
                            else:
                                keys_string = ""
                        except Exception:
                            keys_string = ""
                except Exception:
                    # API failed — attempt helper fallback
                    try:
                        res = helper.get_mps_and_keys2(url_norm)
                        if res:
                            mpd, keys = res
                            url = mpd
                            keys_string = " ".join(
                                [f"--key {k}" for k in keys])
                        else:
                            keys_string = ""
                    except Exception:
                        keys_string = ""
            elif "tencdn.classplusapp" in url:
                headers = {
                    'host': 'api.classplusapp.com',
                    'x-access-token': f'{raw_text4}',
                    'accept-language': 'EN',
                    'api-version': '18',
                    'app-version': '1.4.73.2',
                    'build-number': '35',
                    'connection': 'Keep-Alive',
                    'content-type': 'application/json',
                    'device-details': 'Xiaomi_Redmi 7_SDK-32',
                    'device-id': 'c28d3cb16bbdac01',
                    'region': 'IN',
                    'user-agent': 'Mobile-Android',
                    'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c',
                    'accept-encoding': 'gzip'
                }
                params = {"url": f"{url}"}
                response = requests.get(
                    'https://api.classplusapp.com/cams/uploader/video/jw-signed-url',
                    headers=headers,
                    params=params)
                url = response.json()['url']

            elif 'videos.classplusapp' in url:
                url = requests.get(
                    f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}',
                    headers={
                        'x-access-token': f'{cptoken}'
                    }).json()['url']

            elif 'media-cdn.classplusapp.com' in url or 'media-cdn-alisg.classplusapp.com' in url or 'media-cdn-a.classplusapp.com' in url:
                headers = {
                    'host': 'api.classplusapp.com',
                    'x-access-token': f'{cptoken}',
                    'accept-language': 'EN',
                    'api-version': '18',
                    'app-version': '1.4.73.2',
                    'build-number': '35',
                    'connection': 'Keep-Alive',
                    'content-type': 'application/json',
                    'device-details': 'Xiaomi_Redmi 7_SDK-32',
                    'device-id': 'c28d3cb16bbdac01',
                    'region': 'IN',
                    'user-agent': 'Mobile-Android',
                    'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c',
                    'accept-encoding': 'gzip'
                }
                params = {"url": f"{url}"}
                response = requests.get(
                    'https://api.classplusapp.com/cams/uploader/video/jw-signed-url',
                    headers=headers,
                    params=params)
                url = response.json()['url']

            elif "childId" in url and "parentId" in url:
                url = f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={raw_text4}"

            if "edge.api.brightcove.com" in url:
                bcov = f'bcov_auth={cwtoken}'
                url = url.split("bcov_auth")[0] + bcov

            elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
                url = f"https://anonymouspwplayer-b99f57957198.herokuapp.com/pw?url={url}?token={raw_text4}"

            if ".pdf*" in url:
                url = f"https://dragoapi.vercel.app/pdf/{url}"

            elif 'encrypted.m' in url:
                appxkey = url.split('*')[1]
                url = url.split('*')[0]

            if "youtu" in url:
                ytf = f"bv*[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[height<=?{raw_text2}]"
            elif "embed" in url:
                ytf = f"bestvideo[height<={raw_text2}]+bestaudio/best[height<={raw_text2}]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

            if "jw-prod" in url:
                url = url.replace(
                    "https://apps-s3-jw-prod.utkarshapp.com/admin_v1/file_library/videos",
                    "https://d1q5ugnejk3zoi.cloudfront.net/ut-production-jw/admin_v1/file_library/videos"
                )
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            elif "webvideos.classplusapp." in url:
                cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            try:
                cc = (f"<b>🏷️ Iɴᴅᴇx ID  :</b> {str(count).zfill(3)}\n\n"
                      f"<b>🎞️  Tɪᴛʟᴇ :</b> {name1} \n\n"
                      f"<blockquote>📚  𝗕ᴀᴛᴄʜ : {b_name}</blockquote>"
                      f"\n\n<b>🎓  Extracted by ➤ {CR}</b>")
                cc1 = (f"<b>🏷️ Iɴᴅᴇx ID :</b> {str(count).zfill(3)}\n\n"
                       f"<b>📑  Tɪᴛʟᴇ :</b> {name1} \n\n"
                       f"<blockquote>📚  𝗕ᴀᴛᴄʜ : {b_name}</blockquote>"
                       f"\n\n<b>🎓  Extracted by ➤ {CR}</b>")
                cczip = f'[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{name1} .zip`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                ccimg = (f"<b>🏷️ Iɴᴅᴇx ID <b>: {str(count).zfill(3)} \n\n"
                         f"<b>🖼️  Tɪᴛʟᴇ</b> : {name1} \n\n"
                         f"<blockquote>📚  𝗕ᴀᴛᴄʜ : {b_name}</blockquote>"
                         f"\n\n<b>🎓  Uᴘʟᴏᴀᴅ Bʏ : {CR}</b>")
                ccm = f'[🎵]Audio Id : {str(count).zfill(3)}\n**Audio Title :** `{name1} .mp3`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                cchtml = f'[🌐]Html Id : {str(count).zfill(3)}\n**Html Title :** `{name1} .html`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'

                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=channel_id,
                                                       document=ka,
                                                       caption=cc1)
                        count += 1
                        os.remove(ka)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".pdf" in url:

                    try:
                
                        url = url.replace(" ", "%20")
                        filename = f"{name}.pdf"
                
                        referers = [
                            "https://nirmitacademy.akamai.net.in/",
                            "https://test.classx.co.in/",
                            "https://acadmy.akamai.net.in/",
                            "https://test.akamai.net.in/"
                        ]
                
                        scraper = cloudscraper.create_scraper()
                        success = False
                
                        for ref in referers:
                
                            headers = {
                                "User-Agent": "Mozilla/5.0",
                                "Referer": ref
                                
                            }
                
                            response = scraper.get(url, headers=headers, stream=True)
                
                            if response.status_code == 200:
                
                                with open(filename, "wb") as f:
                                    for chunk in response.iter_content(1024 * 1024):
                                        if chunk:
                                            f.write(chunk)
                
                                await bot.send_document(
                                    chat_id=channel_id,
                                    document=filename,
                                    caption=cc1
                                )
                
                                count += 1
                
                                if os.path.exists(filename):
                                    os.remove(filename)
                
                                success = True
                                break
                
                        if not success:
                            raise Exception("All referers failed")
                
                    except Exception as e:
                
                        await bot.send_message(
                            channel_id,
                            f"⚠️ PDF Download Failed\n\n{name1}\n\nReason: {str(e)}"
                        )
                
                        failed_count += 1
                        count += 1
                        continue
                    

                elif ".ws" in url and url.endswith(".ws"):
                    try:
                        await helper.pdf_download(
                            f"{api_url}utkash-ws?url={url}&authorization={api_token}",
                            f"{name}.html")
                        time.sleep(1)
                        await bot.send_document(chat_id=channel_id,
                                                document=f"{name}.html",
                                                caption=cchtml)
                        os.remove(f'{name}.html')
                        count += 1
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif any(ext in url for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_photo(chat_id=channel_id,
                                                    photo=f'{name}.{ext}',
                                                    caption=ccimg)
                        count += 1
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif any(ext in url for ext in [".mp3", ".wav", ".m4a"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -x --audio-format {ext} -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        await bot.send_document(chat_id=channel_id,
                                                document=f'{name}.{ext}',
                                                caption=cc1)
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif 'encrypted.m' in url:
                    Show = f"<i><b>Video APPX Encrypted Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(
                        channel_id, Show, disable_web_page_preview=True)
                    try:

                        res_file = await helper.download_and_decrypt_video(
                            url, cmd, name, appxkey)
                        filename = res_file
                        await prog.delete(True)
                        if os.path.exists(filename):
                            await helper.send_vid(bot,
                                                  m,
                                                  cc,
                                                  filename,
                                                  thumb,
                                                  name,
                                                  prog,
                                                  channel_id,
                                                  watermark=watermark)
                            count += 1
                        else:
                            await bot.send_message(
                                channel_id,
                                f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {link0}\n\n<blockquote><i><b>Failed Reason: {str(e)}</b></i></blockquote>',
                                disable_web_page_preview=True)
                            failed_count += 1
                            count += 1
                            continue

                    except Exception as e:
                        await bot.send_message(
                            channel_id,
                            f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {link0}\n\n<blockquote><i><b>Failed Reason: {str(e)}</b></i></blockquote>',
                            disable_web_page_preview=True)
                        count += 1
                        failed_count += 1
                        continue

                elif 'drmcdni' in url or 'drm/wv' in url or 'drm/common' in url:
                    Show = f"<i><b>📥 Fast Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(
                        channel_id, Show, disable_web_page_preview=True)
                    res_file = await helper.decrypt_and_merge_video(
                        mpd, keys_string, path, name, raw_text2)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot,
                                          m,
                                          cc,
                                          filename,
                                          thumb,
                                          name,
                                          prog,
                                          channel_id,
                                          watermark=watermark)
                    count += 1
                    await asyncio.sleep(1)
                    continue

                else:
                    Show = f"<i><b>📥 Fast Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(
                        channel_id, Show, disable_web_page_preview=True)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot,
                                          m,
                                          cc,
                                          filename,
                                          thumb,
                                          name,
                                          prog,
                                          channel_id,
                                          watermark=watermark)
                    count += 1
                    time.sleep(1)

            except Exception as e:
                await bot.send_message(
                    channel_id,
                    f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {link0}\n\n<blockquote><i><b>Failed Reason: {str(e)}</b></i></blockquote>',
                    disable_web_page_preview=True)
                count += 1
                failed_count += 1
                continue

    except Exception as e:
        await m.reply_text(e)
        time.sleep(2)

    success_count = len(links) - failed_count
    video_count = v2_count + mpd_count + m3u8_count + yt_count + drm_count + zip_count + other_count
    if raw_text7 == "/d":
        await bot.send_message(
            channel_id, ("<b>📬 ᴘʀᴏᴄᴇꜱꜱ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>\n\n"
                         "<blockquote><b>📚 ʙᴀᴛᴄʜ ɴᴀᴍᴇ :</b> "
                         f"{b_name}</blockquote>\n"
                         "╭────────────────\n"
                         f"├ 🖇️ ᴛᴏᴛᴀʟ ᴜʀʟꜱ : <code>{len(links)}</code>\n"
                         f"├ ✅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ : <code>{success_count}</code>\n"
                         f"├ ❌ ꜰᴀɪʟᴇᴅ : <code>{failed_count}</code>\n"
                         "╰────────────────\n\n"
                         "╭──────── 📦 ᴄᴀᴛᴇɢᴏʀʏ ────────\n"
                         f"├ 🎞️ ᴠɪᴅᴇᴏꜱ : <code>{video_count}</code>\n"
                         f"├ 📑 ᴘᴅꜰꜱ : <code>{pdf_count}</code>\n"
                         f"├ 🖼️ ɪᴍᴀɢᴇꜱ : <code>{img_count}</code>\n"
                         "╰────────────────────────────\n\n"
                         "<i>ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ Rixie 🤖</i>"))

    else:
        await bot.send_message(
            channel_id,
            f"<b>-┈━═.•°✅ Completed ✅°•.═━┈-</b>\n<blockquote><b>🎯Batch Name : {b_name}</b></blockquote>\n<blockquote>🔗 Total URLs: {len(links)} \n┃   ┠🔴 Total Failed URLs: {failed_count}\n┃   ┠🟢 Total Successful URLs: {success_count}\n┃   ┃   ┠🎥 Total Video URLs: {video_count}\n┃   ┃   ┠📄 Total PDF URLs: {pdf_count}\n┃   ┃   ┠📸 Total IMAGE URLs: {img_count}</blockquote>\n"
        )
        await bot.send_message(
            m.chat.id,
            f"<blockquote><b>✅ Your Task is completed, please check your Set Channel📱</b></blockquote>"
        )


@bot.on_message(
    filters.text
    & filters.private
    & auth_filter
    & ~filters.command(
        ["start", "drm", "addlive", "process", "stoplive", "killalllive",
         "plan", "id", "t2t", "t2h", "logs", "144", "240", "360", "480", "720", "1080"]
    )
)
async def text_handler(bot: Client, m: Message):
    if m.from_user.is_bot:
        return
    links = m.text
    path = None
    match = re.search(r'https?://\S+', links)
    if match:
        link = match.group(0)
    else:
        await m.reply_text("<pre><code>Invalid link format.</code></pre>")
        return

    editable = await m.reply_text(
        f"<pre><code>**🔹Processing your link...\n🔁Please wait...⏳**</code></pre>"
    )
    await m.delete()

    await editable.edit(
        f"╭━━━━❰ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ❱━━➣ \n┣━━⪼ send `144`\n┣━━⪼ send `240`\n┣━━⪼ send `360`\n┣━━⪼ send `480`\n┣━━⪼ send `720`\n┣━━⪼ send `1080`\n╰━━⌈⚡[`{CREDIT}`]⚡⌋━━➣ "
    )
    input2: Message = await bot.listen(editable.chat.id,
                                       filters=filters.text
                                       & filters.user(m.from_user.id))
    raw_text2 = input2.text
    quality = f"{raw_text2}p"
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080"
        else:
            res = "UN"
    except Exception:
        res = "UN"
    # ... rest of the function logic would continue here ...


# New Callback Handlers for the buttons
@bot.on_callback_query(filters.regex("features"))
async def features_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    features_text = ("**🔥 Bot Features 🔥**\n\n"
                     "• 📥 Download DRM protected videos\n"
                     "• 🎬 Support for multiple video formats\n"
                     "• 📱 Works with YouTube and other platforms\n"
                     "• 📑 PDF download support\n"
                     "• 🖼️ Image download support\n"
                     "• 🎵 Audio download support\n"
                     "• 📝 Text to file conversion\n"
                     "• ⚙️ Customizable quality settings\n"
                     "• 🎨 Custom watermark support\n")
    await callback_query.message.edit_text(
        features_text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]))


@bot.on_callback_query(filters.regex("details"))
async def details_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    details_text = ("**📋 Bot Details 📋**\n\n"
                    "• 🤖 Bot Name: DRM Wizard 🦋\n"
                    "• 👨‍💻 Developer: Ghost Rix\n"
                    "• 📱 Contact: @RixieHQ\n"
                    "• 🔄 Version: 1.0\n"
                    "• 📝 Language: Python\n"
                    "• 🛠️ Framework: Pyrogram\n\n"
                    "**🔐 Privacy & Security**\n\n"
                    "• 🔒 Your data is secure with us\n"
                    "• 🚫 We don't store your personal information\n"
                    "• 🔐 End-to-end encryption for all communications\n")
    await callback_query.message.edit_text(
        details_text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]))


@bot.on_callback_query(filters.regex("back_to_start"))
async def back_to_start_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    # Get the user info again to personalize the message
    user_id = callback_query.from_user.id
    is_authorized = db.is_user_authorized(user_id, client.me.username)
    is_admin = db.is_admin(user_id)

    commands_list = ("**>  /drm - ꜱᴛᴀʀᴛ ᴜᴘʟᴏᴀᴅɪɴɢ ᴄᴘ/ᴄᴡ ᴄᴏᴜʀꜱᴇꜱ**\n"
                     "**>  /plan - ᴠɪᴇᴡ ʏᴏᴜʀ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴅᴇᴛᴀɪʟꜱ**\n")

    if is_admin:
        commands_list += ("\n**👑 Admin Commands**\n"
                          "• /users - List all users\n")

    await callback_query.message.edit_media(
        media=InputMediaPhoto(
            media=photologo,
            caption=
            f"**Mʏ ᴄᴏᴍᴍᴀɴᴅꜱ ғᴏʀ ʏᴏᴜ [{callback_query.from_user.first_name} ](tg://settings)**\n\n{commands_list}"
        ),
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("👑 OWNER 👑",
                                     url="https://t.me/RixieHQ")
            ],
             [
                 InlineKeyboardButton("ғᴇᴀᴛᴜʀᴇꜱ 🪔", callback_data="features"),
                 InlineKeyboardButton("ᴅᴇᴛᴀɪʟꜱ 🦋", callback_data="details")
             ]]))



# ================= LIVE AUTO RECORDER (MULTI VERSION) =================


ACTIVE_LIVES: Dict[int, Dict[str, Any]] = {}
PROCESS_COUNTER = 0
MAX_LIVE_MISSING_COUNT = 3  # Configurable
CHECK_INTERVAL = 20  # seconds
FFMPEG_TIMEOUT = 30  # seconds for graceful shutdown


@dataclass
class LiveConfig:
    """Configuration for live recording"""
    pid: int
    api_base: str
    course_id: str
    token: str
    upload_chat: int
    thread_id: Optional[int]
    client: Any
    owner_chat: int
    quality: str = "480p"  # Fixed quality, no selection
    max_duration: Optional[int] = None  # Max recording duration in seconds
    batch_name: str = ""  # New: Store batch name from course_slug


class LiveRecorder:
    """Robust live recorder with proper resource management"""
    
    def __init__(self, config: LiveConfig):
        self.config = config
        self.current_live: Optional[str] = None
        self.live_file: Optional[str] = None
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.live_missing_count = 0
        self.last_title: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._temp_dir = tempfile.mkdtemp(prefix=f"live_{config.pid}_")
        
    async def cleanup(self):
        """Proper cleanup of all resources"""
        async with self._lock:
            # Stop ffmpeg process
            if self.proc and self.proc.returncode is None:
                try:
                    # Graceful shutdown first
                    self.proc.send_signal(signal.SIGTERM)
                    await asyncio.wait_for(self.proc.wait(), timeout=FFMPEG_TIMEOUT)
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown fails
                    self.proc.kill()
                    await self.proc.wait()
                except Exception as e:
                    print(f"[PID {self.config.pid}] Error stopping ffmpeg: {e}")
                finally:
                    self.proc = None
            
            # Cleanup temp files
            if self.live_file and os.path.exists(self.live_file):
                try:
                    os.remove(self.live_file)
                except Exception as e:
                    print(f"[PID {self.config.pid}] Error removing live file: {e}")
            
            # Cleanup temp directory
            try:
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"[PID {self.config.pid}] Error removing temp dir: {e}")
    
    async def fetch_batch_name(self) -> str:
        """Fetch batch name from course_slug using /get/courselistnewv2 endpoint"""
        headers = {
            "Authorization": self.config.token,
            "Client-Service": "Appx",
            "Auth-Key": "appxapi",
            "User-ID": "-2",
            "User-Agent": "okhttp/4.9.1"
        }

        try:
            async with aiohttp.ClientSession() as session:
                # Get exam_id first from course details if needed, or try without it
                url = f"{self.config.api_base}/get/courselistnewv2?exam_id=&start=-1"
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return "Unknown Batch"
                    
                    try:
                        data = await resp.json()
                    except Exception:
                        return "Unknown Batch"
                    
                    if not isinstance(data, dict):
                        return "Unknown Batch"
                    
                    # Search for course_id in the list
                    courses = data.get("data", {}).get("course_list", [])
                    for course in courses:
                        if str(course.get("id")) == str(self.config.course_id):
                            course_slug = course.get("course_slug", "")
                            # Convert slug to readable name
                            # e.g., "psi-2026-detailed-live-solution-3-papers" -> "PSI 2026 Detailed Live Solution 3 Papers"
                            if course_slug:
                                batch_name = course_slug.replace("-", " ").title()
                                return batch_name
                    
                    return "Unknown Batch"
                    
        except Exception as e:
            print(f"[PID {self.config.pid}] Error fetching batch name: {e}")
            return "Unknown Batch"
    
    async def fetch_live_data(self) -> tuple:
        """Fetch live data with proper error handling"""
        headers = {
            "Authorization": self.config.token,
            "Client-Service": "Appx",
            "Auth-Key": "appxapi",
            "User-ID": "-2",
            "User-Agent": "okhttp/4.9.1"
        }

        endpoints = [
            f"/get/live_upcoming_course_classv2?start=-1&courseid={self.config.course_id}",
            f"/get/course_contents_by_live_status?course_id={self.config.course_id}&start=-1&live_status=1,2"
        ]

        async with aiohttp.ClientSession() as session:
            for ep in endpoints:
                try:
                    url = f"{self.config.api_base}{ep}"
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        
                        if resp.status in [401, 403]:
                            return "AUTH_ERROR", None, None
                        
                        if resp.status != 200:
                            continue
                        
                        try:
                            data = await resp.json()
                        except Exception:
                            continue
                        
                        if not isinstance(data, dict):
                            continue
                            
                        live_data = data.get("data", {}).get("live", [])
                        if not live_data:
                            continue
                        
                        item = live_data[0]
                        title = item.get("Title", "LIVE")
                        sid = item.get("recording_schedule")
                        
                        if not sid:
                            return None, None, None
                        
                        # Construct stream URL with fixed quality (480p)
                        stream_url = f"https://liveclasses.cloud-front.in/live/{sid}_480p.m3u8"
                        
                        return title, sid, stream_url
                        
                except asyncio.TimeoutError:
                    print(f"[PID {self.config.pid}] Timeout fetching live data from {ep}")
                    continue
                except Exception as e:
                    print(f"[PID {self.config.pid}] Error fetching from {ep}: {e}")
                    continue
        
        return None, None, None
    
    def build_ffmpeg_cmd(self, stream_url: str, output_file: str) -> list:
        """Build optimized ffmpeg command"""
        return [
            "ffmpeg",
            "-y",
            "-hide_banner",  # Less verbose
            "-loglevel", "error",  # Only show errors
            "-fflags", "+genpts+discardcorrupt",  # Handle corrupt streams
            "-thread_queue_size", "4096",  # Prevent buffer overruns
            "-i", stream_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-movflags", "+faststart",
            "-map", "0",
            "-f", "mp4",
            output_file
        ]
    
    async def start_recording(self, title: str, sid: str, stream_url: str):
        """Start new recording with proper setup"""
        async with self._lock:
            self.current_live = sid
            self.last_title = title
            self.start_time = datetime.now()
            self.live_missing_count = 0
            
            # Sanitize filename - use Title (batch name nahi, wo caption mein ayega)
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title or "LIVE")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.live_file = os.path.join(
                self._temp_dir, 
                f"{safe_title}_{self.config.pid}_{timestamp}.mp4"
            )
            
            # Notify start
            try:
                await self.config.client.send_message(
                    self.config.upload_chat,
                    f"🔴 <b>LIVE STARTED</b>\\n"
                    f"🆔 Process: <code>{self.config.pid:03d}</code>\\n"
                    f"🎬 <b>{title}</b>\\n"
                    f"📊 Quality: <code>480p</code>\\n"
                    f"📚 Batch: <b>{self.config.batch_name}</b>\\n"
                    f"⬇️ <i>Recording started...</i>\\n"
                    f"⏰ <code>{datetime.now().strftime(\'%H:%M:%S\')}</code>",
                    message_thread_id=self.config.thread_id
                )
            except Exception as e:
                print(f"[PID {self.config.pid}] Failed to send start notification: {e}")
            
            # Start ffmpeg
            cmd = self.build_ffmpeg_cmd(stream_url, self.live_file)
            try:
                self.proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Start stderr reader to prevent buffer blocking
                asyncio.create_task(self._read_stderr())
                
            except Exception as e:
                print(f"[PID {self.config.pid}] Failed to start ffmpeg: {e}")
                await self._notify_error(f"Failed to start recording: {e}")
                raise
    
    async def _read_stderr(self):
        """Read ffmpeg stderr to prevent blocking"""
        if not self.proc:
            return
            
        try:
            while True:
                line = await self.proc.stderr.readline()
                if not line:
                    break
                # Log only errors, not info
                decoded = line.decode().strip()
                if "error" in decoded.lower():
                    print(f"[PID {self.config.pid}] FFmpeg: {decoded}")
        except Exception:
            pass
    
    async def stop_recording(self) -> bool:
        """Stop recording and upload with proper finalization"""
        async with self._lock:
            if not self.current_live:
                return False
            
            # Stop ffmpeg
            if self.proc and self.proc.returncode is None:
                try:
                    # Send Q to gracefully stop ffmpeg (standard way)
                    self.proc.stdin.close() if self.proc.stdin else None
                    
                    # Wait with timeout
                    await asyncio.wait_for(self.proc.wait(), timeout=FFMPEG_TIMEOUT)
                except asyncio.TimeoutError:
                    self.proc.kill()
                    await self.proc.wait()
                except Exception as e:
                    print(f"[PID {self.config.pid}] Error stopping ffmpeg: {e}")
                finally:
                    self.proc = None
            
            # Check if file exists and has content
            if not self.live_file or not os.path.exists(self.live_file):
                await self._notify_error("Recording file not found")
                self._reset_state()
                return False
            
            file_size = os.path.getsize(self.live_file)
            if file_size < 1024 * 1024:  # Less than 1MB
                await self._notify_error(f"File too small ({file_size} bytes), likely failed")
                os.remove(self.live_file)
                self._reset_state()
                return False
            
            # Process and upload
            success = await self._finalize_and_upload()
            self._reset_state()
            return success
    
    async def _finalize_and_upload(self) -> bool:
        """Finalize video and upload to Telegram"""
        original_file = self.live_file
        fixed_file = os.path.join(self._temp_dir, f"fixed_{os.path.basename(original_file)}")
        thumb_file = os.path.join(self._temp_dir, "thumb.jpg")
        
        try:
            # Fix video metadata
            fix_cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", original_file,
                "-c", "copy", "-map", "0",
                "-movflags", "+faststart",
                fixed_file
            ]
            
            proc = await asyncio.create_subprocess_exec(*fix_cmd)
            await asyncio.wait_for(proc.wait(), timeout=60)
            
            if not os.path.exists(fixed_file) or os.path.getsize(fixed_file) == 0:
                raise Exception("Video fixing failed")
            
            # Get duration
            duration_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                fixed_file
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *duration_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await proc.communicate()
            duration = int(float(stdout.decode().strip())) if stdout else 0
            
            # Generate thumbnail (at 10% or 5 seconds, whichever is smaller)
            thumb_time = min(duration * 0.1, 5) if duration else 5
            thumb_cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", fixed_file,
                "-ss", str(thumb_time), "-vframes", "1",
                "-vf", "scale=320:-1",  # Smaller thumbnail
                thumb_file
            ]
            
            proc = await asyncio.create_subprocess_exec(*thumb_cmd)
            await proc.wait()
            
            # Build caption - Title in filename, Batch name in caption
            end_time = datetime.now()
            duration_str = f"{duration // 3600:02d}:{(duration % 3600) // 60:02d}:{duration % 60:02d}" if duration else "Unknown"
            
            # File name mein Title rahega (original title from API)
            caption = (
                f"🎥 <b>Live Recording</b>\\n"
                f"🆔 ID: <code>{self.config.pid:03d}</code>\\n"
                f"📛 <b>{self.last_title or \'Unknown\'}</b> [480p].mp4\\n"
                f"📚 Batch: <b>{self.config.batch_name}</b>\\n"
                f"⏱ Duration: <code>{duration_str}</code>\\n"
                f"📦 Size: <code>{os.path.getsize(fixed_file) / (1024*1024):.1f} MB</code>\\n"
                f"<blockquote>📚 {self.config.batch_name}</blockquote>\\n\\n"
                f"<b>🎓 Extracted by ➤ 𝙂𝙃𝙊𝙎𝙏•𝙍𝙄𝙓</b>\\n"
                f"⏰ <code>{end_time.strftime(\'%H:%M:%S\')}</code>"
            )
            
            # Upload with progress
            await self.config.client.send_video(
                self.config.upload_chat,
                fixed_file,
                caption=caption,
                supports_streaming=True,
                thumb=thumb_file if os.path.exists(thumb_file) else None,
                duration=duration if duration > 0 else None,
                message_thread_id=self.config.thread_id,
                progress=self._upload_progress
            )
            
            # Cleanup files
            for f in [original_file, fixed_file, thumb_file]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
            
            return True
            
        except Exception as e:
            print(f"[PID {self.config.pid}] Finalize error: {e}")
            await self._notify_error(f"Upload failed: {str(e)[:100]}")
            
            # Cleanup on failure
            for f in [original_file, fixed_file, thumb_file]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
            return False
    
    async def _upload_progress(self, current, total):
        """Optional: Log upload progress"""
        if total:
            percent = (current / total) * 100
            if int(percent) % 25 == 0:  # Log at 0, 25, 50, 75, 100
                print(f"[PID {self.config.pid}] Upload: {percent:.1f}%")
    
    async def _notify_error(self, error_msg: str):
        """Send error notification to owner"""
        try:
            await self.config.client.send_message(
                self.config.owner_chat,
                f"⚠️ <b>Process {self.config.pid:03d} Error</b>\\n"
                f"<blockquote>{error_msg}</blockquote>\\n"
                f"🎬 Title: {self.last_title or \'N/A\'}\\n"
                f"📚 Batch: {self.config.batch_name}\\n"
                f"⏰ <code>{datetime.now().strftime(\'%H:%M:%S\')}</code>"
            )
        except Exception as e:
            print(f"[PID {self.config.pid}] Failed to send error notification: {e}")
    
    def _reset_state(self):
        """Reset internal state"""
        self.current_live = None
        self.live_file = None
        self.start_time = None
        self.live_missing_count = 0
    
    async def run(self):
        """Main recording loop"""
        try:
            # Fetch batch name first
            self.config.batch_name = await self.fetch_batch_name()
            
            await self.config.client.send_message(
                self.config.owner_chat,
                f"✅ <b>Live Monitor Started</b>\\n"
                f"🆔 Process: <code>{self.config.pid:03d}</code>\\n"
                f"📚 Course: <code>{self.config.course_id}</code>\\n"
                f"📦 Batch: <b>{self.config.batch_name}</b>\\n"
                f"📤 Upload to: <code>{self.config.upload_chat}</code>\\n"
                f"⏱ Check interval: <code>{CHECK_INTERVAL}s</code>"
            )
            
            while not self._shutdown_event.is_set():
                try:
                    title, sid, stream_url = await self.fetch_live_data()
                    
                    # Handle auth error
                    if title == "AUTH_ERROR":
                        await self.config.client.send_message(
                            self.config.owner_chat,
                            f"❌ <b>Process {self.config.pid:03d}:</b> Token expired or invalid"
                        )
                        break
                    
                    # Live started
                    if sid and sid != self.current_live:
                        if self.current_live:
                            # Previous live ended, finalize it
                            await self.stop_recording()
                        
                        await self.start_recording(title, sid, stream_url)
                    
                    # Live ended
                    elif not sid and self.current_live:
                        self.live_missing_count += 1
                        
                        if self.live_missing_count >= MAX_LIVE_MISSING_COUNT:
                            await self.stop_recording()
                    
                    # Reset counter if live came back
                    elif sid and self.current_live and sid == self.current_live:
                        self.live_missing_count = 0
                    
                    # Check max duration
                    if (self.config.max_duration and self.start_time and 
                        (datetime.now() - self.start_time).total_seconds() > self.config.max_duration):
                        await self.config.client.send_message(
                            self.config.owner_chat,
                            f"⏹ <b>Process {self.config.pid:03d}:</b> Max duration reached, stopping..."
                        )
                        await self.stop_recording()
                    
                    # Wait for next check
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), 
                            timeout=CHECK_INTERVAL
                        )
                    except asyncio.TimeoutError:
                        pass  # Normal operation, continue loop
                        
                except Exception as e:
                    print(f"[PID {self.config.pid}] Loop error: {e}")
                    await asyncio.sleep(5)  # Brief pause on error
            
        except asyncio.CancelledError:
            print(f"[PID {self.config.pid}] Task cancelled")
        finally:
            # Final cleanup
            if self.current_live:
                await self.stop_recording()
            await self.cleanup()
    
    def stop(self):
        """Signal shutdown"""
        self._shutdown_event.set()


# ================= COMMAND HANDLERS =================

def setup_live(bot):
    
    @bot.on_message(filters.command("addlive") & auth_filter)
    async def add_live_multi(client, message):
        """Add new live monitoring process"""
        global PROCESS_COUNTER
        
        try:
            # Get API details
            await message.reply_text("🌐 Send API HOST (e.g., https://api.example.com)")
            response = await client.listen(message.chat.id)
            api_base = response.text.strip()
            await response.delete()
            
            await message.reply_text("📚 Send COURSE ID")
            response = await client.listen(message.chat.id)
            course_id = response.text.strip()
            await response.delete()
            
            await message.reply_text("🔐 Send AUTH TOKEN")
            response = await client.listen(message.chat.id)
            token = response.text.strip()
            await response.delete()
            
            await message.reply_text(
                "📤 Send CHAT ID for upload\\n"
                "• Send <code>/d</code> for current chat\\n"
                "• Format: <code>-100123456789</code>\\n"
                "• With topic: <code>-100123456789/123</code>"
            )
            response = await client.listen(message.chat.id)
            chat_input = response.text.strip()
            await response.delete()
            
            # Parse chat input
            if chat_input == "/d":
                upload_chat = message.chat.id
                thread_id = None
            else:
                if "/" in chat_input:
                    base, topic = chat_input.split("/", 1)
                    upload_chat = int(base.strip())
                    thread_id = int(topic.strip())
                else:
                    upload_chat = int(chat_input)
                    thread_id = None
            
            # Quality fixed at 480p - no selection needed
            quality = "480p"
            
            # Create process
            PROCESS_COUNTER += 1
            pid = PROCESS_COUNTER
            
            config = LiveConfig(
                pid=pid,
                api_base=api_base,
                course_id=course_id,
                token=token,
                upload_chat=upload_chat,
                thread_id=thread_id,
                client=client,
                owner_chat=message.chat.id,
                quality=quality
            )
            
            recorder = LiveRecorder(config)
            
            # Store and start
            task = asyncio.create_task(recorder.run())
            ACTIVE_LIVES[pid] = {
                "recorder": recorder,
                "task": task,
                "config": config,
                "started_at": datetime.now()
            }
            
            await message.reply_text(
                f"✅ <b>Live Monitor Started</b>\\n\\n"
                f"🆔 Process ID: <code>{pid:03d}</code>\\n"
                f"🌐 API: <code>{api_base[:30]}...</code>\\n"
                f"📚 Course: <code>{course_id}</code>\\n"
                f"📤 Upload: <code>{upload_chat}</code>\\n"
                f"🎥 Quality: <code>480p (Fixed)</code>\\n\\n"
                f"Use <code>/stoplive {pid}</code> to stop"
            )
            
        except Exception as e:
            await message.reply_text(f"❌ <b>Error:</b> <code>{str(e)[:200]}</code>")
    
    @bot.on_message(filters.command("process") & auth_filter)
    async def list_processes(client, message):
        """List all active live processes"""
        if not ACTIVE_LIVES:
            return await message.reply_text("❌ No active live processes")
        
        text = "📊 <b>Active Live Processes</b>\\n\\n"
        
        for pid, data in sorted(ACTIVE_LIVES.items()):
            config = data["config"]
            started = data["started_at"].strftime("%H:%M:%S")
            recorder = data["recorder"]
            
            status = "🔴 Recording" if recorder.current_live else "⏳ Waiting"
            current = recorder.last_title or "N/A"
            batch = config.batch_name or "Fetching..."
            
            text += (
                f"🆔 <code>{pid:03d}</code> | {status}\\n"
                f"├ 🎬 {current[:30]}...\\n"
                f"├ 📦 {batch[:30]}...\\n"
                f"├ 📚 {config.course_id}\\n"
                f"├ 📤 {config.upload_chat}\\n"
                f"├ 🎥 480p\\n"
                f"└ ⏰ Started: {started}\\n\\n"
            )
        
        text += f"Total: <code>{len(ACTIVE_LIVES)}</code> processes"
        await message.reply_text(text)
    
    @bot.on_message(filters.command("stoplive") & auth_filter)
    async def stop_live(client, message):
        """Stop specific live process"""
        try:
            parts = message.text.split()
            if len(parts) != 2:
                return await message.reply_text("❌ Usage: <code>/stoplive PROCESS_ID</code>")
            
            pid = int(parts[1])
            
            if pid not in ACTIVE_LIVES:
                return await message.reply_text(f"❌ Process <code>{pid:03d}</code> not found")
            
            data = ACTIVE_LIVES[pid]
            
            # Signal shutdown
            data["recorder"].stop()
            
            # Cancel task
            data["task"].cancel()
            
            try:
                await asyncio.wait_for(data["task"], timeout=10)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            
            # Cleanup
            ACTIVE_LIVES.pop(pid, None)
            
            await message.reply_text(f"🛑 Process <code>{pid:03d}</code> stopped successfully")
            
        except ValueError:
            await message.reply_text("❌ Invalid process ID")
        except Exception as e:
            await message.reply_text(f"❌ Error: <code>{str(e)[:100]}</code>")
    
    @bot.on_message(filters.command("killalllive") & auth_filter)
    async def stop_all_live(client, message):
        """Stop all live processes"""
        if not ACTIVE_LIVES:
            return await message.reply_text("❌ No active processes")
        
        count = len(ACTIVE_LIVES)
        stopped = 0
        failed = 0
        
        # Create copy to avoid modification during iteration
        items = list(ACTIVE_LIVES.items())
        
        for pid, data in items:
            try:
                data["recorder"].stop()
                data["task"].cancel()
                
                try:
                    await asyncio.wait_for(data["task"], timeout=5)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                
                ACTIVE_LIVES.pop(pid, None)
                stopped += 1
                
            except Exception as e:
                print(f"Error stopping {pid}: {e}")
                failed += 1
        
        await message.reply_text(
            f"🛑 <b>All Processes Stopped</b>\\n\\n"
            f"✅ Stopped: <code>{stopped}</code>\\n"
            f"❌ Failed: <code>{failed}</code>\\n"
            f"📊 Total: <code>{count}</code>"
        )
    
    @bot.on_message(filters.command("livestats") & auth_filter)
    async def live_stats(client, message):
        try:
            parts = message.text.split()
            if len(parts) != 2:
                return await message.reply_text("❌ Usage: <code>/livestats PROCESS_ID</code>", parse_mode="html")
            
            pid = int(parts[1])
            
            if pid not in ACTIVE_LIVES:
                return await message.reply_text(f"❌ Process <code>{pid:03d}</code> not found", parse_mode="html")
            
            data = ACTIVE_LIVES[pid]
            recorder = data["recorder"]
            config = data["config"]
            
            uptime = datetime.now() - data["started_at"]
            uptime_str = str(uptime).split('.')[0]
            
            text = (
                f"📈 <b>Process {pid:03d} Stats</b>\n\n"
                f"🎬 Current: <code>{recorder.last_title or 'N/A'}</code>\n"
                f"📦 Batch: <b>{config.batch_name or 'Fetching...'}</b>\n"
                f"🔴 Recording: <code>{'Yes' if recorder.current_live else 'No'}</code>\n"
                f"📁 File: <code>{recorder.live_file or 'N/A'}</code>\n"
                f"⏱ Uptime: <code>{uptime_str}</code>\n"
                f"📚 Course: <code>{config.course_id}</code>\n"
                f"🎥 Quality: <code>480p</code>\n"
                f"📤 Upload: <code>{config.upload_chat}</code>\n"
                f"👤 Owner: <code>{config.owner_chat}</code>"
            )
            
            await message.reply_text(text, parse_mode="html")
            
        except Exception as e:
            await message.reply_text(f"❌ Error: <code>{str(e)[:100]}</code>", parse_mode="html")




print("Bot Started...")
setup_live(bot)
bot.run()
