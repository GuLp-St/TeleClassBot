import configparser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from telebot import types

from utils import get_main_markup, webdriver_lock, user_accounts

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
base_url = config['website']['base_url']

def account_handler(message, bot):  # Add bot as an argument
    """Handles the /acc command."""
    user_id = message.chat.id

    if user_accounts.has_section(str(user_id)):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Delete Account", callback_data="del_acc"))
        bot.reply_to(message, "You have an account saved. Do you want to delete it?", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Add Account", callback_data="add_acc"))
        bot.reply_to(message, "No account saved. Do you want to add one?", reply_markup=markup)

def handle_account_callback(call, bot):  # Add bot as an argument
    """Handles callbacks from the /acc inline keyboard."""
    user_id = call.message.chat.id
    if call.data == "add_acc":
        remove_markup = types.ReplyKeyboardRemove()
        bot.send_message(user_id, ".", reply_markup=remove_markup)
        msg = bot.send_message(user_id, "Please enter your account details in the format:\n\n`username password`\n\nExample:\n\n`82367 Unimas!024123822`")
        bot.register_next_step_handler(msg, lambda msg: process_add_account(msg, bot))  
    elif call.data == "del_acc":
        if user_accounts.has_section(str(user_id)):
            user_accounts.remove_section(str(user_id))
            with open('user_accounts.ini', 'w') as f:
                user_accounts.write(f)
            bot.reply_to(call.message, "Account deleted successfully!", reply_markup=get_main_markup())
        else:
            bot.reply_to(call.message, "You have no saved accounts.", reply_markup=get_main_markup())

def process_add_account(message, bot):  # Add bot as an argument
    user_id = message.chat.id
    try:
        bot.send_message(user_id, "checking credential validity...")
        username, password = message.text.split()
        if not verify_credentials(username, password):
            markup = get_main_markup()
            bot.reply_to(message, "Invalid credentials. Please try again.", reply_markup=markup)
            return
        if not user_accounts.has_section(str(user_id)):
            user_accounts.add_section(str(user_id))
        user_accounts.set(str(user_id), 'credentials', f"{username} {password}")
        with open('user_accounts.ini', 'w') as f:
            user_accounts.write(f)
        markup = get_main_markup()
        bot.send_message(user_id, "Account added successfully!", reply_markup=markup)
    except ValueError:
        markup = get_main_markup()
        bot.reply_to(message, "Invalid format. Please use `username password`.", reply_markup=markup)

def verify_credentials(username, password):
    """Verifies the given credentials by attempting a partial login."""

    chrome_options = Options()
    chrome_options.add_argument("--headless")

    with webdriver_lock:
        driver = webdriver.Chrome(service=webdriver.chrome.service.Service(
            ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)

    try:
        driver.get(base_url.format(333333))

        # Locate username/email field
        username_field = driver.find_element(By.ID, "username")
        username_field.send_keys(username)

        # Locate password field
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(password)

        # Sign in button
        sign_in_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "body > div.cont > div > div > form > button")))
        sign_in_button.click()

        # Check for the "Sign in another way" button (indicates valid credentials)
        try:
            WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span[onclick='toggleAlt()']")))
            return True  # Credentials are valid
        except TimeoutException:
            return False  # Credentials are invalid

    except Exception as e:
        print(f"Error during credential verification: {e}")
        return False
    finally:
        driver.quit()