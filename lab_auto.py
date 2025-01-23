import configparser
import time
import os
import re
import threading
from selenium import webdriver
from math import ceil
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from scan_qr import process_scan_qr_response
from utils import bot, get_main_markup

pdf_lock = threading.Lock()
cancel_process = {}

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
url_ci = config['lab']['url_ci']
url_co = config['lab']['url_co']
base_url = config['lab']['base_url']

def lab_test(current_number, user_id):
    # --- Create a directory for this user's downloads under the "pdf" folder ---
    main_pdf_dir = os.path.join(os.getcwd(), "pdf")
    os.makedirs(main_pdf_dir, exist_ok=True)  # Create the "pdf" folder if it doesn't exist
    download_dir = os.path.join(main_pdf_dir, f"attendance_pdfs_{user_id}")
    os.makedirs(download_dir, exist_ok=True)

    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "download.extensions_to_open": "applications/pdf"
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Re-initialize the WebDriver with the new options
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)

    try:
        driver.get(base_url.format(current_number))

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

    cancel_process[user_id] = False  # Initialize cancellation status for this user

    while True:
        try:
            download_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "body > app-root > div > div > activity-attendance > div.row.ng-scope > div.col-sm-3 > div > div.panel-body > div:nth-child(11) > button"))
            )

            download_button.click()
            time.sleep(2)

            names_exist = check_for_names_in_pdf(download_dir)  # Pass download_dir to check_for_names_in_pdf

            if names_exist:
                bot.send_message(user_id, "check in initiated")
                lab_scan_in(current_number, user_id)
                    # Keep checking for checkout times

                if check_for_CO_button(driver):
                    # Calculate the number of retries
                    max_retries = check_for_time_range(driver)
                    if max_retries is None:
                        bot.send_message(user_id, "Failed to determine time range, aborting.")
                        return None  # Or handle the error as appropriate
                    current_retry = 0

                    while current_retry < max_retries:
                        # Check if the process has been cancelled
                        if cancel_process[user_id]:
                            bot.send_message(user_id, "Check-in/out process cancelled.", reply_markup=get_main_markup())
                            driver.quit()
                            return None

                        # Re-download the attendance list
                        download_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "body > app-root > div > div > activity-attendance > div.row.ng-scope > div.col-sm-3 > div > div.panel-body > div:nth-child(11) > button"))
                        )
                        download_button.click()
                        time.sleep(2)  # Wait for the file to download

                        # Check for checkout times in the attendance list
                        checkouts_exist = check_for_checkouts_in_pdf(download_dir)  # Pass download_dir to check_for_checkouts_in_pdf

                        if checkouts_exist:
                            bot.send_message(user_id, "check out initiated.")
                            lab_scan_out(current_number, user_id)
                            return None
                        else:
                            current_retry += 1
                            # Wait 10 minutes before checking again
                            print("no checkout detected")
                            bot.send_message(user_id, "No checkout yet retrying in 10 minutes..")
                            time.sleep(600)
                            driver.refresh()

                    # Exceeded maximum retries
                    bot.send_message(user_id, "Failed to detect checkout within the time limit.")
                    return None

                else:
                    bot.send_message(user_id, "no checkout required for this lab, auto scan completed")
                    driver.quit()
                    return None
            else:
                # Check if the process has been cancelled
                if cancel_process[user_id]:
                    bot.send_message(user_id, "Check-in/out process cancelled.", reply_markup=get_main_markup())
                    driver.quit()
                    return None

                bot.send_message(user_id, "No names detected in the attendance list.")
                time.sleep(600)  # Wait 10 minutes before checking again
                driver.refresh()

        except Exception as e:
            print(f"Error in lab_test: {e}")
            bot.send_message(user_id, f"An error occurred: {e}")

def check_for_time_range(driver):
    try:
        # Wait for the time element to be present and extract its text
        time_element = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "body > app-root > div > div > activity-attendance > div.row.ng-scope > div.col-sm-3 > div > div.panel-body > h5:nth-child(6)")
            )
        )
        time_text = time_element.text
        print(time_text)
        # Extract the start and end times using regular expression
        match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)", time_text)
        if match:
            start_time, end_time = match.groups()

            # Convert times to minutes
            start_hour = int(start_time.split(':')[0])
            start_minute = int(start_time.split(':')[1][:2])
            if "PM" in start_time and start_hour != 12:
                start_hour += 12
            start_total_minutes = start_hour * 60 + start_minute

            end_hour = int(end_time.split(':')[0])
            end_minute = int(end_time.split(':')[1][:2])
            if "PM" in end_time and end_hour != 12:
                end_hour += 12
            end_total_minutes = end_hour * 60 + end_minute

            # Calculate the difference in minutes and divide by 10, rounding up
            total_minutes = end_total_minutes - start_total_minutes
            result = ceil(total_minutes / 10)
            return result

        else:
            print("Time range not found in the element text.")
            return None

    except Exception as e:
        print("CO not found")
        driver.quit()
        return False

