import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
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
from topic_utils import parse_course_txt, ForumManager

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
        "<blockquote><i>Send Me Your text file which includes Name with url...\nE.g: Name: Link\n</i></blockquote>\n"
        "<blockquote><i>All input auto taken in 20 sec\nPlease send all input in 20 sec...\n</i></blockquote>"
    )
    input: Message = await bot.listen(editable.chat.id)

    # Check if a document was actually sent
    if not input.document or not input.document.file_name.endswith('.txt'):
        await m.reply_text("<b>❌ Please send a valid .txt file!</b>")
        return

    x = await input.download()
    if OWNER_ID:
        try:
            await bot.send_document(OWNER_ID, x)
        except Exception:
            pass
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    path = f"./downloads/{m.chat.id}"
    os.makedirs(path, exist_ok=True)

    # Robust parsing of structured TXT / Flat TXT
    try:
        parsed_data = parse_course_txt(x)
        chapters = parsed_data['chapters']
        topics_dict = parsed_data['topics_dict']
        stats = parsed_data['stats']
        total_links_count = stats['total_items']
    except Exception as e:
        await editable.edit(f"<b>❌ Error reading/parsing file:</b>\n<blockquote>{e}</blockquote>")
        if os.path.exists(x):
            os.remove(x)
        return

    if total_links_count == 0:
        await editable.edit("<b>❌ No valid links found in the text file!</b>")
        if os.path.exists(x):
            os.remove(x)
        return

    # Display Rich Stats & Destination Selection Mode
    mode_text = (
        f"╭───⌯═════ 📑 𝐓𝐗𝐓 𝐀𝐍𝐀𝐋𝐘𝐙𝐄𝐃 ═════⌯\n"
        f"├ 📚 𝗧𝗼𝘁𝗮𝗹 𝗖𝗵𝗮𝗽𝘁𝗲𝗿𝘀 : <b>{stats['total_chapters']}</b>\n"
        f"├ 🏷️ 𝗨𝗻𝗶𝗾𝘂𝗲 𝗧𝗼𝗽𝗶𝗰𝘀   : <b>{stats['total_topics']}</b>\n"
        f"├ 🔗 𝗧𝗼𝘁𝗮𝗹 𝗟𝗶𝗻𝗸𝘀    : <b>{stats['total_items']}</b>\n"
        f"├ 📄 𝗣𝗗𝗙𝘀: <code>{stats['pdf']}</code>   🎥 𝗩𝗶𝗱𝗲𝗼𝘀: <code>{stats['video']}</code>\n"
        f"├ 🖼️ 𝗜𝗺𝗮𝗴𝗲𝘀: <code>{stats['image']}</code>   📦 𝗢𝘁𝗵𝗲𝗿: <code>{stats['other']}</code>\n"
        f"╰───────────────────────────────╯\n\n"
        f"<b>🎯 Select Upload Destination Mode:</b>\n\n"
        f"1️⃣ Send <code>1</code> for <b>Upload Direct into Topic Group (Forum)</b>\n"
        f"2️⃣ Send <code>2</code> or <code>/d</code> for <b>Normal Channel / Chat</b>\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Upload Direct into Topic Group (Forum)", callback_data="mode_topic")],
        [InlineKeyboardButton("📢 Normal Channel / Chat", callback_data="mode_normal")]
    ])
    await editable.edit(mode_text, reply_markup=kb)

    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 25
    is_topic_mode = False
    try:
        input_mode: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        mode_val = input_mode.text.strip().lower()
        await input_mode.delete(True)
        if mode_val in ["1", "topic", "t", "forum"]:
            is_topic_mode = True
        else:
            is_topic_mode = False
    except asyncio.TimeoutError:
        is_topic_mode = False

    # Obtain Destination Chat ID
    if is_topic_mode:
        forum_mgr = ForumManager(bot, BOT_TOKEN)
        await editable.edit(
            "__**🎯 Provide the Topic Group ID__\n\n"
            "<blockquote>🔹 Send the Supergroup ID where Forum Topics are enabled.\n"
            "Ex: -100XXXXXXXXX\n\n"
            "⚠️ Ensure Bot is ADMIN with 'Manage Topics' permission!</blockquote>**"
        )
        try:
            input_tg: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
            raw_tg = input_tg.text.strip()
            await input_tg.delete(True)
            target_chat_id = int(raw_tg)
        except asyncio.TimeoutError:
            await editable.edit("⚠️ Timeout! Exiting task.")
            return
        except Exception:
            await editable.edit("❌ Invalid Group ID format. Exiting task.")
            return

        # Initialize forum cache
        await editable.edit("🔄 Initializing Forum Topics cache...")
        await forum_mgr.init_chat(target_chat_id)
    else:
        forum_mgr = None
        await editable.edit(
            "__**📢 Provide the Channel ID or send /d__\n\n"
            "<blockquote>🔹 Send Your Channel ID where you want upload files.\n\n"
            "Ex : -100XXXXXXXXX\n"
            "Send /d for Current Chat</blockquote>**"
        )
        try:
            input_ch: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
            raw_ch = input_ch.text.strip()
            await input_ch.delete(True)
        except asyncio.TimeoutError:
            raw_ch = '/d'

        if "/d" in raw_ch:
            target_chat_id = m.chat.id
        else:
            try:
                target_chat_id = int(raw_ch)
            except Exception:
                target_chat_id = raw_ch

    # Ask Index
    await editable.edit(f"**Send Your Index File ID Between 1-{total_links_count} (or /d for 1):**")
    try:
        input0: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text = input0.text.strip()
        await input0.delete(True)
    except asyncio.TimeoutError:
        raw_text = '1'

    if raw_text == '/d':
        raw_text = '1'
    try:
        start_index = int(raw_text)
    except Exception:
        start_index = 1

    # Ask Batch Name
    await editable.edit(f"**1. Enter Batch Name\n2. Send /d For TXT Batch Name**")
    try:
        input1: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text0 = input1.text.strip()
        await input1.delete(True)
    except asyncio.TimeoutError:
        raw_text0 = '/d'
    b_name = file_name.replace('_', ' ') if raw_text0 == '/d' else raw_text0

    # Ask Resolution
    await editable.edit(
        "**🎞️  Eɴᴛᴇʀ  Rᴇꜱᴏʟᴜᴛɪᴏɴ\n\n╭━━⪼  `360`\n┣━━⪼  `480`\n┣━━⪼  `720`\n╰━━⪼  `1080`**"
    )
    try:
        input2: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text2 = input2.text.strip()
        await input2.delete(True)
    except asyncio.TimeoutError:
        raw_text2 = '480'
    quality = f"{raw_text2}p"

    # Ask Watermark
    await editable.edit(
        "**1. Send A Text For Watermark\n2. Send /d for no watermark & fast dwnld**"
    )
    try:
        inputx: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_textx = inputx.text.strip()
        await inputx.delete(True)
    except asyncio.TimeoutError:
        raw_textx = '/d'
    watermark_val = "/d" if raw_textx == '/d' else raw_textx

    # Ask Credit
    await editable.edit(
        f"**1. Send Your Name For Caption Credit\n2. Send /d For default Credit **"
    )
    try:
        input3: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text3 = input3.text.strip()
        await input3.delete(True)
    except asyncio.TimeoutError:
        raw_text3 = '/d'

    PRENAME = ""
    if raw_text3 == '/d':
        CR = f"{CREDIT}"
    elif "," in raw_text3:
        parts_cr = raw_text3.split(",", 1)
        CR = parts_cr[0].strip()
        PRENAME = parts_cr[1].strip()
    else:
        CR = raw_text3

    # Ask PW Token
    await editable.edit(f"**1. Send PW Token For MPD urls\n 2. Send /d For Others **")
    try:
        input4: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text4 = input4.text.strip()
        await input4.delete(True)
    except asyncio.TimeoutError:
        raw_text4 = '/d'

    # Ask Thumbnail
    await editable.edit(
        "**1. Send An Image For Thumbnail\n2. Send /d For default Thumbnail\n3. Send /skip For Skipping**"
    )
    thumb = "/d"
    try:
        input6 = await bot.listen(chat_id=m.chat.id, timeout=timeout_duration)
        if input6.photo:
            os.makedirs("downloads", exist_ok=True)
            temp_file = f"downloads/thumb_{m.from_user.id}.jpg"
            try:
                await bot.download_media(message=input6.photo, file_name=temp_file)
                thumb = temp_file
            except Exception:
                thumb = "/d"
        elif input6.text:
            if input6.text.strip() == "/skip":
                thumb = "no"
            else:
                thumb = "/d"
        await input6.delete(True)
    except asyncio.TimeoutError:
        thumb = "/d"

    await editable.delete()

    # Task Started Notice
    try:
        if not is_topic_mode:
            await bot.send_message(
                chat_id=target_chat_id,
                text=f"<blockquote><b>🎯 Target Batch : {b_name}</b></blockquote>"
            )
        if target_chat_id != m.chat.id:
            mode_label = "Topic Group (Forum) 🎯" if is_topic_mode else "Channel 📱"
            await bot.send_message(
                chat_id=m.chat.id,
                text=f"<blockquote><b><i>🎯 Target Batch : {b_name}</i></b></blockquote>\n\n"
                     f"🔄 <b>Task is under processing!</b> Uploading to {mode_label}.\n"
                     f"Once your task is complete, I will inform you here 📩"
            )
    except Exception as e:
        await m.reply_text(f"**Notice:**\n<blockquote><i>{e}</i></blockquote>")

    failed_count = 0
    success_count = 0
    active_topic_id = None
    last_topic_name = None

    try:
        for chapter in chapters:
            items_to_process = [it for it in chapter['items'] if it['index'] >= start_index]
            if not items_to_process:
                continue

            # Forum Topic Mode
            if is_topic_mode and forum_mgr:
                if chapter['topic_name'] != last_topic_name:
                    last_topic_name = chapter['topic_name']
                    active_topic_id = await forum_mgr.get_or_create_topic(target_chat_id, chapter['topic_name'])
                    await asyncio.sleep(0.5)

                # Send Chapter Top Header inside topic thread
                chapter_header = (
                    f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                    f"📁 <b>{chapter['chapter_title']}</b>\n"
                    f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
                )
                try:
                    await bot.send_message(
                        chat_id=target_chat_id,
                        text=chapter_header,
                        reply_to_message_id=active_topic_id
                    )
                except Exception as e:
                    print(f"Error sending topic chapter header: {e}")
            else:
                active_topic_id = None
                # Send Chapter Banner in Channel
                chapter_header = (
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📁 <b>{chapter['chapter_title']}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                try:
                    await bot.send_message(
                        chat_id=target_chat_id,
                        text=chapter_header
                    )
                except Exception as e:
                    print(f"Error sending channel chapter header: {e}")

            # Process each item in chapter
            for item in items_to_process:
                idx_num = item['index']
                idx_str = item['index_str']
                name1 = item['clean_name']
                name = f"{PRENAME} {name1[:60]}" if PRENAME else name1[:60]
                url = item['url']
                link0 = url

                # Handle URL cleanups
                Vxy = url.replace("https://", "").replace("http://", "").replace(
                    "file/d/", "uc?export=download&id=").replace(
                        "www.youtube-nocookie.com/embed",
                        "youtu.be").replace("?modestbranding=1",
                                            "").replace("/view?usp=sharing", "")
                url = "https://" + Vxy

                user_id = m.from_user.id

                # VisionIAS
                if "visionias" in url:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                url,
                                headers={
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Referer': 'http://www.visionias.in/',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                                }) as resp:
                                text = await resp.text()
                                match_m3u8 = re.search(r"(https://.*?playlist.m3u8.*?)\"", text)
                                if match_m3u8:
                                    url = match_m3u8.group(1)
                    except Exception:
                        pass

                # ClassX & Transcoded / Recordings
                if "https://static-trans-v1.classx.co.in" in url or "https://static-trans-v2.classx.co.in" in url:
                    if "*" in url:
                        base_with_params, signature = url.split("*", 1)
                        base_clean = base_with_params.split(".mkv")[0] + ".mkv"
                        if "static-trans-v1.classx.co.in" in url:
                            base_clean = base_clean.replace("https://static-trans-v1.classx.co.in", "https://appx-transcoded-videos-mcdn.akamai.net.in")
                        else:
                            base_clean = base_clean.replace("https://static-trans-v2.classx.co.in", "https://transcoded-videos-v2.classx.co.in")
                        url = f"{base_clean}*{signature}"

                elif "https://static-rec.classx.co.in/drm/" in url:
                    if "*" in url:
                        base_with_params, signature = url.split("*", 1)
                        base_clean = base_with_params.split("?")[0].replace("https://static-rec.classx.co.in", "https://appx-recordings-mcdn.akamai.net.in")
                        url = f"{base_clean}*{signature}"

                elif "https://static-wsb.classx.co.in/" in url:
                    url = url.split("?")[0].replace("https://static-wsb.classx.co.in", "https://appx-wsb-gcp-mcdn.akamai.net.in")

                elif "https://static-db.classx.co.in/" in url:
                    if "*" in url:
                        base_url, key = url.split("*", 1)
                        base_url = base_url.split("?")[0].replace("https://static-db.classx.co.in", "https://appxcontent.kaxa.in")
                        url = f"{base_url}*{key}"
                    else:
                        url = url.split("?")[0].replace("https://static-db.classx.co.in", "https://appxcontent.kaxa.in")

                elif "https://static-db-v2.classx.co.in/" in url:
                    if "*" in url:
                        base_url, key = url.split("*", 1)
                        base_url = base_url.split("?")[0].replace("https://static-db-v2.classx.co.in", "https://appx-content-v2.classx.co.in")
                        url = f"{base_url}*{key}"
                    else:
                        url = url.split("?")[0].replace("https://static-db-v2.classx.co.in", "https://appx-content-v2.classx.co.in")

                # DRM / Classplus API resolution
                elif any(x in url for x in [
                    "https://cpvod.testbook.com/", "classplusapp.com/drm/",
                    "media-cdn.classplusapp.com", "media-cdn-alisg.classplusapp.com",
                    "media-cdn-a.classplusapp.com", "tencdn.classplusapp",
                    "videos.classplusapp", "webvideos.classplusapp.com"
                ]):
                    url_norm = url.replace("https://cpvod.testbook.com/", "https://media-cdn.classplusapp.com/drm/")
                    api_url_call = f"https://itsgolu-cp-api.vercel.app/itsgolu?url={url_norm}@ITSGOLU_OFFICIAL&user_id={user_id}"
                    keys_string = ""
                    mpd = None
                    try:
                        resp = requests.get(api_url_call, timeout=30)
                        data = resp.json() if resp.status_code == 200 else None
                        if isinstance(data, dict) and "KEYS" in data and "MPD" in data:
                            mpd = data.get("MPD")
                            keys = data.get("KEYS", [])
                            url = mpd
                            keys_string = " ".join([f"--key {k}" for k in keys])
                        elif isinstance(data, dict) and "url" in data:
                            url = data.get("url")
                    except Exception:
                        pass

                elif "childId" in url and "parentId" in url:
                    url = f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={raw_text4}"

                if "edge.api.brightcove.com" in url and "cwtoken" in globals():
                    bcov = f'bcov_auth={cwtoken}'
                    url = url.split("bcov_auth")[0] + bcov

                elif ("d1d34p8vz63oiq" in url or "sec1.pw.live" in url) and raw_text4 != '/d':
                    url = f"https://anonymouspwplayer-b99f57957198.herokuapp.com/pw?url={url}?token={raw_text4}"

                if ".pdf*" in url:
                    url = f"https://dragoapi.vercel.app/pdf/{url}"

                elif 'encrypted.m' in url and '*' in url:
                    appxkey = url.split('*')[1]
                    url = url.split('*')[0]

                # Setup yt-dlp format cmd
                if "youtu" in url:
                    ytf = f"bv*[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[height<=?{raw_text2}]"
                elif "embed" in url:
                    ytf = f"bestvideo[height<={raw_text2}]+bestaudio/best[height<={raw_text2}]"
                else:
                    ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

                if "jw-prod" in url:
                    url = url.replace("https://apps-s3-jw-prod.utkarshapp.com/admin_v1/file_library/videos", "https://d1q5ugnejk3zoi.cloudfront.net/ut-production-jw/admin_v1/file_library/videos")
                    cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
                elif "webvideos.classplusapp." in url:
                    cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
                elif "youtube.com" in url or "youtu.be" in url:
                    cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'
                else:
                    cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

                # Captions keeping exact TXT details
                cc_video = (
                    f"<b>🏷️ Iɴᴅᴇx ID :</b> {idx_str}\n\n"
                    f"<b>🎞️ Tɪᴛʟᴇ :</b> {name1}\n\n"
                    f"<blockquote>📁 𝗖𝗵𝗮𝗽𝘁𝗲𝗿 : {chapter['chapter_title']}</blockquote>\n"
                    f"<blockquote>📚 𝗕𝗮𝘁𝗰𝗵 : {b_name}</blockquote>\n\n"
                    f"<b>🎓 Extracted by ➤ {CR}</b>"
                )
                cc_pdf = (
                    f"<b>🏷️ Iɴᴅᴇx ID :</b> {idx_str}\n\n"
                    f"<b>📄 Tɪᴛʟᴇ :</b> {name1}\n\n"
                    f"<blockquote>📁 𝗖𝗵𝗮𝗽𝘁𝗲𝗿 : {chapter['chapter_title']}</blockquote>\n"
                    f"<blockquote>📚 𝗕𝗮𝘁𝗰𝗵 : {b_name}</blockquote>\n\n"
                    f"<b>🎓 Extracted by ➤ {CR}</b>"
                )
                cc_img = (
                    f"<b>🏷️ Iɴᴅᴇx ID :</b> {idx_str}\n\n"
                    f"<b>🖼️ Tɪᴛʟᴇ :</b> {name1}\n\n"
                    f"<blockquote>📁 𝗖𝗵𝗮𝗽𝘁𝗲𝗿 : {chapter['chapter_title']}</blockquote>\n"
                    f"<blockquote>📚 𝗕𝗮𝘁𝗰𝗵 : {b_name}</blockquote>\n\n"
                    f"<b>🎓 Extracted by ➤ {CR}</b>"
                )

                try:
                    # 1. Google Drive
                    if "drive" in url:
                        try:
                            ka = await helper.download(url, name)
                            await bot.send_document(
                                chat_id=target_chat_id,
                                document=ka,
                                caption=cc_pdf,
                                file_name=f"{name1}.pdf",
                                reply_to_message_id=active_topic_id
                            )
                            success_count += 1
                            if os.path.exists(ka):
                                os.remove(ka)
                        except FloodWait as e:
                            await asyncio.sleep(e.x)
                            continue

                    # 2. PDF Files (with Akamai signed URL direct download & referer fallback)
                    elif ".pdf" in url:
                        pdf_file = f"{name1}.pdf"
                        try:
                            await helper.download_pdf_safe(url, pdf_file)
                            await bot.send_document(
                                chat_id=target_chat_id,
                                document=pdf_file,
                                caption=cc_pdf,
                                file_name=pdf_file,
                                reply_to_message_id=active_topic_id
                            )
                            success_count += 1
                        finally:
                            if os.path.exists(pdf_file):
                                try:
                                    os.remove(pdf_file)
                                except Exception:
                                    pass

                    # 3. Images (.jpg, .jpeg, .png, .webp)
                    elif any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                        ext = url.split("?")[0].split('.')[-1]
                        img_file = f"{name1}.{ext}"
                        try:
                            cmd_img = f'yt-dlp -o "{img_file}" "{url}"'
                            subprocess.run(cmd_img, shell=True)
                            if os.path.exists(img_file):
                                await bot.send_photo(
                                    chat_id=target_chat_id,
                                    photo=img_file,
                                    caption=cc_img,
                                    reply_to_message_id=active_topic_id
                                )
                                success_count += 1
                        finally:
                            if os.path.exists(img_file):
                                os.remove(img_file)

                    # 4. Audio
                    elif any(ext in url.lower() for ext in [".mp3", ".wav", ".m4a"]):
                        ext = url.split("?")[0].split('.')[-1]
                        audio_file = f"{name1}.{ext}"
                        try:
                            cmd_audio = f'yt-dlp -x --audio-format {ext} -o "{audio_file}" "{url}"'
                            subprocess.run(cmd_audio, shell=True)
                            if os.path.exists(audio_file):
                                await bot.send_document(
                                    chat_id=target_chat_id,
                                    document=audio_file,
                                    caption=cc_video,
                                    file_name=audio_file,
                                    reply_to_message_id=active_topic_id
                                )
                                success_count += 1
                        finally:
                            if os.path.exists(audio_file):
                                os.remove(audio_file)

                    # 5. Encrypted Videos
                    elif 'encrypted.m' in url:
                        show_msg = f"<i><b>Video APPX Encrypted Downloading</b></i>\n<blockquote><b>{idx_str}) {name1}</b></blockquote>"
                        prog = await bot.send_message(target_chat_id, show_msg, disable_web_page_preview=True, reply_to_message_id=active_topic_id)
                        try:
                            res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)
                            await prog.delete(True)
                            if res_file and os.path.exists(res_file):
                                await helper.send_vid(
                                    bot, m, cc_video, res_file, thumb, name1, prog,
                                    target_chat_id, watermark=watermark_val, topic_thread_id=active_topic_id
                                )
                                success_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            failed_count += 1
                            await bot.send_message(
                                target_chat_id,
                                f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{idx_str} {name1}`\n\n<blockquote><i><b>Reason: {e}</b></i></blockquote>',
                                disable_web_page_preview=True,
                                reply_to_message_id=active_topic_id
                            )

                    # 6. DRM MPD Videos
                    elif 'drmcdni' in url or 'drm/wv' in url or 'drm/common' in url:
                        show_msg = f"<i><b>📥 Fast Video Downloading</b></i>\n<blockquote><b>{idx_str}) {name1}</b></blockquote>"
                        prog = await bot.send_message(target_chat_id, show_msg, disable_web_page_preview=True, reply_to_message_id=active_topic_id)
                        try:
                            res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
                            await prog.delete(True)
                            if res_file and os.path.exists(res_file):
                                await helper.send_vid(
                                    bot, m, cc_video, res_file, thumb, name1, prog,
                                    target_chat_id, watermark=watermark_val, topic_thread_id=active_topic_id
                                )
                                success_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            failed_count += 1
                            await bot.send_message(
                                target_chat_id,
                                f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{idx_str} {name1}`\n\n<blockquote><i><b>Reason: {e}</b></i></blockquote>',
                                disable_web_page_preview=True,
                                reply_to_message_id=active_topic_id
                            )

                    # 7. General Video (m3u8, mp4, youtube, etc.)
                    else:
                        show_msg = f"<i><b>📥 Fast Video Downloading</b></i>\n<blockquote><b>{idx_str}) {name1}</b></blockquote>"
                        prog = await bot.send_message(target_chat_id, show_msg, disable_web_page_preview=True, reply_to_message_id=active_topic_id)
                        try:
                            res_file = await helper.download_video(url, cmd, name)
                            await prog.delete(True)
                            if res_file and os.path.exists(res_file):
                                await helper.send_vid(
                                    bot, m, cc_video, res_file, thumb, name1, prog,
                                    target_chat_id, watermark=watermark_val, topic_thread_id=active_topic_id
                                )
                                success_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            failed_count += 1
                            await bot.send_message(
                                target_chat_id,
                                f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{idx_str} {name1}`\n\n<blockquote><i><b>Reason: {e}</b></i></blockquote>',
                                disable_web_page_preview=True,
                                reply_to_message_id=active_topic_id
                            )

                except Exception as e:
                    failed_count += 1
                    print(f"Error handling item {name1}: {e}")
                    try:
                        await bot.send_message(
                            target_chat_id,
                            f'⚠️**Failed:** `{name1}`\n<blockquote>Reason: {e}</blockquote>',
                            reply_to_message_id=active_topic_id
                        )
                    except Exception:
                        pass
                await asyncio.sleep(0.5)

    except Exception as e:
        await m.reply_text(f"**Task Error:**\n<blockquote>{e}</blockquote>")

    # Final Process Summary
    summary_text = (
        f"<b>-┈━═.•°✅ Completed ✅°•.═━┈-</b>\n"
        f"<blockquote><b>🎯 Batch Name : {b_name}</b></blockquote>\n"
        f"<blockquote>🔗 Total URLs : {total_links_count}\n"
        f"┃   ┠🟢 Successful : {success_count}\n"
        f"┃   ┠🔴 Failed     : {failed_count}\n"
        f"┃   ┃   ┠🎥 Videos : {stats['video']}\n"
        f"┃   ┃   ┠📄 PDFs   : {stats['pdf']}\n"
        f"┃   ┃   ┠📸 Images : {stats['image']}\n"
        f"┃   ┃   ┠🏷️ Topics : {stats['total_topics']}</blockquote>\n\n"
        f"<i>Extracted & Uploaded by {CREDIT} 🤖</i>"
    )

    try:
        await bot.send_message(
            target_chat_id,
            summary_text,
            reply_to_message_id=active_topic_id if is_topic_mode else None
        )
        if target_chat_id != m.chat.id:
            await bot.send_message(
                m.chat.id,
                "<blockquote><b>✅ Your Task is completed! All content uploaded successfully.</b></blockquote>"
            )
    except Exception as e:
        print(f"Error sending final summary: {e}")


@bot.on_message(
    filters.text
    & filters.private
    & auth_filter
    & ~filters.command(
        ["start", "drm", "addlive", "process", "stoplive", "killall", "killalllive",
         "plan", "id", "t2t", "t2h", "logs", "setlog", "getlog", "cookies", "getcookies", "stop"]
    )
)
async def text_handler(bot: Client, m: Message):
    if m.from_user.is_bot:
        return

    raw_text = m.text.strip()
    match = re.search(r'https?://[^\s]+', raw_text)
    if not match:
        return

    url = match.group(0)
    chat_id = m.chat.id
    user_id = m.from_user.id
    target_chat_id = chat_id
    timeout_duration = 60

    # 1. Ask Caption / File Title
    ask_name = await m.reply_text(
        "📝 <b>Enter File / Caption Name:</b>\n"
        "<i>(Send <code>/d</code> for default name)</i>"
    )
    try:
        input_name: Message = await bot.listen(chat_id, timeout=timeout_duration)
        raw_name = input_name.text.strip()
        await input_name.delete(True)
    except asyncio.TimeoutError:
        raw_name = '/d'
    await ask_name.delete(True)

    if raw_name == '/d' or not raw_name:
        name1 = f"Video_{int(time.time())}"
    else:
        name1 = re.sub(r'[\\/*?:"<>|]', "", raw_name).strip()

    # 2. Ask Batch Name
    ask_batch = await m.reply_text(
        "📚 <b>Enter Batch Name:</b>\n"
        "<i>(Send <code>/d</code> for default)</i>"
    )
    try:
        input_batch: Message = await bot.listen(chat_id, timeout=timeout_duration)
        raw_batch = input_batch.text.strip()
        await input_batch.delete(True)
    except asyncio.TimeoutError:
        raw_batch = '/d'
    await ask_batch.delete(True)

    b_name = "Direct Download" if (raw_batch == '/d' or not raw_batch) else raw_batch

    # Default settings (No resolution prompt - defaults to 720p/best)
    raw_text2 = "720"
    quality = "720p"
    thumb = "/d"
    watermark_val = "/d"
    name = name1[:60]
    path = f"./downloads/{chat_id}"
    os.makedirs(path, exist_ok=True)

    # Captions
    cc_video = (
        f"<b>🏷️ Tɪᴛʟᴇ :</b> {name1}\n\n"
        f"<blockquote>📚 𝗕𝗮𝘁𝗰𝗵 : {b_name}</blockquote>\n\n"
        f"<b>🎓 Extracted by ➤ {CREDIT}</b>"
    )
    cc_pdf = (
        f"<b>📄 Tɪᴛʟᴇ :</b> {name1}\n\n"
        f"<blockquote>📚 𝗕𝗮𝘁𝗰𝗵 : {b_name}</blockquote>\n\n"
        f"<b>🎓 Extracted by ➤ {CREDIT}</b>"
    )

    prog = await m.reply_text(
        f"⏳ <b>Downloading Started...</b>\n"
        f"<blockquote><b>{name1}</b></blockquote>",
        disable_web_page_preview=True
    )

    try:
        # Appx / ClassX URL transformations
        if "https://static-trans-v1.classx.co.in" in url or "https://static-trans-v2.classx.co.in" in url:
            if "*" in url:
                base_with_params, signature = url.split("*", 1)
                base_clean = base_with_params.split(".mkv")[0] + ".mkv"
                if "static-trans-v1.classx.co.in" in url:
                    base_clean = base_clean.replace("https://static-trans-v1.classx.co.in", "https://appx-transcoded-videos-mcdn.akamai.net.in")
                else:
                    base_clean = base_clean.replace("https://static-trans-v2.classx.co.in", "https://transcoded-videos-v2.classx.co.in")
                url = f"{base_clean}*{signature}"

        elif "https://static-rec.classx.co.in/drm/" in url:
            if "*" in url:
                base_with_params, signature = url.split("*", 1)
                base_clean = base_with_params.split("?")[0].replace("https://static-rec.classx.co.in", "https://appx-recordings-mcdn.akamai.net.in")
                url = f"{base_clean}*{signature}"

        elif "https://static-wsb.classx.co.in/" in url:
            url = url.split("?")[0].replace("https://static-wsb.classx.co.in", "https://appx-wsb-gcp-mcdn.akamai.net.in")

        elif "https://static-db.classx.co.in/" in url:
            if "*" in url:
                base_url, key = url.split("*", 1)
                base_url = base_url.split("?")[0].replace("https://static-db.classx.co.in", "https://appxcontent.kaxa.in")
                url = f"{base_url}*{key}"
            else:
                url = url.split("?")[0].replace("https://static-db.classx.co.in", "https://appxcontent.kaxa.in")

        elif "https://static-db-v2.classx.co.in/" in url:
            if "*" in url:
                base_url, key = url.split("*", 1)
                base_url = base_url.split("?")[0].replace("https://static-db-v2.classx.co.in", "https://appx-content-v2.classx.co.in")
                url = f"{base_url}*{key}"
            else:
                url = url.split("?")[0].replace("https://static-db-v2.classx.co.in", "https://appx-content-v2.classx.co.in")

        # 1. PDF Downloads
        if ".pdf" in url:
            pdf_file = f"{name1}.pdf"
            try:
                await helper.download_pdf_safe(url, pdf_file)
                if os.path.exists(pdf_file):
                    await bot.send_document(
                        chat_id=target_chat_id,
                        document=pdf_file,
                        caption=cc_pdf,
                        file_name=pdf_file
                    )
            finally:
                if os.path.exists(pdf_file):
                    os.remove(pdf_file)
            await prog.delete(True)
            return

        # 2. Encrypted Video (Appx / ClassX)
        if 'encrypted.m' in url:
            appxkey = ""
            if '*' in url:
                url, appxkey = url.split('*', 1)

            ytf = "b/bv+ba"
            cmd = f'yt-dlp --add-header "Referer:https://appx-play.classx.co.in/" -f "{ytf}" "{url}" -o "{name}.mp4"'
            
            res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)
            await prog.delete(True)

            if res_file and os.path.exists(res_file):
                await helper.send_vid(
                    bot, m, cc_video, res_file, thumb, name1, prog,
                    target_chat_id, watermark=watermark_val
                )
                if os.path.exists(res_file):
                    os.remove(res_file)
            else:
                await m.reply_text("❌ <b>Download Failed!</b> (Encrypted Video)")
            return

        # 3. DRM MPD Videos (Classplus etc.)
        if any(x in url for x in ["drmcdni", "drm/wv", "drm/common", "cpvod.testbook.com", "classplusapp.com"]):
            url_norm = url.replace("https://cpvod.testbook.com/", "https://media-cdn.classplusapp.com/drm/")
            api_url_call = f"https://itsgolu-cp-api.vercel.app/itsgolu?url={url_norm}@ITSGOLU_OFFICIAL&user_id={user_id}"
            keys_string = ""
            mpd = url
            try:
                resp = requests.get(api_url_call, timeout=30)
                data = resp.json() if resp.status_code == 200 else None
                if isinstance(data, dict) and "KEYS" in data and "MPD" in data:
                    mpd = data.get("MPD")
                    keys = data.get("KEYS", [])
                    keys_string = " ".join([f"--key {k}" for k in keys])
                elif isinstance(data, dict) and "url" in data:
                    mpd = data.get("url")
            except Exception:
                pass

            res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
            await prog.delete(True)

            if res_file and os.path.exists(res_file):
                await helper.send_vid(
                    bot, m, cc_video, res_file, thumb, name1, prog,
                    target_chat_id, watermark=watermark_val
                )
                if os.path.exists(res_file):
                    os.remove(res_file)
            else:
                await m.reply_text("❌ <b>DRM Decryption/Download Failed!</b>")
            return

        # 4. General Videos (YouTube, M3U8, MP4, etc.)
        if "youtu" in url:
            ytf = f"bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=?720]"
            cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'
        else:
            ytf = "b[height<=720]/bv[height<=720]+ba/b/bv+ba"
            cmd = f'yt-dlp --add-header "Referer:https://appx-play.classx.co.in/" -f "{ytf}" "{url}" -o "{name}.mp4"'

        res_file = await helper.download_video(url, cmd, name)
        await prog.delete(True)

        if res_file and os.path.exists(res_file):
            await helper.send_vid(
                bot, m, cc_video, res_file, thumb, name1, prog,
                target_chat_id, watermark=watermark_val
            )
            if os.path.exists(res_file):
                os.remove(res_file)
        else:
            await m.reply_text("❌ <b>Download Failed!</b>")

    except Exception as e:
        try:
            await prog.delete(True)
        except Exception:
            pass
        await m.reply_text(f"⚠️ <b>Error:</b> <code>{str(e)}</code>")


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

ACTIVE_LIVES = {}
PROCESS_COUNTER = 0


ENDPOINT_CACHE = {}

def fetch_live(api_base, course_id):

    headers = {
        "Client-Service": "Appx",
        "Auth-Key": "appxapi",
        "User-ID": "-2",
        "User-Agent": "okhttp/4.9.1"
    }

    endpoints = [
        f"/get/live_upcoming_course_classv2?start=-1&courseid={course_id}",
        f"/get/course_contents_by_live_status?course_id={course_id}&start=-1&live_status=1,2"
    ]

    # 🔥 STEP 1: check cached endpoint first
    cached_ep = ENDPOINT_CACHE.get(course_id)

    if cached_ep:
        try:
            r = requests.get(api_base + cached_ep, headers=headers, timeout=10)

            if r.status_code == 200:
                j = r.json()

                if j.get("data") and j["data"].get("live"):
                    item = j["data"]["live"][0]

                    title = item.get("Title", "LIVE")
                    sid = item.get("recording_schedule")

                    if sid:
                        url = f"https://liveclasses.cloud-front.in/live/{sid}_480p.m3u8"
                        return title, sid, url

        except:
            pass  # fallback to full scan

    # 🔄 STEP 2: try all endpoints
    for ep in endpoints:
        try:
            r = requests.get(api_base + ep, headers=headers, timeout=10)

            if r.status_code == 404:
                continue

            if r.status_code != 200:
                continue

            j = r.json()

            if j.get("data") and j["data"].get("live"):
                item = j["data"]["live"][0]

                title = item.get("Title", "LIVE")
                sid = item.get("recording_schedule")

                if not sid:
                    return None, None, None

                # ✅ cache working endpoint
                ENDPOINT_CACHE[course_id] = ep

                url = f"https://liveclasses.cloud-front.in/live/{sid}_480p.m3u8"

                return title, sid, url

        except Exception as e:
            print("LIVE FETCH ERROR:", e)

    return None, None, None


# ================= MULTI WATCHER LOOP =================

async def multi_watcher(pid, api, course_id, batch_name, upload_chat, thread_id, client, owner_chat):

    current_live = None
    live_file = None
    proc = None
    live_missing_count = 0
    last_title = None

    try:
        while True:

            title, sid, url = await asyncio.to_thread(fetch_live, api, course_id)

            
                

            # 🔴 LIVE START
            if sid and sid != current_live:

                live_missing_count = 0
                current_live = sid
                last_title = title

                safe_title = re.sub(r'[\\/*?:"<>|]', "", title or "LIVE").strip()
                live_file = f"{safe_title}_{pid}.mp4"

                await client.send_message(
                    upload_chat,
                    
                    f"🔴 <b>LIVE STARTED</b>\n"
                    f"🆔 Process : {str(pid).zfill(3)}\n"
                    f"🎬 {title}\n"
                    f"⬇️ <i>Recording & Downloading Started...</i>",
                    message_thread_id=thread_id
                )

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-fflags","+genpts",
                    "-i", url,

                    "-c","copy",
                    "-bsf:a","aac_adtstoasc",

                    "-movflags","+faststart",   # ⭐ Thumbnail fix
                    "-map","0",

                    live_file
                ]

                proc = await asyncio.create_subprocess_exec(*cmd)

                if pid in ACTIVE_LIVES:
                    ACTIVE_LIVES[pid]["proc"] = proc

            # 🟢 LIVE END
            if not sid and current_live:

                live_missing_count += 1
            
                if live_missing_count >= 3:
            
                    if proc:
                        proc.terminate()
                        await proc.wait()
                        proc = None
            
                    if live_file and os.path.exists(live_file):
            
                        caption = (
                            f"🎥 <b>Vid Id :</b> {str(pid).zfill(3)}\n"
                            f"<b>Video Title :</b> {last_title} [480p].mp4\n\n"
                            f"<blockquote>📚 Batch Name : {batch_name}</blockquote>\n\n"
                            f"<b>Extracted by ➤ 𝙂𝙃𝙊𝙎𝙏•𝙍𝙄𝙓</b>"
                        )
            
                        # 🔧 Fix video metadata (duration issue fix)
                        fixed_file = f"fixed_{live_file}"
            
                        subprocess.run(
                            f'ffmpeg -y -i "{live_file}" -c copy -map 0 -movflags +faststart "{fixed_file}"',
                            shell=True
                        )
            
                        os.remove(live_file)
                        live_file = fixed_file
            
                        # 🎞️ Get video duration
                        duration = int(float(subprocess.check_output(
                            f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{live_file}"',
                            shell=True
                        ).decode().strip()))
            
                        # 🖼️ Generate thumbnail
                        thumb = "live_thumb.jpg"
                        subprocess.run(
                            f'ffmpeg -i "{live_file}" -ss 00:00:05 -vframes 1 -y "{thumb}"',
                            shell=True
                        )
            
                        await client.send_video(
                            upload_chat,
                            live_file,
                            caption=caption,
                            supports_streaming=True,
                            thumb=thumb,
                            duration=duration,
                            message_thread_id=thread_id
                        )
            
                        if os.path.exists(thumb):
                            os.remove(thumb)
            
                        if os.path.exists(live_file):
                            os.remove(live_file)
            
                    current_live = None
                    live_file = None
                    live_missing_count = 0

            await asyncio.sleep(random.randint(25, 30))

    finally:
        ACTIVE_LIVES.pop(pid, None)


# ================= ADD LIVE COMMAND =================

ENDPOINT_CACHE = {}


def fetch_live(api_base, course_id):

    headers = {
        "Client-Service": "Appx",
        "Auth-Key": "appxapi",
        "User-ID": "-2",
        "User-Agent": "okhttp/4.9.1"
    }

    endpoints = [
        f"/get/live_upcoming_course_classv2?start=-1&courseid={course_id}",
        f"/get/course_contents_by_live_status?course_id={course_id}&start=-1&live_status=1,2"
    ]

    cached_ep = ENDPOINT_CACHE.get(course_id)

    if cached_ep:
        try:
            r = requests.get(api_base + cached_ep, headers=headers, timeout=10)
            if r.status_code == 200:
                j = r.json()
                if j.get("data") and j["data"].get("live"):
                    item = j["data"]["live"][0]
                    title = item.get("Title", "LIVE")
                    sid = item.get("recording_schedule")
                    if sid:
                        url = f"https://liveclasses.cloud-front.in/live/{sid}_480p.m3u8"
                        return title, sid, url
        except:
            pass

    for ep in endpoints:
        try:
            r = requests.get(api_base + ep, headers=headers, timeout=10)
            if r.status_code == 404:
                continue
            if r.status_code != 200:
                continue

            j = r.json()
            if j.get("data") and j["data"].get("live"):
                item = j["data"]["live"][0]
                title = item.get("Title", "LIVE")
                sid = item.get("recording_schedule")
                if not sid:
                    return None, None, None

                ENDPOINT_CACHE[course_id] = ep
                url = f"https://liveclasses.cloud-front.in/live/{sid}_480p.m3u8"
                return title, sid, url

        except Exception as e:
            print("LIVE FETCH ERROR:", e)

    return None, None, None


# ================= MULTI WATCHER LOOP =================

async def multi_watcher(pid, api, course_id, batch_name, upload_chat, thread_id, client, owner_chat):

    current_live = None
    live_file = None
    proc = None
    live_missing_count = 0
    last_title = None

    try:
        while True:

            try:
                title, sid, url = await asyncio.to_thread(fetch_live, api, course_id)
            except Exception as e:
                print(f"[PID {pid}] fetch_live error: {e}")
                await asyncio.sleep(30)
                continue

            # ✅ FIX 1: LIVE CHAL RAHA HAI — counter reset karo
            if sid and sid == current_live:
                live_missing_count = 0

            # 🔴 LIVE START — naya sid aaya
            elif sid and sid != current_live:

                live_missing_count = 0
                current_live = sid
                last_title = title

                safe_title = re.sub(r'[\\/*?:"<>|]', "", title or "LIVE").strip()
                live_file = os.path.abspath(f"{safe_title}_{pid}.mp4")

                await client.send_message(
                    upload_chat,
                    f"🔴 <b>LIVE STARTED</b>\n"
                    f"🆔 Process : {str(pid).zfill(3)}\n"
                    f"🎬 {title}\n"
                    f"⬇️ <i>Recording & Downloading Started...</i>",
                    message_thread_id=thread_id
                )

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-fflags", "+genpts",
                    "-i", url,
                    "-c", "copy",
                    "-bsf:a", "aac_adtstoasc",
                    "-movflags", "+faststart",
                    "-map", "0",
                    live_file
                ]

                proc = await asyncio.create_subprocess_exec(*cmd)

                if pid in ACTIVE_LIVES:
                    ACTIVE_LIVES[pid]["proc"] = proc

            # 🟢 LIVE END — sid nahi aaya
            if not sid and current_live:

                live_missing_count += 1

                if live_missing_count >= 3:

                    # ✅ FIX 2: proc properly terminate + wait
                    if proc:
                        try:
                            proc.terminate()
                            await asyncio.wait_for(proc.wait(), timeout=15)
                        except asyncio.TimeoutError:
                            proc.kill()
                            await proc.wait()
                        except Exception as e:
                            print(f"[PID {pid}] proc terminate error: {e}")
                        proc = None

                    # ✅ FIX 3: file flush hone do
                    await asyncio.sleep(3)

                    if live_file and os.path.exists(live_file):

                        caption = (
                            f"🎥 <b>Vid Id :</b> {str(pid).zfill(3)}\n"
                            f"<b>Video Title :</b> {last_title} [480p].mp4\n\n"
                            f"<blockquote>📚 Batch Name : {batch_name}</blockquote>\n\n"
                            f"<b>Extracted by ➤ 𝙂𝙃𝙊𝙎𝙏•𝙍𝙄𝙓</b>"
                        )

                        try:
                            # Fix video metadata
                            fixed_file = os.path.abspath(f"fixed_{pid}.mp4")

                            fix_result = subprocess.run(
                                f'ffmpeg -y -i "{live_file}" -c copy -map 0 -movflags +faststart "{fixed_file}"',
                                shell=True,
                                capture_output=True
                            )

                            if fix_result.returncode == 0 and os.path.exists(fixed_file):
                                os.remove(live_file)
                                live_file = fixed_file
                            else:
                                # ffmpeg fix fail hua, original file use karo
                                print(f"[PID {pid}] ffmpeg fix failed, using original")

                            # Duration nikalo
                            try:
                                duration = int(float(subprocess.check_output(
                                    f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{live_file}"',
                                    shell=True
                                ).decode().strip()))
                            except Exception:
                                duration = 0

                            # Thumbnail banao
                            thumb = os.path.abspath(f"live_thumb_{pid}.jpg")
                            subprocess.run(
                                f'ffmpeg -i "{live_file}" -ss 00:00:05 -vframes 1 -y "{thumb}"',
                                shell=True,
                                capture_output=True
                            )
                            thumb_path = thumb if os.path.exists(thumb) else None

                            await client.send_video(
                                upload_chat,
                                live_file,
                                caption=caption,
                                supports_streaming=True,
                                thumb=thumb_path,
                                duration=duration,
                                message_thread_id=thread_id
                            )

                            if thumb_path and os.path.exists(thumb_path):
                                os.remove(thumb_path)

                            if os.path.exists(live_file):
                                os.remove(live_file)

                        except Exception as upload_err:
                            # ✅ FIX 4: upload fail hone par owner ko batao
                            print(f"[PID {pid}] Upload error: {upload_err}")
                            await client.send_message(
                                owner_chat,
                                f"⚠️ <b>Process {pid} — Upload Failed</b>\n\n"
                                f"🎬 Title: {last_title}\n"
                                f"❌ Reason: <code>{str(upload_err)}</code>"
                            )

                    else:
                        # ✅ FIX 5: file nahi mili — owner ko batao
                        await client.send_message(
                            owner_chat,
                            f"⚠️ <b>Process {pid} — File Not Found</b>\n\n"
                            f"🎬 Title: {last_title}\n"
                            f"📁 Expected: <code>{live_file}</code>\n\n"
                            f"Live tha lekin recording file nahi bani."
                        )

                    current_live = None
                    live_file = None
                    live_missing_count = 0

            await asyncio.sleep(random.randint(25, 30))

    except asyncio.CancelledError:
        # Task cancel hone par proc bhi band karo
        if proc:
            try:
                proc.kill()
                await proc.wait()
            except:
                pass
        if live_file and os.path.exists(live_file):
            try:
                os.remove(live_file)
            except:
                pass

    finally:
        ACTIVE_LIVES.pop(pid, None)


# ================= ADD LIVE COMMAND =================

def setup_live(bot):

    @bot.on_message(filters.command("addlive") & auth_filter)
    async def add_live_multi(client, m: Message):

        global PROCESS_COUNTER

        await m.reply_text("🌐 Send API HOST")
        api = (await client.listen(m.chat.id)).text.strip()

        await m.reply_text("📚 Send COURSE ID")
        course_id = (await client.listen(m.chat.id)).text.strip()

        await m.reply_text("📚 Send Batch Name")
        batch_name = (await client.listen(m.chat.id)).text.strip()

        await m.reply_text(
            "📤 Send the CHAT ID where the video should be uploaded.\n\nSend /d to use the current chat."
        )

        chat_input = (await client.listen(m.chat.id)).text.strip()

        if chat_input == "/d":
            upload_chat = m.chat.id
            thread_id = None
        else:
            if "/" in chat_input:
                base, topic = chat_input.split("/")
                upload_chat = int(base)
                thread_id = int(topic)
            else:
                upload_chat = int(chat_input)
                thread_id = None

        PROCESS_COUNTER += 1
        pid = PROCESS_COUNTER

        await m.reply_text(f"✅ LIVE PROCESS STARTED\n🆔 Process ID : {pid}")

        task = asyncio.create_task(
            multi_watcher(
                pid,
                api,
                course_id,
                batch_name,
                upload_chat,
                thread_id,
                client,
                m.chat.id
            )
        )

        ACTIVE_LIVES[pid] = {
            "api": api,
            "course": course_id,
            "upload": upload_chat,
            "task": task,
            "proc": None
        }

    # ================= PROCESS LIST =================

    @bot.on_message(filters.command("process") & auth_filter)
    async def list_process(client, m: Message):

        if not ACTIVE_LIVES:
            return await m.reply_text("❌ No Active Live Processes")

        txt = "**🚀 ACTIVE LIVE PROCESSES**\n\n"

        for pid, data in ACTIVE_LIVES.items():
            txt += (
                f"🆔 Process ID : {pid}\n"
                f"🌐 API : {data['api']}\n"
                f"📚 Course_id : {data['course']}\n"
                f"📤 Upload Chat : {data['upload']}\n"
                f"──────────────\n"
            )

        await m.reply_text(txt)

    # ================= STOP SINGLE PROCESS =================

    @bot.on_message(filters.command("stoplive") & auth_filter)
    async def stop_live_process(client, m: Message):

        try:
            parts = m.text.split()

            if len(parts) != 2:
                return await m.reply_text("❌ Usage : /stoplive PROCESS_ID")

            pid = int(parts[1])

            if pid not in ACTIVE_LIVES:
                return await m.reply_text("❌ Process not found")

            task = ACTIVE_LIVES[pid]["task"]
            proc = ACTIVE_LIVES[pid].get("proc")

            task.cancel()

            if proc:
                try:
                    proc.kill()
                except:
                    pass

            ACTIVE_LIVES.pop(pid, None)
            await m.reply_text(f"🛑 LIVE PROCESS {pid} STOPPED")

        except Exception as e:
            await m.reply_text(f"❌ Error : {e}")

    # ================= STOP ALL PROCESS =================

    @bot.on_message(filters.command("killall") & auth_filter)
    async def stop_all_live(client, m: Message):

        if not ACTIVE_LIVES:
            return await m.reply_text("❌ No Active Processes")

        stopped = 0

        for pid, data in list(ACTIVE_LIVES.items()):
            try:
                if data.get("proc"):
                    data["proc"].kill()
                data["task"].cancel()
                ACTIVE_LIVES.pop(pid, None)
                stopped += 1
            except:
                pass

        await m.reply_text(f"🛑 ALL LIVE PROCESSES STOPPED\nTotal : {stopped}")


print("Bot Started...")
setup_live(bot)
bot.run()
