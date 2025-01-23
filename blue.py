import subprocess
import time
import pyautogui
import sys
import os
import telebot
import configparser
import json
import re

# --- Configuration ---
image_folder = "images"
metadata_file = r"C:\ProgramData\BlueStacks_nxt\Engine\UserData\MimMetaData.json"

# Load configuration for Telegram bot token
config = configparser.ConfigParser()
config.read('config.ini')  # Make sure this points to your config.ini file
bot_token = config['telegram']['bot_token']
bot = telebot.TeleBot(bot_token)

if len(sys.argv) == 4:  # Added user_id argument
    username = sys.argv[1]
    password = sys.argv[2]
    user_id = sys.argv[3]  # Get user_id from arguments
    print(f"Received credentials: {username}, {password}")
    print(f"User ID: {user_id}")
else:
    # --- If no arguments, get them from user input ---
    print("No arguments provided. Please enter the following:")
    username = input("Username: ")
    password = input("Password: ")
    current_url = input("URL: ")
    user_id = input("User ID: ")
# -------------------

def send_message_to_telegram(user_id, message, screenshot_path=None):
    """Sends the message and optional screenshot to the Telegram user."""
    try:
        markup = get_main_markup()
        bot.send_message(user_id, message, reply_markup=markup)
        if screenshot_path:
            bot.send_photo(user_id, photo=open(screenshot_path, 'rb'))
        print(f"Message sent to Telegram: {message}")
    except Exception as e:
        print(f"Error sending message or screenshot to Telegram: {e}")

def get_app_name_and_instance(username):
    """
    Retrieves the app name and instance name from MimMetaData.json.
    The app name is determined by extracting the number from the InstanceName.
    """
    try:
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        for org in data['Organization']:
            if org['Name'] == f"BlueStacks App Player {username}":
                instance_name = org['InstanceName']  # Get the full InstanceName
                match = re.search(r'_(\d+)$', instance_name)  # Extract the number
                if match:
                    app_number = match.group(1)  # Get the extracted number
                    app_name = f"BlueStacks App Player {app_number}"
                    return app_name, instance_name
                else:
                    print(f"Error: Could not extract number from InstanceName: {instance_name}")
                    return None, None  # Or handle the error as needed
    except FileNotFoundError:
        print(f"Error: {metadata_file} not found.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {metadata_file}.")
    except KeyError:
        print(f"Error: 'Organization' key not found in {metadata_file}.")
    return None, None        
        
def get_main_markup():
    """Creates and returns the main markup for the bot."""
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_start = telebot.types.KeyboardButton('/start')
    btn_settings = telebot.types.KeyboardButton('/settings')  # Keep /settings
    btn_acc = telebot.types.KeyboardButton('/acc')  # New button for account management
    btn_search = telebot.types.KeyboardButton('/search')  # New button for searching
    btn_timetable = telebot.types.KeyboardButton('/timetable')
    btn_scheduling_scan = telebot.types.KeyboardButton('/scheduling_scan')
    btn_help = telebot.types.KeyboardButton('/help')
    markup.add(btn_start, btn_settings, btn_acc, btn_search, btn_timetable, btn_scheduling_scan, btn_help)
    return markup

def take_screenshot_of_area(x, y, width, height, screenshot_path):
    """Takes a screenshot of a specific area and saves it."""
    try:
        pyautogui.screenshot(screenshot_path, region=(x, y, width, height))
        print(f"Screenshot of area taken and saved to {screenshot_path}")
    except Exception as e:
        print(f"Error taking screenshot of area: {e}")

def take_screenshot_of_app(app_name, screenshot_path):
    """
    Takes a screenshot of the specified application window.
    """
    try:
        # Use pyautogui.getWindowsWithTitle() to get the window
        app_window = pyautogui.getWindowsWithTitle(app_name)[0] 
        
        # Activate the window and bring it to the front
        app_window.activate()
        
        # Get window coordinates and dimensions
        x, y, width, height = app_window.left, app_window.top, app_window.width, app_window.height

        # Take the screenshot
        pyautogui.screenshot(screenshot_path, region=(x, y, width, height))
        print(f"Screenshot of app taken and saved to {screenshot_path}")

    except IndexError:
        print(f"Error: Application window '{app_name}' not found.")
    except Exception as e:
        print(f"Error taking screenshot of app: {e}")        
        
def remove_choose_menu():
    """Removes the choose account menu by sending a message with ReplyKeyboardRemove."""
    try:
        remove_markup = telebot.types.ReplyKeyboardRemove()
        bot.send_message(user_id, ".", reply_markup=remove_markup)
        print("Choose account menu removed.")
    except Exception as e:
        print(f"Error removing choose account menu: {e}")        

