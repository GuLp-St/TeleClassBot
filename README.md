TeleClassBot 🤖
TeleClassBot is a Telegram bot designed to automate attendance tasks for Unimas students. It interacts with the Unimas QR attendance system to streamline and simplify the process of checking in and out of classes and labs.

Key Features ✨
Automated Search:
Search for courses by name or code.
Scan QR codes for known courses.
QR Code Scanning:
Extracts and displays QR codes.
Optionally scans using Bluestacks.
Account Management:
Save your UnimasNow login credentials.
Delete saved accounts.
Timetable Management:
Create and manage a weekly schedule.
(Planned) Scheduled scans based on timetable.
Settings:
Change search start point.
Set max search attempts.
Cancel Search: Stop an ongoing search.
How It Works ⚙️
TeleClassBot leverages the telebot library for Telegram interaction and selenium for web automation. It simulates user actions on the Unimas QR attendance website to perform tasks such as searching for courses, extracting QR codes, and submitting attendance.

The bot also incorporates features for user convenience, such as:

Preset Courses: A list of predefined courses for quick selection.
Bluestacks Integration: Optional use of Bluestacks for QR code scanning.
Scheduled Scans: (Planned) Ability to schedule automatic scans based on a timetable.
Usage 🚀
Start the bot: Send /start to the bot on Telegram.
Search for Courses: Use /search and choose /find or /scan_qr.
Scan QR Codes: Add your UnimasNow account with /acc and follow the prompts.
Manage Timetable: Use /timetable to add or remove courses.
Customize Settings: Use /settings to adjust search parameters.
Disclaimer ⚠️
This bot is intended for educational purposes and to assist Unimas students with attendance tasks. Please use it responsibly and ethically. The developers are not responsible for any misuse or consequences arising from the use of this bot.

Note: The bot may refresh every 300 searches to avoid issues with the Unimas website.

Contributing 🤝
Contributions are welcome! Feel free to submit issues or pull requests to improve the bot's functionality or address any bugs.

Let's make attendance a breeze! 💨