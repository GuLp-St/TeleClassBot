import telebot
import configparser
import subprocess
import os
import time
import psutil
from telebot import types

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Telegram bot token for the control bot
CONTROL_BOT_TOKEN = config['control']['bot_token']
CONFIRMATION_PASSWORD = config['control']['confirmation_password']  # Password for shutdown

bot = telebot.TeleBot(CONTROL_BOT_TOKEN)

# --- Helper functions ---

def get_main_markup():
    """Creates and returns the main markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_start = types.KeyboardButton('/start')
    btn_status = types.KeyboardButton('/status')
    btn_start_app = types.KeyboardButton('/start_app')
    btn_stop_app = types.KeyboardButton('/stop_app')
    btn_restart_app = types.KeyboardButton('/restart_app')
    btn_shutdown = types.KeyboardButton('/shutdown')
    btn_restart = types.KeyboardButton('/restart') 
    markup.add(btn_start, btn_status, btn_start_app, btn_stop_app, btn_restart_app, btn_shutdown, btn_restart)
    return markup

def is_app_running():
    """Checks if app.py is running."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == 'python.exe' and 'app.py' in proc.cmdline():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def start_app():
    """Starts app.py in a separate process."""
    subprocess.Popen(['python', 'app.py'])

def stop_app():
    """Stops app.py."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' and 'app.py' in proc.cmdline():
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Kill BlueStacks, Player, OBS, and Manager processes (suppressing potential errors)
    for proc_name in ["HD-Player.exe", "BlueStacks X.exe", "obs64.exe", "HD-MultiInstanceManager.exe"]:
        try:
            subprocess.run(["taskkill", "/f", "/im", proc_name], check=True)
        except subprocess.CalledProcessError:
            pass

def restart_app():
    """Restarts app.py."""
    stop_app()
    time.sleep(2)
    start_app()

def shutdown_pc():
    """Shuts down the PC."""
    os.system("shutdown /s /t 1")

def restart_pc():
    """Restarts the PC."""
    os.system("shutdown /r /t 1")

# --- Bot commands ---

@bot.message_handler(commands=['start'])
def send_help(message):
    help_text = """
    Available commands:
    /start - Start the control bot
    /status - Check the status of app.py
    /start_app - Start app.py
    /stop_app - Stop app.py
    /restart_app - Restart app.py
    /shutdown - Shutdown the PC
    /restart - Restart the PC 
    """
    bot.reply_to(message, help_text, reply_markup=get_main_markup())

@bot.message_handler(commands=['status'])
def check_status(message):
    if is_app_running():
        bot.reply_to(message, "app.py is running.", reply_markup=get_main_markup())
    else:
        bot.reply_to(message, "app.py is not running.", reply_markup=get_main_markup())

@bot.message_handler(commands=['start_app'])
def start_app_handler(message):
    if not is_app_running():
        start_app()
        bot.reply_to(message, "app.py started.", reply_markup=get_main_markup())
    else:
        bot.reply_to(message, "app.py is already running.", reply_markup=get_main_markup())

@bot.message_handler(commands=['stop_app'])
def stop_app_handler(message):
    if is_app_running():
        stop_app()
        bot.reply_to(message, "app.py stopped.", reply_markup=get_main_markup())
    else:
        bot.reply_to(message, "app.py is not running.", reply_markup=get_main_markup())

@bot.message_handler(commands=['restart_app'])
def restart_app_handler(message):
    restart_app()
    bot.reply_to(message, "app.py restarted.", reply_markup=get_main_markup())

@bot.message_handler(commands=['shutdown'])
def shutdown_handler(message):
    msg = bot.reply_to(message, "Enter confirmation password to shutdown the PC:")
    bot.register_next_step_handler(msg, confirm_shutdown)

@bot.message_handler(commands=['restart'])
def restart_handler(message):
    msg = bot.reply_to(message, "Enter confirmation password to restart the PC:")
    bot.register_next_step_handler(msg, confirm_restart)

def confirm_shutdown(message):
    if message.text == CONFIRMATION_PASSWORD:
        bot.reply_to(message, "Shutting down the PC...")
        shutdown_pc()
    else:
        bot.reply_to(message, "Incorrect password. Shutdown cancelled.", reply_markup=get_main_markup())

def confirm_restart(message):
    if message.text == CONFIRMATION_PASSWORD:
        bot.reply_to(message, "Restarting the PC...")
        restart_pc()
    else:
        bot.reply_to(message, "Incorrect password. Shutdown cancelled.", reply_markup=get_main_markup())
# Start the control bot
bot.polling()
