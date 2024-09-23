import requests
import asyncio
from telegram import Bot
from flask import Flask
import time
import backoff
from threading import Thread

# Flask app for Koyeb deployment
app = Flask(__name__)

# Telegram Bot Information
BOT_TOKEN = '7106709057:AAEDzg7JSl0lTC-Nc5kcyKen6gYWLiywMdM'
CHAT_ID = '-1002408234754'
bot = Bot(token=BOT_TOKEN)

# API Information
ACCOUNT_ID = "6415636611001"
API_TOKEN = 'd81fc5d9c79ec9002ede6c03cddee0a4730ab826'

headers = {
    'Accept': 'application/json',
    'origintype': 'web',
    'token': API_TOKEN,
    'usertype': '2',
    'Content-Type': 'application/x-www-form-urlencoded'
}

# URL templates
subject_url = "https://spec.iitschool.com/api/v1/batch-subject/{batch_id}"
live_url = "https://spec.iitschool.com/api/v1/batch-detail/{batchId}?subjectId={subjectId}&topicId=live"
class_detail_url = "https://spec.iitschool.com/api/v1/class-detail/{id}"

# Store already sent links
sent_links = set()

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_subject_details(batchId):
    """Retrieves subject details (id, subjectName) for a given batch."""
    formatted_url = subject_url.format(batch_id=batchId)
    response = requests.get(formatted_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data["data"]["batch_subject"]
    else:
        print(f"Error getting subject details: {response.status_code}")
        return []

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_live_lecture_links(batchId, subjectId):
    """Retrieves new lecture links for live lectures."""
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

async def send_telegram_message(message):
    """Send a message to the configured Telegram chat."""
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def check_for_new_links():
    """Check for new lecture links and send them if available."""
    batchId = '99'  # Replace with actual batch ID
    while True:
        subjects = get_subject_details(batchId)
        for subject in subjects:
            subjectId = subject["id"]
            new_links = get_live_lecture_links(batchId, subjectId)
            for link in new_links:
                message = f"☆☆𝗧𝗢𝗗𝗔𝗬 𝗟𝗜𝗩𝗘 𝗟𝗜𝗡𝗞𝗦★★\n\n{link['start_time']}**\n\n{link['lesson_name']}\n\n𝐋𝐢𝐯𝐞 - {link['link']}"
                await send_telegram_message(message)

        time.sleep(360)  # Check every minute

@app.route('/')
def index():
    return "Telegram Bot is running!"

if __name__ == "__main__":
    # Start checking for new links in a separate thread
    Thread(target=lambda: asyncio.run(check_for_new_links())).start()
    # Start Flask app
    app.run(host='0.0.0.0', port=8080)
