import time
import threading
import datetime

from utils import get_main_markup, bot, preset_targets_scan, user_accounts
from auto_search import perform_scan_qr
from settings import user_settings
from timetable import timetable

scheduling_scan_enabled = {}  # Dictionary to store scheduling status for each user
schedule_timers = {}  # Dictionary to store timers for scheduled scans

def schedule_scan(user_id, course, time_range):
    """Schedules a QR code scan for the given course and time range."""
    try:
        start_time_str = time_range.split('-')[0]
        start_hour = int(start_time_str[:2])
        start_minute = int(start_time_str[2:])
        end_time_str = time_range.split('-')[1]  # Get the end time
        end_hour = int(end_time_str[:2])
        end_minute = int(end_time_str[2:])

        now = datetime.datetime.now()
        start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        end_time = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)  # Calculate end_time

        time_difference = (start_time - now).total_seconds()

        # Check if the current time is within the class duration
        if now >= start_time and now < end_time:
            # Trigger the scan immediately without any delay
            trigger_scan_with_retry(user_id, course, time_range)
            print(f"Triggered immediate scan for {course} at {time_range} for user {user_id}")

        elif time_difference > 0:
            # Schedule the reminder 5 minutes before the class
            reminder_timer = threading.Timer(time_difference - 300, remind_before_class, args=(user_id, course, time_range))
            reminder_timer.start()
            schedule_timers[user_id][course]['reminder'] = reminder_timer

            # Schedule the scan
            scan_timer = threading.Timer(time_difference, trigger_scan_with_retry, args=(user_id, course, time_range))
            scan_timer.start()
            schedule_timers[user_id][course]['scan'] = scan_timer

            print(f"Scheduled scan for {course} at {time_range} for user {user_id}")
        else:
            bot.send_message(user_id, f"Missed scan for {course} at {time_range}. It's already past the start time.")

    except Exception as e:
        print(f"Error scheduling scan: {e}")
        bot.send_message(user_id, f"Error scheduling scan for {course}: {e}")

def remind_before_class(user_id, course, time_range):
    """Sends a reminder message to the user 5 minutes before the class."""
    try:
        bot.send_message(user_id, f"Reminder: {course} starts at {time_range}.")
        print(f"Reminded user {user_id} about {course} at {time_range}")
    except Exception as e:
        print(f"Error sending reminder: {e}")
        bot.send_message(user_id, f"Error sending reminder for {course}: {e}")

def trigger_scan_with_retry(user_id, course, time_range):
    """Triggers the perform_scan_qr function and retries if the date doesn't match."""
    try:
        bot.send_message(user_id,f"Scanning for {course}")
        url = preset_targets_scan.get(course)
        if url:
            end_time_str = time_range.split('-')[1]
            end_hour, end_minute = int(end_time_str[:2]), int(end_time_str[2:])

            now = datetime.datetime.now()
            end_time = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)

            while now < end_time:  # Keep trying until the class ends
                if perform_scan_qr(user_id, url, is_scheduled=True):
                    bot.send_message(user_id, f"Scan initiated for {course}")  # Notify success
                    break  # Exit the loop if the scan was successful
                time.sleep(600)  # Wait 10 minutes before retrying
                now = datetime.datetime.now()
            else:
                bot.send_message(user_id, f"Failed to scan for {course}")  # Notify failure
        else:
            bot.send_message(user_id, f"Invalid course selection: {course}")
    except Exception as e:
        print(f"Error triggering scan: {e}")
        bot.send_message(user_id, f"Error triggering scan for {course}: {e}")

def show_today_schedule(user_id):
    """Shows the user's schedule for today."""
    today = datetime.datetime.now().strftime("%A")
    if timetable.has_section(str(user_id)) and timetable.has_option(str(user_id), today):
        courses = timetable.get(str(user_id), today).split(',')
        todays_plan = f"Today's Plan ({today}):\n"
        for course_time in courses:
            try:
                course, time_range = course_time.strip().split('|')
                todays_plan += f"  - {course} at {time_range}\n"
            except ValueError:
                print(f"Invalid course_time format: {course_time}")
                todays_plan += f"  - {course_time} (Invalid format)\n"
        bot.send_message(user_id, todays_plan)
    else:
        bot.send_message(user_id, f"No courses found for today ({today}).")
        
def schedule_daily_schedule_notification():
    """Schedules the show_today_schedule function to run every day at 0000."""
    try:
        while True:  # Keep the loop running indefinitely
            now = datetime.datetime.now()
            next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            time_difference = (next_midnight - now).total_seconds()

            # Schedule the show_today_schedule function for all users with scheduling enabled
            for user_id in user_settings:
                if user_settings.get(user_id, {}).get('scheduling_enabled', False):  # Check if scheduling is enabled
                    daily_schedule_timer = threading.Timer(time_difference, show_today_schedule, args=(user_id,))
                    daily_schedule_timer.start()

            # Sleep until the next midnight
            time.sleep(time_difference)

    except Exception as e:
        print(f"Error scheduling daily notification: {e}")

def scheduling_scan_handler(message):
    """Handles the /scheduling_scan command."""
    user_id = message.chat.id
    if user_id not in scheduling_scan_enabled:
        scheduling_scan_enabled[user_id] = False  # Initialize scheduling status

    if scheduling_scan_enabled[user_id]:
        # Disable scheduling
        scheduling_scan_enabled[user_id] = False
        bot.reply_to(message, "Scheduling scan disabled.", reply_markup=get_main_markup())

        # Cancel any existing timers
        if user_id in schedule_timers:
            for course, timers in schedule_timers[user_id].items():
                for timer_type, timer in timers.items():
                    if timer.is_alive():
                        timer.cancel()
            del schedule_timers[user_id]

    else:
        # Check if the user has an account
        if not user_accounts.has_section(str(user_id)):
            bot.reply_to(message, "No account saved. Please add your account using /acc first.", reply_markup=get_main_markup())
            return

        # Enable scheduling
        scheduling_scan_enabled[user_id] = True
        bot.reply_to(message, "Scheduling scan enabled.", reply_markup=get_main_markup())

        show_today_schedule(user_id)
        # Schedule scans for today's classes
        today = datetime.datetime.now().strftime("%A")  # Get today's day of the week
        if timetable.has_section(str(user_id)) and timetable.has_option(str(user_id), today):
            schedule_timers[user_id] = {}
            courses = timetable.get(str(user_id), today).split(',')
            for course_time in courses:
                try:
                    course, time_range = course_time.strip().split('|')
                    schedule_timers[user_id][course] = {}
                    schedule_scan(user_id, course, time_range)
                except ValueError:
                    print(f"Invalid course_time format: {course_time}")  
