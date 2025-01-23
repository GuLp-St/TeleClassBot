import os
import configparser
from telebot import types

from utils import get_main_markup, bot, preset_targets_scan

# Load or create timetable file
if not os.path.exists('timetable.ini'):
    with open('timetable.ini', 'w') as f:
        pass  # Create an empty file
timetable = configparser.ConfigParser()
timetable.read('timetable.ini')

def get_timetable_markup():
    """Creates and returns the timetable markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_add_timetable = types.KeyboardButton('/add_timetable')
    btn_delete_timetable = types.KeyboardButton('/delete_timetable')
    btn_back_to_main = types.KeyboardButton('/main_menu')  # Button to go back to the main menu
    markup.add(btn_add_timetable, btn_delete_timetable, btn_back_to_main)
    return markup

def get_day_markup():
    """Creates and returns the day selection markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Monday'),
        types.KeyboardButton('Tuesday'),
        types.KeyboardButton('Wednesday'),
        types.KeyboardButton('Thursday'),
        types.KeyboardButton('Friday'),
        types.KeyboardButton('Cancel')  

    )
    return markup

def get_time_markup(start=8, end=20):
    """Creates and returns the time selection markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
    time_buttons = []
    for hour in range(start, end + 1):
        time_buttons.append(types.KeyboardButton(f"{hour:02d}00"))
    time_buttons.append(types.KeyboardButton('Cancel'))
    markup.add(*time_buttons)
    return markup

def get_course_markup():
    """Creates and returns the course selection markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # Add your preset courses here (from preset_targets_scan)
    for course in preset_targets_scan:
        markup.add(types.KeyboardButton(course))
    markup.add(types.KeyboardButton('Cancel'))
    return markup


def show_timetable(message):
    """Displays the user's current timetable."""
    user_id = message.chat.id
    if timetable.has_section(str(user_id)):
        timetable_str = "Your Timetable:\n"
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            if timetable.has_option(str(user_id), day):
                courses = timetable.get(str(user_id), day).split(',')
                timetable_str += f"\n**{day}:**\n"
                for course_time in courses:
                    try:
                        course, time_range = course_time.strip().split('|')  # Split using the pipe symbol
                        timetable_str += f"  - {course} ({time_range})\n"
                    except ValueError:
                        timetable_str += f"  - {course_time} (Invalid format)\n"
            else:
                timetable_str += f"\n**{day}:**\n  - No courses\n"
    else:
        timetable_str = "You haven't added any courses to your timetable yet."
    bot.reply_to(message, timetable_str, parse_mode='Markdown')

@bot.message_handler(commands=['main_menu'])
def main_menu_handler(message):
    """Handles the /main_menu command."""
    bot.reply_to(message, "Main menu:", reply_markup=get_main_markup())


@bot.message_handler(commands=['add_timetable'])
def add_timetable(message):
    """Starts the process of adding a course to the timetable."""
    show_timetable(message)
    msg = bot.send_message(message.chat.id, "Choose a day to add a course:", reply_markup=get_day_markup())
    bot.register_next_step_handler(msg, process_day_selection, "add")

def process_day_selection(message, action):
    """Processes the day selection and prompts for course selection."""
    user_id = message.chat.id
    day = message.text
    if day == "Cancel":
        bot.reply_to(message, "Action cancelled.", reply_markup=get_timetable_markup())
        return

    if action == "add":
        msg = bot.send_message(user_id, "Choose a course:", reply_markup=get_course_markup())
        bot.register_next_step_handler(msg, process_course_selection, day)
    elif action == "delete":
        if timetable.has_section(str(user_id)) and timetable.has_option(str(user_id), day):
            courses = timetable.get(str(user_id), day).split(',')
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            for course_time in courses:
                try:
                    course, time_range = course_time.strip().split('|')
                    markup.add(types.KeyboardButton(course))  # Use the course name with spaces
                except ValueError:
                    print(f"Invalid course_time format: {course_time}")
            markup.add(types.KeyboardButton('Cancel'))
            msg = bot.send_message(user_id, "Choose a course to delete:", reply_markup=markup)
            bot.register_next_step_handler(msg, process_course_deletion, day)
        else:
            bot.reply_to(message, "No courses found for this day.", reply_markup=get_timetable_markup())


