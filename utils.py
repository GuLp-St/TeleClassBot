import time
import imaplib
import re
import configparser
import os
import telebot
from telebot import types
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Lock

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
base_url = config['website']['base_url']

# Initialize Telegram bot
bot = telebot.TeleBot(config['telegram']['bot_token'])
webdriver_lock = Lock()  # Lock to synchronize access to the webdriver

# Load or create user accounts file
if not os.path.exists('user_accounts.ini'):
    with open('user_accounts.ini', 'w') as f:
        pass  # Create an empty file
user_accounts = configparser.ConfigParser()
user_accounts.read('user_accounts.ini')

# --- Preset teaching group URLs ---
preset_targets_scan = {
    "TMA3084 SoftLab": "https://qr.unimas.my/attendance/class/index.html#!/teaching_group/ug/111553",
    "PBM2072 BM": "https://qr.unimas.my/attendance/class/index.html#!/teaching_group/ug/112452",
    "TMF3113 ProjectManagement": "https://qr.unimas.my/attendance/class/index.html#!/teaching_group/ug/111469",
    "TMA3093 FormalMethod": "https://qr.unimas.my/attendance/class/index.html#!/teaching_group/ug/111573",
    "TMF3973 WebDev": "https://qr.unimas.my/attendance/class/index.html#!/teaching_group/ug/111482",
    "TMF3963 Ethics": "https://qr.unimas.my/attendance/class/index.html#!/teaching_group/ug/111570",
    "PBI1082 BI": "https://qr.unimas.my/attendance/class/index.html#!/teaching_group/ug/114293"
}

def get_main_markup():
    """Creates and returns the main markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_start = types.KeyboardButton('/start')
    btn_settings = types.KeyboardButton('/settings')  # Keep /settings
    btn_acc = types.KeyboardButton('/acc')  # New button for account management
    btn_search = types.KeyboardButton('/search')  # New button for searching
    btn_timetable = types.KeyboardButton('/timetable')
    btn_scheduling_scan = types.KeyboardButton('/scheduling_scan') # New button for scheduling scan
    btn_help = types.KeyboardButton('/help')
    markup.add(btn_start, btn_settings, btn_acc, btn_search, btn_timetable, btn_scheduling_scan, btn_help)
    return markup

def login_f2a(driver):
    driver.get(base_url.format(333333))

    # Locate username/email field
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(config['credentials']['username'])

    # Locate password field
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(config['credentials']['password'])

    # Sign in button
    sign_in_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "body > div.cont > div > div > form > button")))
    sign_in_button.click()

    # Locate "Sign in another way" button
    signin_another_way_span = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span[onclick='toggleAlt()']")))
    signin_another_way_span.click()

    # Another option button
    email_option = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "#alt-otp")))
    email_option.click()

    # Wait for 2FA and get the code from email
    time.sleep(5)
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(config['credentials']['email'], config['credentials']['email_password'])
    print("Login successful!")
    mail.select('INBOX')
    _, data = mail.search(None, '(FROM "identity@apps.unimas.my")')

    # Get the ID of the most recent email
    latest_email_id = data[0].split()[-1]

    _, message_data = mail.fetch(latest_email_id, '(RFC822)')
    raw_email = message_data[0][1]

    # Extract 2FA code
    match = re.search(r"Your verification code : (\d+)", raw_email.decode('utf-8'))
    if match:
        code = match.group(1)
        print(code)
    else:
        print("2FA code not found in email.")
        driver.quit()
        return None

    # Enter the 2FA code
    code_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#secret")))
    code_field.send_keys(code)

    # Submit the 2FA form
    submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnsubmit")))
    submit_button.click()

def get_cancel_markup():
    """Creates and returns the cancel markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    btn_cancel = types.KeyboardButton('/cancel')
    markup.add(btn_cancel)
    return markup