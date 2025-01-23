import configparser
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementNotInteractableException
from webdriver_manager.chrome import ChromeDriverManager
from telebot import types

from utils import get_main_markup, get_cancel_markup,bot
from settings import get_user_settings,update_user_settings
from lab_auto import lab_test

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
base_url = config['lab']['base_url']

start_number = int(config['lab']['start_number'])
max_attempts = int(config['lab']['max_attempts'])

cancel_search = {}

def check_for_text_and_location(driver, target_text, target_location, current_url):
    try:
        print(f"Checking for text and location at {current_url}")

        element = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body > app-root > div > div > activity-attendance > div.row.ng-scope > div.col-sm-3 > div > div.panel-body > h3 > b"))
        )
        # Extract the text
        text = element.text

        print(f"Extracted text: {text}")

        # 5. Process and compare the text
        processed_target_text = ''.join(target_text.lower().split())
        all_text = ''.join(e for e in text.lower() if e.isalnum())

        print(f"Processed extracted text: {all_text}")

        if processed_target_text in all_text:
            print("Text match found!")
            
            # Now check for location match
            try:
                location_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body > app-root > div > div > activity-attendance > div.row.ng-scope > div.col-sm-3 > div > div.panel-body > h5:nth-child(7)"))
                )
                location_text = location_element.text.lower()
                if target_location.lower() in location_text:
                    print("Location match found!")
                    return True
                else:
                    print(f"Location mismatch: Expected '{target_location}', found '{location_text}'")
                    return False
            except TimeoutException:
                print(f"Timeout occurred while waiting for location element at {current_url}")
                return False
            except Exception as e:
                print(f"Error finding or matching location at {current_url}: {e}")
                return False
        else:
            return False

    except TimeoutException:
        print(f"Timeout occurred while waiting for element or text at {current_url}")
        return False
    except (StaleElementReferenceException, ElementNotInteractableException) as e:
        print(f"Error interacting with element at {current_url}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking for text at {current_url}: {e}")
        return False

def perform_search(user_id, target_text, target_location):
    """
    Performs the search with user-specific settings, refreshing the browser every 300 searches.
    Includes initial login and 2FA, and re-login/2FA after refreshing.
    """
    settings = get_user_settings(user_id, 'lab')
    start_number = settings['start_number']
    max_attempts = settings['max_attempts']

    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    
    # Initialize the WebDriver outside the loop
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(
        ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)

    attempt = 0
    current_number = start_number
    found = False
    cancel_search[user_id] = False
    search_count = 0  # Counter for searches

    search_message = bot.send_message(user_id, f"Currently searching at {current_number}... (0/{max_attempts})", reply_markup=get_cancel_markup())

    # --- Initial Login and 2FA ---
    try:
        driver.get(base_url.format(90827))

        # Locate username/email field
        username_field = driver.find_element(By.ID, "username")
        username_field.send_keys(config['credentials']['username'])

        # Locate password field
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(config['credentials']['password'])

        # Sign in button
        sign_in_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.cont > div > div > form > button")))
        sign_in_button.click()

        driver.get(base_url.format(current_number))

        wait = WebDriverWait(driver, 10)
        alert = wait.until(EC.alert_is_present())

        alert_text = alert.text
        print(f"Alert text: {alert_text}")

        alert.accept()

    except Exception as e:
        print(f"Error during initial login/2FA: {e}")
        bot.send_message(user_id, f"An error occurred: {e}")
        driver.quit()
        return None
    # --- End of Initial Login and 2FA ---

    while attempt < max_attempts and not found and not cancel_search[user_id]:
        try:
            current_url = base_url.format(current_number)

            if attempt % 20 == 0:
                try:
                    bot.delete_message(chat_id=user_id, message_id=search_message.message_id)
                except Exception as e:
                    print(f"Error deleting message: {e}")

                search_message = bot.send_message(user_id, f"Currently searching at {current_number}... ({attempt}/{max_attempts})", reply_markup=get_cancel_markup())

            result = check_for_text_and_location(driver, target_text, target_location, current_url)

            if result is True:  # Text and location found
                # --- Update start number for the user ---
                update_user_settings(user_id, 'lab', new_start_number=current_number)
                print(f"Start number updated to: {current_number} for user {user_id}")
                found = True

                print(f"Text and location found at: {current_url}")
                ask_to_save_course(user_id, target_text, target_location, current_url) 

                # --- Load existing config or create a new one ---
                if not config.has_section(str(user_id)):
                    config.add_section(str(user_id))

                # --- Set the new target and number without overwriting ---
                config.set(str(user_id), 'target_lab', target_text)
                config.set(str(user_id), 'number_lab', str(current_number))

                # --- Save the updated config ---
                with open('config.ini', 'w') as configfile:
                    config.write(configfile)

                ask_to_start_lab_test(user_id, current_number)

                driver.quit()
                return current_url

            elif result is False:  # Incorrect match, timeout, or empty page
                print(f"Skipping {current_url} - No match found.")
                current_number += 1
                attempt += 1
                search_count += 1
                driver.get(base_url.format(current_number))
                wait = WebDriverWait(driver, 10)
                alert = wait.until(EC.alert_is_present())

                alert_text = alert.text
                alert.accept()

        except Exception as e:
            print(f"Error checking for text: {e}")
            bot.send_message(user_id, f"An error occurred: {e}")
            driver.quit()
            return None

    if found:
        update_user_settings(user_id, 'lab', new_start_number=current_number)
    else:
        if cancel_search[user_id]:
            bot.send_message(user_id, "Search cancelled.", reply_markup=get_main_markup())
        else:
            bot.send_message(user_id, "Text not found after maximum attempts.")

    driver.quit()
    return current_url if found else None