def launch_obs():
    """
    Launches OBS Studio with the specified command-line options, 
    including starting the virtual camera.
    """
    obs_path = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"  # Replace with your OBS path
    obs_dir = os.path.dirname(obs_path)

    try:
        # Construct the command with options
        command = f'cd /d "{obs_dir}" && start "" "{obs_path}" --disable-shutdown-check --startreplaybuffer --startvirtualcam' 

        # Execute the command
        subprocess.Popen(command, shell=True)

        print("Launching OBS Studio with options...")
        time.sleep(1)  # Give OBS some time to start

    except Exception as e:
        print(f"Error launching OBS Studio: {e}")

def launch_app():
    """Launches the app using the command line."""
    command = r'"C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance Pie64 --cmd launchAppWithBsx --package "my.unimas.earlyedition" --source desktop_shortcut'
    subprocess.Popen(command)
    print(f"Launching app: {app_name}")

def find_image(image_name, timeout=5):
    """Repeatedly searches for an image in the subfolder until it's found or timeout."""
    image_path = os.path.join(image_folder, image_name)  # Construct the full path
    print(f"Searching for image: {image_path}")
    start_time = time.time()
    location = None
    while location is None and time.time() - start_time < timeout:
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
            if location:
                print(f"Found image: {image_path}")
                return location
            else:
                print(f"Image not found yet: {image_path}")
        except (TypeError, pyautogui.ImageNotFoundException):
            print(f"Image not found yet: {image_path}")
            pass
        time.sleep(1)

    # If the loop completes without finding the image, raise an exception
    if location is None:
        raise TimeoutError(f"Scanned Qr or Outdated Qr")

def is_app_loaded():
    """Checks if the app is fully loaded."""
    time.sleep(10)
    return find_image('loaded.png', timeout=20) is not None

def is_app_loaded2():
    """Checks if the app is fully loaded."""
    time.sleep(10)
    return find_image('loaded2.png', timeout=20) is not None

def login2():
    try:

        # locate and click the qr button
        qr_button = find_image('qr.png')
        pyautogui.click(qr_button)
        print("Clicked qr button")

        # Locate check_in image with a 10-second timeout
        check_in_image = find_image('check_in.png', timeout=10)
        if check_in_image:
            screenshot_path = os.path.join(image_folder, "app_screenshot.png")
            take_screenshot_of_app(app_name, screenshot_path) 
            send_message_to_telegram(user_id, "Qr Scanned Sucessfully", screenshot_path)

            # If found, click on the home image
            home_image = find_image('home.png')
            pyautogui.click(home_image)
            print("Clicked home image")
            
            kill_player()
            kill_obs()
            
    except TimeoutError as e:
        print(e) 
        screenshot_path = os.path.join(image_folder, "app_screenshot.png")
        take_screenshot_of_app(app_name, screenshot_path) 
        send_message_to_telegram(user_id, "Outdated or Scanned Qr", screenshot_path)
        
        time.sleep(1)  

        kill_player()
        kill_obs()

def login():
    """Navigates through the login sequence."""
    try:
        # Define the login steps as a list of functions
        login_steps = [
            lambda: pyautogui.click(find_image('okay.png')),  # Click okay button
            lambda: pyautogui.click(find_image('allow.png')),  # Click allow button
            lambda: time.sleep(1),
            lambda: pyautogui.click(find_image('username_field.png')), 
            lambda: pyautogui.write(username),
            lambda: pyautogui.click(find_image('password_field.png')),
            lambda: pyautogui.write(password),
            lambda: pyautogui.click(find_image('login_button.png')),  # Click login button
            lambda: time.sleep(1),
            lambda: pyautogui.click(find_image('ok.png')),  # Click ok button
            lambda: pyautogui.click(find_image('ok.png')),  # Click ok button
            lambda: pyautogui.click(find_image('qr.png')),  # Click qr button
            lambda: pyautogui.click(find_image('allow.png')),  # Click allow button
            lambda: time.sleep(0.5),
            lambda: pyautogui.click(find_image('switch.png'))  # Click switch button
        ]

        # Iterate through the login steps with retry mechanism
        current_step = 0
        while current_step < len(login_steps):
            try:
                login_steps[current_step]()  # Execute the current step
                print(f"Completed step {current_step + 1}")
                current_step += 1  # Move to the next step
            except TimeoutError:
                print(f"TimeoutError on step {current_step + 1}. Retrying previous step...")
                if current_step > 0:  # Avoid going back from the first step
                    current_step -= 1
                time.sleep(1)

        # Locate check_in image with a 10-second timeout
        check_in_image = find_image('check_in.png', timeout=10)
        if check_in_image:
            screenshot_path = os.path.join(image_folder, "app_screenshot.png")
            take_screenshot_of_app(app_name, screenshot_path) 
            send_message_to_telegram(user_id, "Qr Scanned Sucessfully", screenshot_path)

            # If found, click on the home image
            home_image = find_image('home.png')
            pyautogui.click(home_image)
            print("Clicked home image")

            kill_player()
            kill_obs()
            kill_manager()
            
    except TimeoutError as e:
        print(e) 
        screenshot_path = os.path.join(image_folder, "app_screenshot.png")
        take_screenshot_of_app(app_name, screenshot_path) 
        send_message_to_telegram(user_id, "Outdated or Scanned Qr", screenshot_path)
        
        time.sleep(1)  

        kill_player()
        kill_obs()
        kill_manager()
    
    
