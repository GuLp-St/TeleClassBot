from telebot import types

from utils import get_main_markup, bot
from auto_search import scan_qr_handler
from manual_search import find_text
from settings import settings_handler
from timetable import show_timetable, get_timetable_markup
from schedule_scan import scheduling_scan_handler, schedule_daily_schedule_notification
from account import account_handler, handle_account_callback,user_accounts
from lab_search import scan_lab_handler

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Use the get_main_markup function
    markup = get_main_markup()
    help_text = """
    Welcome!

    **Commands:**
    /start: See this message again.
    /settings: Show current settings.
    /search: Find your course.
    /acc: Manage your account.
    /timetable: Manage your timetable.
    /scheduling_scan: Coming soon.
    /help: Get a full detailed guide.
    """
    bot.reply_to(message, help_text, reply_markup=markup)

@bot.message_handler(commands=['help'])
def send_welcome(message):
    # Use the get_main_markup function
    markup = get_main_markup()
    help_text = """
    Welcome to the Unimas QR Attendance Bot!

    This bot helps you automate attendance tasks.

    🤖 **Key Features:**

    * **Automated Search (/search):**
        -* `/find`: Find courses by name or code.
        -* `/scan_qr`: Quickly scan QRs for 
        known courses.

    * **QR Code Scanning:**
        -* Extracts and displays QR codes.
        -* Optionally scans using Bluestacks.

    * **Account Management (/acc):**
        -* `/add_acc`: Save your UnimasNow 
        login.
        -* `/del_acc`: Remove saved accounts.

    * **Timetable (/timetable):**
        -* `/add_timetable`: Create a weekly 
        schedule.
        -* `/delete_timetable`: Edit your 
        schedule.
        -* *(Planned)* Scheduled scans based on 
        timetable.

    * **Settings (/settings):**
        -* `/number`: Change search start point.
        -* `/max`: Set max search attempts.

    * **Cancel Search (/cancel):** Stop an 
        ongoing search.


    🧭 **How to Use:**

    1. **Search for Courses:**
        -* Use `/search` and choose `/find` or 
         `/scan_qr`.
        -* `/find`: Select a preset course or type 
          the name/code.
        -* `/scan_qr`: Choose from preset 
          courses.
        -* The bot will log in and find the QR 
          code.
        -* Choose to scan the code when found.

    2. **Scan QR Codes:**
        -* Add your UnimasNow account with 
         `/add_acc`.
        -* When asked to scan, say "Yes" and 
          pick your account.
        -* The bot will scan the code for you.

    3. **Manage Timetable:**
        -* Use `/timetable` to see, add, or 
          remove courses.
        -* Follow the steps to choose day, 
          course, and time.


    ⚠️ **Important Notes:**

    * The bot refreshes every 300 searches to 
      avoid issues.


    ⌨️ **Commands:**

    * /start: Show this message.
    * /settings: Change bot settings.
    * /acc: Manage UnimasNow accounts.
    * /search: Find courses and QRs.
    * /timetable: Manage your schedule.
    * /help: Show this message again. 
    """
    bot.reply_to(message, help_text, reply_markup=markup, parse_mode='Markdown') 

@bot.message_handler(commands=['settings'])
def settings_handler_wrapper(message):
    settings_handler(message)

@bot.message_handler(commands=['acc'])
def account_handler_wrapper(message):
    account_handler(message, bot)  # Pass the bot instance

@bot.callback_query_handler(func=lambda call: call.data in ["add_acc", "del_acc"])
def handle_account_callback_wrapper(call):
    handle_account_callback(call, bot)  # Pass the bot instance

@bot.message_handler(commands=['search'])
def search_handler(message):
    """Handles the /search command."""
    # --- Create inline keyboard for search options ---
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Find Course (/find)", callback_data="find"),
        types.InlineKeyboardButton("Scan QR (/scan_qr)", callback_data="scan_qr"),
        types.InlineKeyboardButton("Scan lab (/scan_lab)", callback_data="scan_lab")
    )

    bot.reply_to(message, "Choose a search method:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["find", "scan_qr", "scan_lab"])
def handle_search_callback(call):
    """Handles callbacks from the /search inline keyboard."""
    if call.data == "find":
        find_text(call.message)  # Pass the message object to find_text

    elif call.data == "scan_qr":
        scan_qr_handler(call.message)  # Pass the message object to scan_qr_handler

    elif call.data == "scan_lab":
        scan_lab_handler(call.message) 


@bot.message_handler(commands=['timetable'])
def timetable_handler(message):
    """Handles the /timetable command."""
    show_timetable(message)
    bot.send_message(message.chat.id, "What do you want to do?", reply_markup=get_timetable_markup())

@bot.message_handler(commands=['scheduling_scan'])
def scheduling_scan_handler_wrapper(message):
    scheduling_scan_handler(message)

def send_main_markup_to_all_users():
    """Sends the get_main_markup  to all users in user_accounts.ini."""
    for user_id in user_accounts.sections():
        try:
            bot.send_message(user_id, ".", reply_markup=get_main_markup())
        except Exception as e:
            print(f"Error sending main markup to user {user_id}: {e}")

# Start the bot
#send_main_markup_to_all_users()
bot.polling()
#schedule_daily_schedule_notification()