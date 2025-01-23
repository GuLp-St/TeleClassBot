import base64
import subprocess
import threading
import os
import time
from io import BytesIO 
from queue import Queue
from threading import Thread
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils import bot, user_accounts, webdriver_lock, get_main_markup

qr_code_queue = Queue()  # Queue to manage QR code scan requests
queue_processing_thread = None  # Thread to handle processing the queue
qr_code_thread = None

def save_qr_code_image(driver, stop_event, lab=False):  # Added lab argument
    """Continuously saves QR code images from the driver."""
    qr_code_dir = "qr_codes"  # Store all QR codes in this directory
    os.makedirs(qr_code_dir, exist_ok=True)

    while not stop_event.is_set():
        try:
            if lab:
                # Extract QR code data for lab
                qr_code_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#qrcode img"))  # Select the <img> tag
                )
                qr_code_data = qr_code_element.get_attribute("src").split(",")[1]  # Extract base64 data from src
            else:
                # Extract QR code data for normal class
                qr_code_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#qrcode canvas"))
                )
                qr_code_data = driver.execute_script(
                    "return arguments[0].toDataURL('image/png').substring(22);",
                    qr_code_element
                )

            if qr_code_data:
                # Create an in-memory bytes buffer
                buffer = BytesIO()
                buffer.write(base64.b64decode(qr_code_data))
                buffer.seek(0)

                # Save the QR code image to the directory
                with open(f"{qr_code_dir}/qr_code.png", "wb") as f:
                    f.write(buffer.getvalue())
                print("QR code image saved.")
            else:
                print("QR code not found on the page.")

            time.sleep(1)  # Adjust the sleep time as needed

        except Exception as e:
            print(f"Error saving QR code image: {e}")
            # The loop will automatically retry after the sleep

def process_scan_qr_response(user_id, driver, lab=False):  # Added lab argument
    """Adds the QR code scan request to the queue."""
    global queue_processing_thread  # Declare qr_code_thread as global
    qr_code_queue.put((user_id, driver, lab))  # Add the request to the queue

    bot.send_message(user_id, "Your QR code scan request has been added to the queue.Please wait...")
    
    # Start the queue processing thread if it's not already running
    if queue_processing_thread is None:
        queue_processing_thread = Thread(target=process_queue)
        queue_processing_thread.daemon = True
        queue_processing_thread.start()


def process_queue():
    """Continuously processes QR code scan requests from the queue."""
    global qr_code_thread
    while True:
        user_id, driver, lab = qr_code_queue.get()  # Get the next request from the queue
        stop_event = threading.Event()
        try:
            # Directly get the username and password from user_accounts
            if user_accounts.has_section(str(user_id)):
                username, password = user_accounts.get(str(user_id), 'credentials').split()  # Use 'credentials' key

                try:
                    bot.send_message(user_id, "Scanning...")
                    # Start the QR code saving thread
                    qr_code_thread = Thread(target=save_qr_code_image, args=(driver, stop_event, lab))  # Pass lab argument
                    qr_code_thread.daemon = True
                    qr_code_thread.start()

                    # Call the BlueStacks script
                    subprocess.run([".venv/Scripts/python.exe", "blue.py", username, password, str(user_id)], check=True)

                except subprocess.CalledProcessError as e:
                    pass  # Handle the error appropriately (e.g., log it)

                finally:
                    # Stop the QR code saving thread
                    if qr_code_thread is not None:
                        stop_event.set()
                        qr_code_thread.join()
                        qr_code_thread = None
                        print("qr stopped")

                    with webdriver_lock:
                        driver.quit()
            else:
                bot.send_message(user_id, "Account not found.Add an account first bozo", reply_markup=get_main_markup())
                with webdriver_lock:
                    driver.quit()

        except Exception as e:
            print(f"Error processing QR code scan request: {e}")
            # Consider sending an error message to the user
        finally:
            qr_code_queue.task_done()  # Mark the task as done