def kill_player():
    """Kills all BlueStacks processes."""
    try:
        subprocess.run(["taskkill", "/f", "/im", "HD-Player.exe"], check=True)
        print("player processes killed.")
    except subprocess.CalledProcessError as e:
        print(f"Error killing player processes: {e}")
        
        
def kill_bluestacks():
    """Kills all BlueStacks processes."""
    try:
        subprocess.run(["taskkill", "/f", "/im", "BlueStacks X.exe"], check=True)
        print("BlueStacks processes killed.")
    except subprocess.CalledProcessError as e:
        print(f"Error killing BlueStacks processes: {e}")

def kill_obs():
    """Kills all obs processes."""
    try:
        subprocess.run(["taskkill", "/f", "/im", "obs64.exe"], check=True)
        print("Obs processes killed.")
    except subprocess.CalledProcessError as e:
        print(f"Error killing Obs processes: {e}")    


def kill_manager():
    """Kills all manager processes."""
    try:
        subprocess.run(["taskkill", "/f", "/im", "HD-MultiInstanceManager.exe"], check=True)
        print("manager processes killed.")
    except subprocess.CalledProcessError as e:
        print(f"Error killing manager processes: {e}") 

def get_instance_name(username):
    """Retrieves the instance name associated with the username from MimMetaData.json."""
    try:
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        for org in data['Organization']:
            if org['Name'] == f"BlueStacks App Player {username}":
                return org['InstanceName']
    except FileNotFoundError:
        print(f"Error: {metadata_file} not found.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {metadata_file}.")
    except KeyError:
        print(f"Error: 'Organization' key not found in {metadata_file}.")
    return None

def create_new_instance(username):
    """Creates a new BlueStacks instance using the instance manager."""
    try:
        # Launch the instance manager
        instance_manager_path = r"C:\Program Files\BlueStacks_nxt\HD-MultiInstanceManager.exe"
        subprocess.Popen(instance_manager_path)
        print("Launching BlueStacks Instance Manager...")
        time.sleep(1)  # Give the manager time to start

        # Locate and click the create button
        create_button = find_image('create.png')
        pyautogui.click(create_button)
        print("Clicked create button")

        # Locate and click the clone button
        clone_button = find_image('clone.png')
        pyautogui.click(clone_button)
        print("Clicked clone button")

        # Locate and click the new button
        new_button = find_image('new.png')
        pyautogui.click(new_button)
        print("Clicked new button")

        # Get the initial number of instances
        with open(metadata_file, 'r') as f:
            initial_data = json.load(f)
        initial_count = len(initial_data['Organization'])

        # Wait for a new instance to be added to MimMetaData.json
        while True:
            with open(metadata_file, 'r') as f:
                new_data = json.load(f)
            new_count = len(new_data['Organization'])
            if new_count > initial_count:
                rename_instance(new_data, username)  # Rename the new instance
                break
            time.sleep(1)

    except Exception as e:
        print(f"Error creating new instance: {e}")
        send_message_to_telegram(user_id, f"Error creating new instance: {e}")

def rename_instance(data, username):
    """Renames the newly created instance in the provided data."""
    try:
        # Assuming the newly added instance is the last one
        new_instance = data['Organization'][-1]  
        new_instance['Name'] = f"BlueStacks App Player {username}"

        with open(metadata_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Instance renamed to: BlueStacks App Player {username}")
    except Exception as e:
        print(f"Error renaming instance: {e}")
        send_message_to_telegram(user_id, f"Error renaming instance: {e}")

def launch_app(instance_name="Pie64"): 
    """Launches the app using the command line with the given instance name."""
    command = fr'"C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance {instance_name} --cmd launchAppWithBsx --package "my.unimas.earlyedition" --source desktop_shortcut'
    subprocess.Popen(command)
    print(f"Launching app: {app_name} on instance {instance_name}")

if __name__ == "__main__":
    launch_obs()

    app_name, instance_name = get_app_name_and_instance(username)
    if instance_name and app_name:
        launch_app(instance_name)
            # Wait for the app to load
        if is_app_loaded2():
            print("App is loaded.")
            kill_bluestacks() 
            login2()
        else:
            print("App loading timed out.")
    else:
        send_message_to_telegram(user_id, "No previous attempt detected, please wait...")
        create_new_instance(username)
        instance_name = get_instance_name(username)  # Get the new instance name
        launch_app(instance_name)  # Launch the app in the new instance
            # Wait for the app to load
        if is_app_loaded():
            print("App is loaded.")
            kill_bluestacks() 
            login()
        else:
            print("App loading timed out.")