def ask_to_start_lab_test(user_id, current_number):
    """Asks the user if they want to start the lab test."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Yes", callback_data=f"start_lab_test:{current_number}"),
        types.InlineKeyboardButton("No", callback_data="no_start")
    )
    bot.send_message(user_id, "Do you want to auto check in/out?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('start_lab_test:', 'no_start')))
def callback_query(call):
    user_id = call.from_user.id
    data = call.data
    
    if data.startswith("start_lab_test:"):
        current_number = int(data.split(":")[1])
        bot.answer_callback_query(call.id, "Starting lab test...")
        
        # Edit the message to remove the keyboard
        bot.edit_message_text("Do you want to auto check in/out?", call.message.chat.id, call.message.message_id, reply_markup=None)  
        
        lab_test(current_number, user_id)

    elif data == "no_start":
        bot.answer_callback_query(call.id, "Lab test not started.")
        
        # Edit the message to remove the keyboard
        bot.edit_message_text("Do you want to auto check in/out?", call.message.chat.id, call.message.message_id, reply_markup=None)

def scan_lab_handler(message):
    user_id = message.chat.id
    settings = get_user_settings(user_id, 'lab')  # Get user settings
    start_number = settings['start_number']
    max_attempts = settings['max_attempts']

    # --- Get last search target from config.ini ---
    try:
        config.read('config.ini')  # Re-read the config file
        last_target = config.get(str(user_id), 'target_lab', fallback=None)
        last_number = config.get(str(user_id), 'number_lab', fallback=None)
        if last_target and last_number:
            last_search_msg = f"Latest Searches:\n{last_target} at {last_number}\n"
        else:
            last_search_msg = ""
    except Exception as e:
        print(f"Error reading last search target from config.ini: {e}")
        last_search_msg = ""

    # Show current settings in the message
    bot.reply_to(message, "Please enter your target text:")
    bot.send_message(user_id, f"{last_search_msg}\nCurrent Settings:\nSearch number - {start_number} \nMax attempt - {max_attempts}")
    # Get saved courses markup
    saved_courses_markup = get_saved_courses_markup(user_id)
    if saved_courses_markup:
        # Use send_message instead of reply_to
        sent_msg = bot.send_message(user_id, "Choose from your saved courses, or enter a new target text:", reply_markup=saved_courses_markup)  
        # Register a handler to catch both button presses and new text input
        bot.register_next_step_handler(sent_msg, handle_course_choice_or_new_target) 
    else:
        bot.reply_to(message, "Please enter your target text:")
        # --- Directly register the next step handler for the received message ---
        bot.register_next_step_handler(message, get_target_location)

def handle_course_choice_or_new_target(message):
    if message.text:  # User entered new text
        target_text = message.text
        bot.reply_to(message, "Please enter the target location:")
        bot.register_next_step_handler(message, lambda msg: start_search_thread(message, target_text, msg.text))
    else:  # User pressed a button (this will be handled by the callback_query handler)
        pass  # Do nothing here, as the callback_query handler will take care of it

def get_target_location(message):
    target_text = message.text
    bot.reply_to(message, "Please enter the target location:")
    bot.register_next_step_handler(message, lambda msg: start_search_thread(message, target_text, msg.text))

def start_search_thread(message, target_text=None, target_location=None):
    user_id = message.chat.id
    if target_text is None:
        target_text = message.text
    if target_location is None:
        target_location = message.text  # Assuming location is in the same message if not provided separately
    bot.send_message(user_id, "Logging In...", reply_markup=get_cancel_markup())
    thread = threading.Thread(target=perform_search, args=(user_id, target_text, target_location))
    thread.daemon = True
    thread.start()

@bot.message_handler(commands=['cancel'])
def cancel_search_handler(message):
    user_id = message.chat.id
    cancel_search[user_id] = True
    bot.reply_to(message, "Cancelling the search...", reply_markup=get_main_markup())

def save_course_info(user_id, target_text, target_location):
    """Saves the course information for the user."""
    try:
        config.read('config.ini')
        if not config.has_section(str(user_id)):
            config.add_section(str(user_id))
        # Use a unique key for each course (e.g., combine text and location)
        course_key = f"{target_text}-{target_location}" 
        config.set(str(user_id), course_key, f"{target_text}|{target_location}") 
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        print(f"Course info saved for user {user_id}: {target_text} - {target_location}")
        return True
    except Exception as e:
        print(f"Error saving course info: {e}")
        return False

def delete_course_info(user_id, course_key):
    """Deletes the saved course information."""
    try:
        config.read('config.ini')
        if config.has_section(str(user_id)) and config.has_option(str(user_id), course_key):
            config.remove_option(str(user_id), course_key)
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            print(f"Course info deleted for user {user_id}: {course_key}")
            return True
    except Exception as e:
        print(f"Error deleting course info: {e}")
    return False

def ask_to_save_course(user_id, target_text, target_location, current_url):
    """Asks the user if they want to save the course info."""
    keyboard = types.InlineKeyboardMarkup()
    course_key = f"{target_text}-{target_location}"  # Use the same key as in save_course_info
    keyboard.row(
        types.InlineKeyboardButton("Yes, save it", callback_data=f"save_course:{course_key}"),
        types.InlineKeyboardButton("No", callback_data="no_save")
    )
    bot.send_message(user_id, f"Text and location found at: {current_url}\nDo you want to save this course info for later use?", reply_markup=keyboard)
    bot.send_message(user_id, ".",reply_markup=get_main_markup())

def get_saved_courses_markup(user_id):
    """Creates an inline keyboard with saved courses for the user."""
    try:
        config.read('config.ini')
        if config.has_section(str(user_id)):
            keyboard = types.InlineKeyboardMarkup()
            for key, value in config.items(str(user_id)):
                if key not in ['target_lab', 'number_lab']:  # Exclude these keys
                    try:
                        text, location = value.split('|')
                        course_key = key  # The key is already unique
                        callback_data = f"use_course:{course_key}"
                        keyboard.add(types.InlineKeyboardButton(f"{text} - {location}", callback_data=callback_data))
                    except ValueError:
                        continue  # Skip this course and move to the next
            # Add a button to delete saved courses
            keyboard.add(types.InlineKeyboardButton("Delete saved courses", callback_data="delete_courses"))
            return keyboard
        else:
            return None
    except Exception as e:
        print(f"Error getting saved courses: {e}")
        return None

@bot.callback_query_handler(func=lambda call: call.data.startswith(('save_course:', 'no_save', 'use_course:', 'delete_courses')))
def callback_query(call):
    user_id = call.from_user.id
    data = call.data
    
    if data.startswith("save_course:"):
        course_key = data.split(":")[1]
        target_text, target_location = course_key.split("-")  # Extract text and location
        if save_course_info(user_id, target_text, target_location):
            bot.answer_callback_query(call.id, "Course info saved!")
            # Optionally, update the keyboard to reflect the saved course
            new_keyboard = get_saved_courses_markup(user_id)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_keyboard)
        else:
            bot.answer_callback_query(call.id, "Error saving course info.")

    elif data == "no_save":
        bot.answer_callback_query(call.id, "Not saved.")
        # Optionally, clear the keyboard
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    elif data.startswith("use_course:"):
        course_key = data.split(":")[1]
        target_text, target_location = course_key.split("-")  # Extract text and location
        bot.answer_callback_query(call.id, f"Using course: {target_text} - {target_location}")

        # Clear the previous message and keyboard to avoid waiting for user input
        bot.clear_step_handler_by_chat_id(chat_id=user_id) 
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)  

        # Start the search with the selected course
        start_search_thread(call.message, target_text, target_location)

    elif data == "delete_courses":
        # Get a list of course keys to delete
        course_keys_to_delete = [key for key, value in config.items(str(user_id)) if key not in ['target_lab', 'number_lab']]
        
        if course_keys_to_delete:
            for course_key in course_keys_to_delete:
                delete_course_info(user_id, course_key)
            bot.answer_callback_query(call.id, "All saved courses deleted!")
            # Update the keyboard to remove deleted courses
            new_keyboard = get_saved_courses_markup(user_id) 
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_keyboard)
        else:
            bot.answer_callback_query(call.id, "No saved courses to delete.")
