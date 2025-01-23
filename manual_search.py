import configparser
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementNotInteractableException
from webdriver_manager.chrome import ChromeDriverManager

from utils import login_f2a, get_main_markup, get_cancel_markup,bot
from settings import get_user_settings, update_user_settings

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
base_url = config['website']['base_url']


start_number = int(config['website']['start_number'])
max_attempts = int(config['website']['max_attempts'])

cancel_search = {}

def check_for_text(driver, target_text, current_url, timeout=2):
    try:
        print(f"Checking for text at {current_url}")

        # 1. Wait for the parent <span> element to be present
        span_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body > div > div > code-qr > div.col-sm-12 > div:nth-child(1) > div:nth-child(2) > span"))
        )

        # 2. Wait for the text content to be non-empty using JavaScript
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script(
                "return document.querySelector('body > div > div > code-qr > div.col-sm-12 > div:nth-child(1) > div:nth-child(2) > span').textContent.trim() !== '';"
            )
        )

        # 3. Extract the text content from the <span>
        text_content = span_element.text
        print(f"Extracted text: {text_content}")

        # 5. Process and compare the text
        processed_target_text = ''.join(target_text.lower().split())
        all_text = ''.join(e for e in text_content.lower() if e.isalnum())
        print(f"Processed extracted text: {all_text}")

        if processed_target_text in all_text:
            print("Text match found!")
            return True
        else:
            return None

    except TimeoutException:
        print(f"Timeout occurred while waiting for element or text at {current_url}")
        return None
    except (StaleElementReferenceException, ElementNotInteractableException) as e:
        print(f"Error interacting with element at {current_url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error checking for text at {current_url}: {e}")
        return None

def perform_search(user_id, target_text):
    """
    Performs the search with user-specific settings, refreshing the browser every 300 searches.
    Includes initial login and 2FA, and re-login/2FA after refreshing.
    """
    settings = get_user_settings(user_id, 'class')
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
        login_f2a(driver)
        # Now you are logged in and can start the search
        driver.get(base_url.format(current_number))

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

            result = check_for_text(driver, target_text, current_url)

            if result is True:  # Text found
                print(f"Text found at: {current_url}")
                bot.send_message(user_id, f"Text found at: {current_url}")

                # --- Update start number for the user ---
                update_user_settings(user_id, 'class', new_start_number=current_number)
                print(f"Start number updated to: {current_number} for user {user_id}")
                found = True

                # --- Load existing config or create a new one ---
                if not config.has_section(str(user_id)):
                    config.add_section(str(user_id))

                # --- Set the new target and number without overwriting ---
                config.set(str(user_id), 'target', target_text)
                config.set(str(user_id), 'number', str(current_number))

                # --- Save the updated config ---
                with open('config.ini', 'w') as configfile:
                    config.write(configfile)

                return current_url

            elif result is False:  # Empty page found
                print(f"Skipping {current_url} - empty page.")
                current_number += 1
                attempt += 1
                search_count += 1
                driver.get(base_url.format(current_number))

            else:  # Incorrect match or timeout
                current_number += 1
                attempt += 1
                search_count += 1
                driver.get(base_url.format(current_number))

            # Refresh the browser every 300 searches
            if search_count >= 300:
                print("Refreshing the browser...")
                bot.send_message(user_id, "lemme rest a bit ya", reply_markup=get_cancel_markup())
                driver.quit()
                driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=chrome_options)
                driver.implicitly_wait(10)
                search_count = 0  # Reset the counter

                # --- Re-Login and 2FA ---
                try:
                    login_f2a(driver)
                    driver.get(base_url.format(current_number))  # Go back to the current URL
                except Exception as e:
                    print(f"Error during re-login/2FA: {e}")
                    bot.send_message(user_id, f"An error occurred: {e}")
                    driver.quit()
                    return None
                # --- End of Re-Login and 2FA ---
        except Exception as e:
            print(f"Error checking for text: {e}")
            bot.send_message(user_id, f"An error occurred: {e}")
            driver.quit()
            return None

    if found:
        update_user_settings(user_id, 'class', new_start_number=current_number)
    else:
        if cancel_search[user_id]:
            bot.send_message(user_id, "Search cancelled.", reply_markup=get_main_markup())
        else:
            bot.send_message(user_id, "Text not found after maximum attempts.")

    driver.quit()
    return current_url if found else None

def find_text(message):
    user_id = message.chat.id
    settings = get_user_settings(user_id, 'class')  # Get user settings
    start_number = settings['start_number']
    max_attempts = settings['max_attempts']

    # --- Get last search target from config.ini ---
    try:
        config.read('config.ini')  # Re-read the config file
        last_target = config.get(str(user_id), 'target', fallback=None)
        last_number = config.get(str(user_id), 'number', fallback=None)
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

    # --- Directly register the next step handler for the received message ---
    bot.register_next_step_handler(message, start_search_thread)

def start_search_thread(message, target_text=None):
    user_id = message.chat.id
    if target_text is None:
        target_text = message.text
    bot.send_message(user_id, "Logging In...", reply_markup=get_cancel_markup())
    thread = threading.Thread(target=perform_search, args=(user_id, target_text))
    thread.daemon = True
    thread.start()


@bot.message_handler(commands=['cancel'])
def cancel_search_handler(message):
    user_id = message.chat.id
    cancel_search[user_id] = True
    bot.reply_to(message, "Cancelling the search...", reply_markup=get_main_markup())