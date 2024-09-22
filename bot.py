import requests
import telebot
from datetime import datetime, timedelta
from threading import Thread, Timer
import config  # Import your config.py file

# API URLs
url = "https://spec.iitschool.com/api/v1/batch-subject/{batch_id}"
live_url = "https://spec.iitschool.com/api/v1/batch-detail/{batchId}?subjectId={subjectId}&topicId=live"

# Brightcove API
ACCOUNT_ID = "6415636611001"
BCOV_POLICY = "BCpkADawqM1474MvKwYlMRZNBPoqkJY-UWm7zE1U769d5r5kqTjG0v8L-THXuVZtdIQJpfMPB37L_VJQxTKeNeLO2Eac_yMywEgyV9GjFDQ2LTiT4FEiHhKAUvdbx9ku6fGnQKSMB8J5uIDd"
bc_url = f"https://edge.api.brightcove.com/playback/v1/accounts/{ACCOUNT_ID}/videos/"

# Default headers
headers = {
    'Accept': 'application/json',
    'origintype': 'web',
    'usertype': '2',
    'Content-Type': 'application/x-www-form-urlencoded'
}

# Function to get live lecture links
def get_live_lecture_links(batchId, subjectId, token):
    """Retrieves and prints the live lecture links for a given batch and subject."""
    url = live_url.format(batchId=batchId, subjectId=subjectId)

    headers['token'] = token  # Set token in headers

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        classes = data["data"]["class_list"]["classes"]

        live_links = []
        for lesson in classes:
            lesson_name = lesson["lessonName"]
            lesson_id = lesson["id"]
            lesson_url = lesson["lessonUrl"]

            # Check for alphabet in lesson_url (for YouTube links)
            if any(c.isalpha() for c in lesson_url):
                youtube_link = f"https://www.youtube.com/watch?v={lesson_url}"
                live_links.append(f"{lesson_name}:n{youtube_link}")

            # Get livestream token
            livestream_token_url = f"https://spec.iitschool.com/api/v1/livestreamToken?base=web&module=batch&type=brightcove&vid={lesson_id}"
            token_response = requests.get(livestream_token_url, headers=headers)

            if token_response.status_code == 200:
                token_data = token_response.json()
                brightcove_token = token_data["data"]["token"]

                # Construct the Brightcove video link
                brightcove_link = bc_url + str(lesson_url) + "/master.m3u8?bcov_auth=" + brightcove_token
                live_links.append(f"{lesson_name}: {brightcove_link}")        
        return live_links
    else:        
        return f"Request failed with status code {response.status_code}"

# Function to get subject details
def get_subject_details(batchId, token):
    """Retrieves subject details (id, subjectName) for a given batch."""
    url = "https://spec.iitschool.com/api/v1/batch-subject/{batch_id}".format(batch_id=batchId)

    headers['token'] = token  # Set token in headers

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        subjects = data["data"]["batch_subject"]
        subject_details = []
        for subject in subjects:
            subjectId = subject["id"]
            subjectName = subject["subjectName"]
            subject_details.append({"subjectId": subjectId, "subjectName": subjectName})
        return subject_details
    else:
        return f"Error getting subject details: {response.status_code}"

# Function to get the latest/upcoming lectures
def get_latest_lectures(batchId, token):
    """Retrieves and prints the live lecture links for a given batch and subject."""
    subject_details = get_subject_details(batchId, token)
    if subject_details:
        all_links = []
        for subject in subject_details:
            live_links = get_live_lecture_links(batchId, subject["subjectId"], token)
            if live_links:
                all_links.extend(live_links)  # Add all links for the subject
        return all_links
    else:
        return f"Error getting subject details: {response.status_code}"

# Function to check for new lectures and send them to the user
def check_for_new_lectures(chat_id, batchId, token):
    global previous_links
    latest_links = get_latest_lectures(batchId, token)

    if latest_links:
        new_links = [link for link in latest_links if link not in previous_links]
        if new_links:
            bot.send_message(chat_id, "New lectures added:")
            for link in new_links:
                bot.send_message(chat_id, link)
            previous_links = latest_links  # Update previous links with the latest
    
    # Schedule the next check
    Timer(60, check_for_new_lectures, [chat_id, batchId, token]).start()

# Initialize the bot
bot = telebot.TeleBot(config.BOT_TOKEN)  # Use the token from config.py

# Start the bot
@bot.message_handler(commands=['start'])
def send_welcome(message):
    global token, batchId, previous_links
    token = config.API_TOKEN  # Use the API token from config.py
    batchId = config.BATCH_ID  # Use the batch ID from config.py
    previous_links = []  # Initialize previous_links list
    
    # Start the lecture checking in a separate thread
    Thread(target=check_for_new_lectures, args=(message.chat.id, batchId, token)).start()

    bot.reply_to(message, "Welcome! I'm now checking for new lectures automatically.")

# Keep the bot running continuously
bot.polling(none_stop=True)
