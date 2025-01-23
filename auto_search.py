import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from telebot import types

from utils import login_f2a, bot, webdriver_lock, get_main_markup, preset_targets_scan
from scan_qr import process_scan_qr_response

def perform_scan_qr(user_id, url, is_scheduled=False):
    """Performs the QR code number extraction."""

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Uncomment for headless mode

    with webdriver_lock:  # Assuming webdriver_lock is accessible here
        driver = webdriver.Chrome(service=webdriver.chrome.service.Service(
            ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)

    try:
        login_f2a(driver)

        qr_code_url = get_qr_numbers(driver, url)  # Get the QR code URL
        if qr_code_url:
            # --- Send the QR code URL to the user ---
            bot.send_message(user_id, f"QR code found: {qr_code_url}")  

            driver.get(qr_code_url)  # Open the QR code page
            time.sleep(2)
            # --- Extract the date ---
            try:
                extracted_date = get_qr_date(driver)
                current_date = datetime.datetime.now().strftime("%d %B")
                print(extracted_date, current_date)

                if extracted_date != current_date:  # Use direct comparison for exact match
                    if is_scheduled:
                        bot.send_message(user_id, f"QR code date ({extracted_date}) does not match the current date ({current_date}). Retrying in 10 minutes", reply_markup=get_main_markup())
                        #process_scan_qr_response(user_id, driver)
                        #return True
                        return False  # Return False if dates don't match for scheduled scans
                    else:
                        bot.send_message(user_id, f"QR code date ({extracted_date}) does not match the current date ({current_date}).Cuz the qr aint ready yet , try again next time bozo", reply_markup=get_main_markup())
                        #process_scan_qr_response(user_id, driver)
                        #return True
                        return  # Exit the function if dates don't match for non-scheduled scans

            except Exception as e:
                print(f"Error extracting date: {e}")
                extracted_date = "Unknown Date"  # Assign a value in the except block

            process_scan_qr_response(user_id, driver)
            return True
        else:
            bot.send_message(user_id, "No QR codes found or an error occurred.")

    except Exception as e:
        print(f"Error during scan_qr: {e}")
        bot.send_message(user_id, f"An error occurred: {e}")
    finally:
        # Don't quit the driver here, let process_scan_qr_response handle it
        pass  

def get_qr_numbers(driver, url):
    """Extracts QR numbers (simplified for testing)"""
    driver.get(url)
    try:
        # Wait for the table rows to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tbody > tr"))
        )

        # Find the element (simplified logic based on your working code)
        qr_link = driver.find_element(By.CSS_SELECTOR, "td:nth-child(6) > a:nth-child(1)")

        # If no error is raised up to this point, the element was found
        print("QR link element found successfully!")
        qr_href = qr_link.get_attribute("href")
        qr_number = qr_href.split("/")[-1] if qr_href else "Not Found"
        print(f"Example QR Number: {qr_number}") 

        # Construct the QR code URL
        qr_code_url = f"https://qr.unimas.my/attendance/class/fullpage.html#!/class/check/{qr_number}"
        return qr_code_url  # Return the QR code URL

    except Exception as e:
        print(f"Error extracting QR numbers: {e}")
        return None  # Return None in case of an error

def get_qr_date(driver):
    try:
        h5_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body > div > div > code-qr > div.col-sm-12 > div:nth-child(1) > div:nth-child(2) > h5"))
        )
        h5_text = h5_element.text.strip()
        lines = h5_text.splitlines()
        if len(lines) > 1:
            extracted_date_str = lines[1].strip()
            extracted_date = datetime.datetime.strptime(extracted_date_str.split(" ")[0] + " " + extracted_date_str.split(" ")[1] + " " + str(datetime.datetime.now().year), "%d %B %Y").strftime("%d %B")
            return extracted_date
        else:
            return "Unknown Date"
    except Exception as e:
        print(f"Error extracting date: {e}")
        return "Unknown Date"
    
def scan_qr_handler(message):
    user_id = message.chat.id
    remove_markup = types.ReplyKeyboardRemove()
    bot.send_message(user_id, ".", reply_markup=remove_markup)
    markup = types.InlineKeyboardMarkup(row_width=2)

    # Create buttons for preset targets using short callback data (course code)
    for target in preset_targets_scan: 
        markup.add(types.InlineKeyboardButton(target, callback_data=target)) 

    bot.reply_to(message, "Choose a course:", reply_markup=markup)    


@bot.callback_query_handler(func=lambda call: call.data in preset_targets_scan) 
def handle_scan_qr_button(call):
    user_id = call.message.chat.id
    course_code = call.data  # Get the course code directly
    url = preset_targets_scan.get(course_code)  # Get the URL from preset_targets_scan
    if url:
        bot.send_message(user_id, f"Selected course: {course_code}")  # Send the course code
        bot.send_message(user_id, "Logging in...")
        perform_scan_qr(user_id, url)  # Proceed with the login and extraction
    else:
        bot.send_message(user_id, "Invalid course selection.")    