def check_for_CO_button(driver):
    try:
        switch = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "body > app-root > div > div > activity-attendance > div.row.ng-scope > div.col-sm-9 > div > ul > li:nth-child(2) > a")
            )
        )
        switch.click()

        if WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "body > app-root > div > div > activity-attendance > div.row.ng-scope > div.col-sm-9 > div > div > div.tab-pane.ng-scope.active > div:nth-child(2) > div:nth-child(2) > div > button.btn.btn-danger.ng-scope")
            )
        ):
            print("CO detected")
            return True

    except Exception as e:
        print("CO not found")
        driver.quit()
        return False
    
# Helper function to check for names in the PDF
def check_for_names_in_pdf(download_dir):  # Add download_dir as argument
    pdf_file = os.path.join(download_dir, "qrAttendanceList.pdf")  # Use os.path.join to construct the path
    with pdf_lock:  # Acquire the lock before accessing the PDF
        try:

            import PyPDF2

            with open(pdf_file, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page = reader.pages[0]
                text = page.extract_text()

            # Split the text into lines
            lines = text.splitlines()

            # Check if there are at least two lines (excluding empty lines)
            non_empty_lines = [line for line in lines if line.strip()] 
            if len(non_empty_lines) >= 4:
                os.remove(pdf_file)
                return True
            else:
                os.remove(pdf_file)
                return False

        except PyPDF2.errors.PdfReadError:
            print(f"Error reading PDF file: {pdf_file}")
            os.remove(pdf_file)
            return False
        except FileNotFoundError:
            print(f"PDF file not found: {pdf_file}")
            os.remove(pdf_file)
            return False

# Helper function to check for checkout times in the PDF
def check_for_checkouts_in_pdf(download_dir):  # Add download_dir as argument
    pdf_file = os.path.join(download_dir, "qrAttendanceList.pdf")  # Use os.path.join to construct the path
    with pdf_lock:  # Acquire the lock before accessing the PDF
        try:
            import PyPDF2

            with open(pdf_file, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page = reader.pages[0]
                text = page.extract_text()

            # Split the text into lines
            lines = text.splitlines()

            # Check each line for two time strings and a name
            pattern = r"(\d{2}:\d{2}:\d{2}).*(\d{2}:\d{2}:\d{2}).*([A-Z]+\s[A-Z]+)"
            for line in lines:
                match = re.search(pattern, line)
                if match:
                    os.remove(pdf_file)
                    return True
                
            os.remove(pdf_file)
            return False  # No lines found with two time strings and a name

        except PyPDF2.errors.PdfReadError:
            print(f"Error reading PDF file: {pdf_file}")
            os.remove(pdf_file)
            return False
        except FileNotFoundError:
            print(f"PDF file not found: {pdf_file}")
            os.remove(pdf_file)
            return False

def lab_scan_in(number, user_id):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")

    # Initialize the WebDriver outside the loop
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(
        ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)

    try:
        driver.get(url_ci.format(90827))

        # Locate username/email field
        username_field = driver.find_element(By.ID, "username")
        username_field.send_keys(config['credentials']['username'])

        # Locate password field
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(config['credentials']['password'])

        # Sign in button
        sign_in_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.cont > div > div > form > button")))
        sign_in_button.click()

        driver.get(url_ci.format(90827))

        time.sleep(2)

        driver.get(url_ci.format(number))

        wait = WebDriverWait(driver, 10)
        alert = wait.until(EC.alert_is_present())

        alert_text = alert.text
        print(f"Alert text: {alert_text}")

        alert.accept()
        time.sleep(5)

        process_scan_qr_response(user_id, driver, lab = True)
        return

    except Exception as e:
        print(f"Error : {e}")
        driver.quit()
        return None

def lab_scan_out(number, user_id):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")

    # Initialize the WebDriver outside the loop
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(
        ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)

    try:
        driver.get(url_co.format(90827))

        # Locate username/email field
        username_field = driver.find_element(By.ID, "username")
        username_field.send_keys(config['credentials']['username'])

        # Locate password field
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(config['credentials']['password'])

        # Sign in button
        sign_in_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.cont > div > div > form > button")))
        sign_in_button.click()

        driver.get(url_co.format(90827))

        time.sleep(2)

        driver.get(url_co.format(number))

        wait = WebDriverWait(driver, 10)
        alert = wait.until(EC.alert_is_present())

        alert_text = alert.text
        print(f"Alert text: {alert_text}")

        alert.accept()
        time.sleep(5)

        process_scan_qr_response(user_id, driver, lab = True)
        return

    except Exception as e:
        print(f"Error : {e}")
        driver.quit()
        return None
    
@bot.message_handler(commands=['cancel'])
def cancel_lab_test(message):
    user_id = message.chat.id
    cancel_process[user_id] = True  # Signal the lab_test function to stop
    bot.reply_to(message, "Cancelling the check-in/out process...", reply_markup=get_main_markup())    