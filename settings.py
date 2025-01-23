import threading
from telebot import types

from utils import config, bot, get_main_markup

config_lock = threading.Lock()
user_settings = {}  # Dictionary to store user-specific settings

def get_user_settings(user_id, search_type):
    """Gets or creates user-specific settings for the given search_type ('lab' or 'class')."""
    if user_id not in user_settings:
        user_settings[user_id] = {
            'lab': {
                'start_number': int(config['lab']['start_number']),
                'max_attempts': int(config['lab']['max_attempts'])
            },
            'class': {
                'start_number': int(config['website']['start_number']),
                'max_attempts': int(config['website']['max_attempts'])
            }
        }
    return user_settings[user_id][search_type]

def update_user_settings(user_id, search_type, new_start_number=None, new_max_attempts=None):
    """Updates user-specific settings and saves to config.ini with thread safety."""
    global config  # Declare config as global

    with config_lock:  # Acquire the lock before accessing config
        settings = get_user_settings(user_id, search_type)
        if new_start_number is not None:
            settings['start_number'] = new_start_number
            config[search_type if search_type == 'lab' else 'website']['start_number'] = str(new_start_number)

        if new_max_attempts is not None:
            settings['max_attempts'] = new_max_attempts
            config[search_type if search_type == 'lab' else 'website']['max_attempts'] = str(new_max_attempts)

        with open('config.ini', 'w') as configfile:
            config.write(configfile)

def settings_handler(message):
    """Handles the /settings command."""
    user_id = message.chat.id
    settings_lab = get_user_settings(user_id, 'lab')
    settings_class = get_user_settings(user_id, 'class')

    # --- Create inline keyboard for settings options ---
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Change Start Number (lab)", callback_data="number_lab"),
        types.InlineKeyboardButton("Change Max Attempts (lab)", callback_data="max_lab"),
        types.InlineKeyboardButton("Change Start Number (class)", callback_data="number"),
        types.InlineKeyboardButton("Change Max Attempts (class)", callback_data="max")
    )

    bot.reply_to(message, 
    f"Current Settings:\n"
    f"Lab - Start Number: {settings_lab['start_number']}\n"
    f"Lab - Max Attempts: {settings_lab['max_attempts']}\n"
    f"Class - Start Number: {settings_class['start_number']}\n"
    f"Class - Max Attempts: {settings_class['max_attempts']}", 
    reply_markup=markup)
    
@bot.callback_query_handler(func=lambda call: call.data in ["number", "max", "number_lab", "max_lab"])
def handle_settings_callback(call):
    """Handles callbacks from the /settings inline keyboard."""
    user_id = call.message.chat.id
    search_type = 'lab' if call.data in ["number_lab", "max_lab"] else 'class'
    if call.data.startswith("number"):
        # --- Logic for changing start number ---
        remove_markup = types.ReplyKeyboardRemove()
        bot.send_message(user_id, ".", reply_markup=remove_markup)
        msg = bot.send_message(user_id, "Please enter the new start number:")
        bot.register_next_step_handler(msg, lambda msg: process_new_start_number(msg, search_type))

    elif call.data.startswith("max"):
        # --- Logic for changing max attempts ---
        remove_markup = types.ReplyKeyboardRemove()
        bot.send_message(user_id, ".", reply_markup=remove_markup)
        msg = bot.send_message(user_id, "Please enter the new maximum number of attempts:")
        bot.register_next_step_handler(msg, lambda msg: process_new_max_attempts(msg, search_type))    

def process_new_start_number(message, search_type):
    user_id = message.chat.id
    try:
        new_start_number = int(message.text)
        update_user_settings(user_id, search_type, new_start_number=new_start_number)
        markup = get_main_markup()
        bot.send_message(user_id, f"Start number updated to: {new_start_number}", reply_markup=markup)

    except ValueError:
        bot.reply_to(message, "Invalid number. Please enter an integer.")

def process_new_max_attempts(message, search_type):
    user_id = message.chat.id
    try:
        new_max_attempts = int(message.text)

        # Warn the user if max_attempts is greater than 300
        if new_max_attempts > 300:
            bot.reply_to(message, "the bot will reset after every 300 searches due rate limit of the website,😊")

        update_user_settings(user_id, search_type, new_max_attempts=new_max_attempts)
        markup = get_main_markup()
        bot.send_message(user_id, f"Maximum number of attempts updated to: {new_max_attempts}", reply_markup=markup)
    except ValueError:
        bot.reply_to(message, "Invalid number. Please enter an integer.")