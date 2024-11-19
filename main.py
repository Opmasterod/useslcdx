import requests
import asyncio
from telegram import Bot
from flask import Flask
import time
import backoff
from threading import Thread
from datetime import datetime
import os
import sys
import subprocess

# Flask app for Koyeb deployment
app = Flask(__name__)

# Telegram Bot Information
BOT_TOKEN = '7193921126:AAFOJVvniqaxqFzePHfHlgK0I23Rwwx5sEw'
bot = Bot(token=BOT_TOKEN)

# API Information
API_TOKEN = '9fda05081d8fcb56acaa5999770d310835956881'

# Headers for API requests
headers = {
    'Accept': 'application/json',
    'origintype': 'web',
    'token': API_TOKEN,
    'usertype': '2',
    'Content-Type': 'application/x-www-form-urlencoded'
}

# Store already sent links to avoid duplicates
sent_links = set()

# API URLs
subject_url = "https://spec.iitschool.com/api/v1/batch-subject/{batch_id}"
live_url = "https://spec.iitschool.com/api/v1/batch-detail/{batchId}?subjectId={subjectId}&topicId=live"
class_detail_url = "https://spec.iitschool.com/api/v1/class-detail/{id}"

# Variables for monitoring
last_message_time = datetime.now()

# Function to get subject details
@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_subject_details(batchId):
    formatted_url = subject_url.format(batch_id=batchId)
    response = requests.get(formatted_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data["data"]["batch_subject"]
    else:
        print(f"Error getting subject details: {response.status_code}")
        return []

# Function to get live lecture links
@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_live_lecture_links(batchId, subjectId):
    formatted_url = live_url.format(batchId=batchId, subjectId=subjectId)
    response = requests.get(formatted_url, headers=headers)

    links = []
    if response.status_code == 200:
        data = response.json()
        classes = data["data"]["class_list"]["classes"]

        for lesson in classes:
            lesson_name = lesson["lessonName"]
            lesson_start_time = lesson["startDateTime"]
            lesson_id = lesson["id"]

            # Fetch class details for lessonUrl
            class_response = requests.get(class_detail_url.format(id=lesson_id), headers=headers)

            if class_response.status_code == 200:
                class_data = class_response.json()
                lesson_url = class_data["data"]["class_detail"]["lessonUrl"]

                if lesson_url and any(c.isalpha() for c in lesson_url):
                    youtube_link = f"https://www.youtube.com/watch?v={lesson_url}"

                    # Add formatted link if not already sent
                    if youtube_link not in sent_links:
                        links.append({
                            "link": youtube_link,
                            "start_time": lesson_start_time,
                            "lesson_name": lesson_name
                        })
                        sent_links.add(youtube_link)

    return links

async def send_telegram_message(chat_id, message):
    """Send a message to the configured Telegram chat."""
    global last_message_time
    last_message_time = datetime.now()  # Update last message time
    await bot.send_message(chat_id=chat_id, text=message)

async def check_for_new_links(batch_chat_pairs):
    """Check for new lecture links and send them if available, only between 6 AM and 8 PM."""
    while True:
        # Get the current time
        current_time = datetime.now().time()

        # Define the time range
        start_time = datetime.strptime("00:00", "%H:%M").time()
        end_time = datetime.strptime("23:00", "%H:%M").time()

        # Check if current time is within the desired range
        if start_time <= current_time <= end_time:
            for batchId, chatId in batch_chat_pairs:
                subjects = get_subject_details(batchId)
                links_found = False  # Flag to track if any links are found
                
                for subject in subjects:
                    subjectId = subject["id"]
                    subjectName = subject["subjectName"]  # Get subject name
                    new_links = get_live_lecture_links(batchId, subjectId)

                    if new_links:
                        links_found = True  # Set the flag to True if links are found
                        for link in new_links:
                            message = (f"☆☆𝗧𝗢𝗗𝗔𝗬 𝗟𝗜𝗩𝗘 𝗟𝗜𝗡𝗞𝗦★★\n\n"
                                       f"📚 𝐒𝐮𝐛𝐣𝐞𝐜𝐭 ✨: {subjectName}\n\n"  # Include subject name
                                       f"{link['lesson_name']}\n\n"
                                       f"❃.✮:▹ {link['start_time']} ◃:✮.❃\n\n"
                                       f"■ 𝐋𝐢𝐯𝐞 - {link['link']}\n\n"
                                       "◆𝐒𝐢𝐫,𝐈𝐟 𝐲𝐨𝐮 𝐰𝐚𝐧𝐭 𝐢 𝐫𝐞𝐦𝐨𝐯𝐞 𝐭𝐡𝐢𝐬 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 𝐨𝐫 𝐝𝐨𝐧'𝐭 𝐝𝐨 𝐭𝐡𝐢𝐬 𝐚𝐧𝐲𝐦𝐨𝐫𝐞 𝐜𝐨𝐧𝐭𝐚𝐜𝐭 𝐮𝐬 𝐩𝐥𝐞𝐚𝐬𝐞 - @RemoveIIT")
                            await send_telegram_message(chatId, message)

                if not links_found:  # If no links were found, send the "No lecture found" message
                    no_lecture_message = "NAHI AAYA LECTURE😖"
                    await send_telegram_message(chatId, no_lecture_message)
        else:
            print(f"Outside operating hours: {current_time}. Waiting for the next time window...")

        await asyncio.sleep(150)  # Check every 2 minutes

        # Monitor for inactivity and restart if necessary
        if (datetime.now() - last_message_time).total_seconds() > 600:
            print("No messages sent for 10 minutes. Restarting bot...")
            restart_bot()

def restart_bot():
    """Restart the bot by exiting and relaunching the script."""
    os.execv(sys.executable, ['python'] + sys.argv)

def auto_restart_thread():
    """Automatically restart the bot every 6 hours."""
    while True:
        time.sleep(21600)  # 6 hours
        print("6-hour auto-restart triggered.")
        restart_bot()

@app.route('/')
def index():
    return "Telegram Bot is running!"

# Main function to start the bot
if __name__ == "__main__":
    # Define multiple batch-chat pairs
    batch_chat_pairs = [
        (123, -1002388515011),  # Example: Batch ID and Chat ID
        (123, -1002261455163),
        # Add more batch-chat pairs as needed
    ]
    # Start monitoring thread for 6-hour auto-restart
    Thread(target=auto_restart_thread).start()
    # Start checking for new links in a separate thread
    Thread(target=lambda: asyncio.run(check_for_new_links(batch_chat_pairs))).start()
    # Start Flask app
    app.run(host='0.0.0.0', port=8080)
