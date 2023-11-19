# eagles-break

#### Video Demo: https://youtu.be/mBmqNxh9sGk

#### Description:

The Problem: Eagles-break emerges as a revolutionary solution, particularly addressing the inefficiencies and lapses inherent in traditional methods of managing employee leave. In the past, employees typically requested time off by sending an email to their manager. This method, although straightforward, often led to significant organizational challenges. For instance, if an employee planned a holiday that was more than two weeks away, it was not uncommon for the manager to forget about approving this leave as the date approached. This lack of recall could lead to operational disruptions, especially if the manager had not communicated the approval to the rest of the team. Moreover, under the old system, there was a general lack of transparency and awareness among other employees regarding their colleagues' scheduled leaves. This opacity often resulted in unforeseen gaps in the workforce, as colleagues were uninformed about pending absences and could not plan accordingly. In a busy work environment, particularly in sectors like investment advisory where market responsiveness is critical, such oversights could have cascading effects on productivity and team dynamics.

The solution: Eagles-break directly addresses these issues by introducing a streamlined, transparent, and collaborative approach to leave management. The application's robust notification system ensures that once a leave request is approved, all relevant parties are informed promptly. This feature eliminates the possibility of managerial forgetfulness or oversight.Furthermore, the substitution system embedded within Eagles-breake adds an additional layer of operational security. By requiring employees to find a colleague to cover their duties, the application ensures that there are no sudden gaps in the workflow. This system not only promotes teamwork but also instills a sense of collective responsibility among employees to contribute to uninterrupted business operations.

Eagles-break’s comprehensive approach transforms leave management from a potential point of failure into an efficient, transparent, and cohesive process. It eradicates the pitfalls of the old email-based system, replacing it with a dynamic, interactive, and foolproof mechanism that benefits managers, employees, and the organization as a whole. In summary, Eagles-breake is not just an application for managing leave; it's a strategic tool that enhances overall organizational effectiveness, particularly in fast-paced, responsive sectors like investment management.

## Files

## static/
The static folder contains static files such as JavaScript and CSS. Here, you can also find the photo/ directory, which houses all the photos used in this project.
In script.js, there are two scripts that send real-time notifications: one for a normal user and another for a manager.
style.css includes some custom CSS. - The project primarily uses Bootstrap 5 for styling.

## templates/
The templates directory holds all HTML files. It features base.html along with other files that extend base.html, following the Jinja2 convention.
In some files, such as dashboard.html, you'll find JavaScript for AJAX updates to free days or for a date picker.
holiday_status.html and holiday_users_table.html include JavaScript for paginating tables. Additionally, holiday_users_table.html contains a script for search functionality.

## .gitignore
In this file I mention what files to ignore:
venv/
__pycache__/
flask_session/
company_holiday_app.db
info.txt

__pycache__/

SECRETS.txt

## app.py
This script imports Flask modules for web development, werkzeug for security functions, flask_session for session management, and datetime. It also includes imports from functions.py and notification_functions.py, which provide custom logic and utility functions specific to this application. The latter, notification_functions.py, is particularly used for handling notifications and is separated from functions.py due to its size and complexity.

The script leverages external libraries such as secrets for generating secure random numbers, requests for HTTP communication, xml.etree.ElementTree for XML processing (specifically for the BNR API), and yfinance for accessing financial market data. This wide range of dependencies indicates a diverse set of functionalities.

Key components of app.py include route definitions for HTTP request handling, authentication and authorization logic, data processing routines, and financial data management using yfinance.

Additionally, the authenticate_user function serves as an API endpoint to securely transmit user data to the company website, using an API key for security. This functionality is important for integrating the application with external systems or websites, ensuring that user data is shared securely and efficiently.

Initialization: The application is initialized with Flask(__name__), and session settings are configured with session permanence, lifetime, type, and a secret key.
After Request Function: This function is defined to modify response headers to prevent caching.

dashboard: Displays user-specific information and allows submitting holiday requests. It also manages user holidays and displays data for managers.

create_account: Handles new user account creation.

get_notifications, get_manager_notifications: Fetch and return notifications for users and managers.

handle_manager_buttons, handle_holiday_buttons: Manage actions (accept or decline) on holiday requests.

substitute: Displays substitute information for a given user.

user_info, get_user_days: Provide user-specific information and holiday details.

decline_holiday: Allows users to decline holiday requests.

user_settings, update_user: Manage user settings and allow updates to user information.

finance_rates_comodi: Fetches and displays financial data like currency rates, gold prices, and oil prices.

stock_market: Provides stock market data based on user input.

finance: A route for displaying financial information.

authenticate_user: An API endpoint to send user data, secured with an API key. - This helps in sending the users data to the company website. 

## database.py
This is one of the most important file to start the project. It set the database.

## functions.py
This file is focused on database interactions and business logic.
It uses sqlite3 for database operations.
execute_db function is defined for executing database queries with various options like fetching one or all records, committing changes, and getting the ID of the last inserted row.

fetch_pending_holidays_for_substitute fetches pending holiday notifications for a given substitute, excluding managers.

fetch_manager_approval_request retrieves holiday requests awaiting approval by a manager.

check_for_holidays: Lists holidays for a given user that are accepted by both the substitute and the manager.

check_for_user_sent_or_approved_holidays retrieves holidays sent or approved by a specific user.

update_user_free_days updates the count of free days and days used for a user based on holiday approvals.

all_persons_that_have_a_holiday fetches holiday information for all users, along with the status based on the current date.

restore_free_days_holiday_declined_user restores free days to a user whose holiday was declined.

fetch_notifications retrieves pending notifications for a user.
get_users: Fetches a list of users excluding the one specified by user_id.

user_db_password retrieves the password hash for a user.

change_password updates the password for a user.

user_system_role fetches the system role of a user.

get_all_users retrieves a comprehensive list of all users and their details.

update_user_info updates the email, job role, and department for a user.

get_all_users_and_their_status_for_manager provides a detailed list of all users for a manager's view, including free days and days used.

select_user_substitute_approval_status gets the approval status of holidays for a user and their substitutes.


## notification_functions.py
This file also handle database interactions and possibly notification logic.

It contains functions related to notifications within the application, such as sending notifications to users.
get_manager function retrieves the ID of the user with the system role 'manager'.

holiday_declined_message function It retrieves details about a declined holiday request, including the period, user ID, and substitute.Fetches names of the user and the substitute from the database.Constructs a notification message indicating that the holiday has been declined and inserts this notification into the database.

The purpose of notification_seen_by_user function is to mark a notification as seen by a user.

### Set project 
1. python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
2. python database.py - to create db (When users sign up, if there is no prior user, the first user will be assigned as the manager.)
3. Create a SECRETS.txt file that include 
goldapi = [API](https://www.goldapi.io/dashboard)
oilpriceapi = [API](https://www.oilpriceapi.com/)

### APIs

## The app has two APIs. To fully utilize the app, you should obtain the API keys.

API | Description | Auth | Free | 

|---|---|---|---|---|

| [Gold API](https://www.goldapi.io/dashboard) | API to get gold price data. | `apiKey` | Yes | 
| [Oil Price API](https://www.oilpriceapi.com/) | API to get BRENT price data. | `apiKey`  | Yes | 