def process_course_selection(message, day):
    """Processes the course selection and prompts for start time."""
    user_id = message.chat.id
    course = message.text
    if course == "Cancel":
        bot.reply_to(message, "Action cancelled.", reply_markup=get_timetable_markup())
        return

    msg = bot.send_message(user_id, "Choose the starting time (24-hour format):", reply_markup=get_time_markup())
    bot.register_next_step_handler(msg, process_start_time_selection, day, course)


def process_start_time_selection(message, day, course):
    """Processes the start time selection and prompts for end time."""
    user_id = message.chat.id
    start_time = message.text
    if start_time == "Cancel":
        bot.reply_to(message, "Action cancelled.", reply_markup=get_timetable_markup())
        return

    try:
        # Validate start_time
        int(start_time)
        if len(start_time) != 4 or not 800 <= int(start_time) <= 2000:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "Invalid time format. Please use HHMM (e.g., 0800 for 8 AM).", reply_markup=get_timetable_markup())
        return

    start_hour = int(start_time[:2])
    if start_hour < 18:
        start_hour += 1

    msg = bot.send_message(user_id, "Choose the ending time (24-hour format):", reply_markup=get_time_markup(start_hour, 20))
    bot.register_next_step_handler(msg, process_end_time_selection, day, course, start_time)


def process_end_time_selection(message, day, course, start_time):
    """Processes the end time selection and saves the course to the timetable."""
    user_id = message.chat.id
    end_time = message.text
    if end_time == "Cancel":
        bot.reply_to(message, "Action cancelled.", reply_markup=get_timetable_markup())
        return

    try:
        # Validate end_time
        int(end_time)
        if len(end_time) != 4 or not int(start_time) < int(end_time) <= 2000:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "Invalid time format or end time is earlier than start time. Please use HHMM (e.g., 1000 for 10 AM).", reply_markup=get_timetable_markup())
        return

    if not timetable.has_section(str(user_id)):
        timetable.add_section(str(user_id))

    course_time_str = f"{course}|{start_time}-{end_time}"  # Use pipe symbol as delimiter

    if timetable.has_option(str(user_id), day):
        timetable.set(str(user_id), day, timetable.get(str(user_id), day) + f", {course_time_str}")
    else:
        timetable.set(str(user_id), day, course_time_str)

    with open('timetable.ini', 'w') as f:
        timetable.write(f)

    bot.reply_to(message, f"Course added to your timetable for {day}!", reply_markup=get_timetable_markup())

@bot.message_handler(commands=['delete_timetable'])
def delete_timetable(message):
    """Starts the process of deleting a course from the timetable."""
    show_timetable(message)
    msg = bot.send_message(message.chat.id, "Choose a day to delete a course:", reply_markup=get_day_markup())
    bot.register_next_step_handler(msg, process_day_selection, "delete")

def process_course_deletion(message, day):
    """Processes the course deletion from the timetable."""
    user_id = message.chat.id
    course_to_delete = message.text  # This now contains the full course name with spaces
    if course_to_delete == "Cancel":
        bot.reply_to(message, "Action cancelled.", reply_markup=get_timetable_markup())
        return

    if timetable.has_section(str(user_id)) and timetable.has_option(str(user_id), day):
        courses = timetable.get(str(user_id), day).split(',')
        updated_courses = []
        for course_time in courses:
            try:
                course, time_range = course_time.strip().split('|')
                if course != course_to_delete:  # Compare with the full course name
                    updated_courses.append(course_time)
            except ValueError:
                print(f"Invalid course_time format: {course_time}")

        if len(updated_courses) == len(courses):
            bot.reply_to(message, "Course not found for this day.", reply_markup=get_timetable_markup())
            return

        if updated_courses:
            timetable.set(str(user_id), day, ", ".join(updated_courses))
        else:
            timetable.remove_option(str(user_id), day)

        with open('timetable.ini', 'w') as f:
            timetable.write(f)
        bot.reply_to(message, f"Course removed from your timetable for {day}!", reply_markup=get_timetable_markup())
    else:
        bot.reply_to(message, "No courses found for this day.", reply_markup=get_timetable_markup())
