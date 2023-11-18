from flask import Flask, render_template, request, jsonify, flash, url_for, redirect, session, abort
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from datetime import timedelta
from functions import (execute_db, fetch_manager_approval_request, fetch_pending_holidays_for_substitute, 
                        check_for_holidays, update_user_free_days, user_db_password, 
                        change_password, user_system_role, update_user_info, all_persons_that_have_a_holiday,
                        check_for_user_sent_or_approved_holidays, restore_free_days_holiday_declined_user, select_user_substitute_approval_status)
from notification_functions import(holiday_declined_message, notification_seen_by_user)
import datetime

import secrets
import requests
import xml.etree.ElementTree as ET
import yfinance as yf

app = Flask(__name__)


# Initialize session settings
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = secrets.token_hex(32)
Session(app)





@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Login function
@app.route("/", methods=["GET", "POST"], endpoint='index')
def index():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        user = execute_db("SELECT * FROM users WHERE email = ?", (email,), fetchone=True)
        if user:
            password_hash = user[4]  
            if password_hash:
                if check_password_hash(password_hash, password):
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    return redirect(url_for('dashboard')) 
                else:
                    flash("Invalid password.", "danger")
            else:
                flash("Invalid email or password.", "danger")
        else:
            flash("Invalid email or password.", "danger")

    return render_template('login.html')

# Log out

@app.route("/log-out")
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/get_notifications')
def get_notifications():
    user_id = session.get('user_id')
    if user_id:
        notifications = fetch_pending_holidays_for_substitute(user_id)
        return jsonify(notifications)
    return jsonify([])

@app.route('/get_manager_notifications')
def get_substitute_notifications():
    substitute_id = session.get('user_id')
    if substitute_id:
        notifications = fetch_manager_approval_request(substitute_id)
        return jsonify(notifications)
    return jsonify([]), 403

# Dashboard function
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user_id = session.get('user_id')  

    if request.method == "POST":
        if not user_id:  
            return redirect(url_for('login'))

        try:
            period = request.form.get('dates')
            substitute_name = request.form.get('substitute')

            dates = request.form.get('dates').split(' - ')
            start_date = datetime.datetime.strptime(dates[0], '%m/%d/%Y')
            end_date = datetime.datetime.strptime(dates[1], '%m/%d/%Y')
            total_days = 0
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() < 5:
                    total_days += 1
                current_date += datetime.timedelta(days=1)

           
            total_days_available = execute_db("SELECT number_of_free_days FROM users WHERE id = ?", (user_id,), fetchone=True)

            if total_days_available:
                total_days_available = total_days_available[0]
            else:
                flash("User not found.", "danger")
                return redirect(url_for('dashboard'))

            total_days_available = int(total_days_available) if total_days_available is not None else 0
                        
            if total_days > total_days_available:
                flash("You have fewer free days than you want.", "danger")
                return redirect(url_for('dashboard'))

            if total_days == 0 :
                flash("Please select a period.", "warning")
                return redirect(url_for('dashboard'))

            # Fetch substitute ID 
            substitute_id = execute_db("SELECT id FROM users WHERE name = ?", (substitute_name,), fetchone=True)

            if not substitute_id:
                flash("Substitute not found", "danger")
                return redirect(url_for('dashboard'))

            substitute_id = substitute_id[0]
            approval_status = "Pending"
            manager_approval_status = "Pending"
            user_name = execute_db("SELECT name FROM users WHERE id = ?", (user_id,), fetchone=True)
            user_name=user_name[0]
            message = f"{user_name} want to take a brake. Would you accept to hold his possition on {period} ?"
            # Insert the new record into holiday_periods and get the last inserted ID
            related_holiday_id = execute_db(
                "INSERT INTO holiday_periods (period, approval_status, user_id, substitute, manager_approval_status, number_of_days_requested) VALUES (?, ?, ?, ?, ?, ?)", 
                (period, approval_status, user_id, substitute_id, manager_approval_status, total_days,),
                commit=True,
                lastrowid=True
            )

            # Insert the new notification record
            execute_db(
                "INSERT INTO notifications (sender_id, receiver_id, message, related_holiday_id, status) VALUES (?, ?, ?, ?, ?)", 
                (user_id, substitute_id, message, related_holiday_id, approval_status,),
                commit=True
            )
            
            flash(f"Your holiday notification has been sent to {substitute_name}. After acceptance, it will be forwarded to a manager.", "success")

        except Exception as e:
            print(f"Exception: {e}")
            flash("An error occurred while processing your request.", "danger")
            return redirect(url_for('dashboard'))

    if 'user_id' in session:
        if 'new_account' in session and session['new_account']:
            flash(f"Congratulations {session['username']}!!! Your account was created.", "success")
            session.pop('new_account', None)
        
        substitutes = execute_db("SELECT name, id FROM users WHERE id != ? AND (system_role != 'manager' OR system_role IS NULL);", (user_id,), fetchall=True)
        number_of_free_days = execute_db("SELECT number_of_free_days FROM users WHERE id = ?", (user_id,), fetchone=True)
        number_of_days_used = execute_db("SELECT number_of_days_used FROM users WHERE id = ?", (user_id,), fetchone=True)
        return render_template('dashboard.html', username=session['username'], number_of_days_used=number_of_days_used, number_of_free_days=number_of_free_days, substitute=substitutes, user_id=user_id)
    else:
        return redirect(url_for('index'))

@app.route('/get_user_days')
def get_user_days():
    user_id = session.get('user_id')
    if user_id is None:
        # Handle the case where there is no user in the session
        return jsonify({'error': 'User not logged in'}), 401

    query = "SELECT COALESCE(number_of_free_days, 0), COALESCE(number_of_days_used, 0) FROM users WHERE id = ?"
    result = execute_db(query, (user_id,), fetchone=True)

    if result is None:
        return jsonify({'error': 'User record not found'}), 404

    number_of_free_days, number_of_days_used = result

    return jsonify({
        'number_of_free_days': number_of_free_days,
        'number_of_days_used': number_of_days_used
    })


@app.route('/manager_buttons', methods=["POST"])
def handle_manager_buttons():
    notification_id = request.form.get('notification_id')
    action = request.form.get('action')

    if not notification_id:
        flash("Invalid request.", "error")
        return redirect(url_for('dashboard'))
    notification_id = int(notification_id)
    
    related_holiday_id, = execute_db("SELECT related_holiday_id FROM notifications WHERE id = ?", (notification_id,), fetchone=True)
    sender_name, = execute_db("SELECT users.name FROM users JOIN notifications ON notifications.sender_id = users.id WHERE notifications.id = ?;", (notification_id,), fetchone=True)
    
    if action == 'accept':
        # Update the status to 'accept' for the given notification ID
        execute_db("UPDATE notifications SET status = 'Accepted' WHERE id = ?", (notification_id,), commit=True)
        execute_db("UPDATE holiday_periods SET manager_approval_status = 'Accepted' WHERE id = ?", (related_holiday_id,), commit=True)
        update_user_free_days(related_holiday_id)
        flash(f"Free days accepted for {sender_name}.", "success")

    elif action == 'decline':
        # Update the status to 'decline' for the given notification ID
        execute_db("UPDATE notifications SET status = 'Declined' WHERE id = ?", (notification_id,), commit=True)
        execute_db("UPDATE holiday_periods SET manager_approval_status = 'Declined' WHERE id = ?", (related_holiday_id,), commit=True)
        flash(f"Free days declined for {sender_name}.", "warning")

    else:
        flash("Invalid action.", "error")
    
    return redirect(url_for('dashboard'))


@app.route('/holiday_buttons', methods=['POST'])
def handle_holiday_buttons():
    notification_id = request.form.get('notification_id')
    action = request.form.get('action')

    if not notification_id:
        flash("Invalid request.", "error")
        return redirect(url_for('dashboard'))
    notification_id = int(notification_id)

    if not notification_id or not action:
        flash("Invalid request.", "error")
        return redirect(url_for('dashboard'))

    query_result = execute_db("SELECT related_holiday_id, receiver_id, sender_id FROM notifications WHERE id = ?", (notification_id,), fetchone=True)
    if not query_result:
        flash("Notification not found.", "error")
        return redirect(url_for('dashboard'))

    related_holiday_id, receiver_id, sender_id = query_result
    
    # Fetch the name of the substitute (receiver)
    substitute_name = execute_db("SELECT name FROM users WHERE id = ?", (receiver_id,), fetchone=True)[0]
    requester_name = execute_db("SELECT name FROM users WHERE id = ?", (sender_id,), fetchone=True)[0]
    # Fetch the period of the original holiday request
    period = execute_db("SELECT period FROM holiday_periods WHERE id = ?", (related_holiday_id,), fetchone=True)[0]

    if action == 'accept':
        # Update the status to 'accept' for the given notification ID
        execute_db("UPDATE notifications SET status = 'Accepted' WHERE id = ?", (notification_id,), commit=True)
        # update holiday_periods
        execute_db("UPDATE holiday_periods SET approval_status = 'Accepted' WHERE id = ?", (related_holiday_id,), commit=True)
        # Send a new notification to managers for final approval
        managers = execute_db("SELECT id FROM users WHERE system_role = 'manager'", fetchall=True)
        for manager in managers:
            manager_id = manager[0]
            new_message = f"{substitute_name} has agreed to cover {requester_name} position for the period: {period}. Awaiting your final approval."
            execute_db("INSERT INTO notifications (sender_id, receiver_id, message, related_holiday_id) VALUES (?, ?, ?, ?)", 
                    (sender_id, manager_id, new_message, related_holiday_id), 
                    commit=True)
        
        flash(f"You've accepted to cover {requester_name}. A new notification has been sent to managers for final approval.", "success")
        
    elif action == 'decline':
        # Update the status to 'decline' for the given notification ID
        execute_db("UPDATE notifications SET status = 'Declined' WHERE id = ?", (notification_id,), commit=True)
        execute_db("UPDATE holiday_periods SET approval_status = 'Declined' WHERE id = ?", (related_holiday_id,), commit=True)
        flash(f"Holiday declined.", "warning")

    else:
        flash("Invalid action.", "error")
    
    return redirect(url_for('dashboard'))

@app.route("/substitute/<int:user_id>", methods=["GET"])
def substitute(user_id):
    # Check if the user is logged in
    session_user_id = session.get('user_id')
    if session_user_id is None:
        return redirect(url_for('login'))

    if session_user_id != user_id:
        return "Unauthorized", 403

    periods_info = check_for_holidays(user_id)

    if not periods_info:
        flash("No substitute information found for you.", "warning")
        return redirect(url_for('dashboard'))  

  
    return render_template('substitute_dashboard.html',  periods_info=periods_info, user_id=user_id)


@app.route("/create-account", methods=["GET", "POST"], endpoint='create_account')
def create_account():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        password_confirmation = request.form.get('password_confirmation')

        if not name or not email or not phone_number:
            flash("All fields are required.", "danger")
            return render_template('create_account.html')

        if password != password_confirmation:
            flash("Passwords do not match.", "danger")
            return render_template('create_account.html')

        password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        
        # first user manager
        user_exists = execute_db("SELECT 1 FROM users LIMIT 1", fetchone=True)
        system_role = 'manager' if not user_exists else 'user'

        execute_db("INSERT INTO users (name, phone_number, email, password_hash, system_role) VALUES (?, ?, ?, ?, ?)",
                    (name, phone_number, email, password_hash, system_role), commit=True)
        


        user = execute_db("SELECT * FROM users WHERE email = ?", (email,), fetchone=True)
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['new_account'] = True
        return redirect(url_for('dashboard'))

    return render_template('create_account.html')

@app.route("/holiday-table")
def holiday_table():
    session_user_id = session.get('user_id')
    if not session_user_id:
        return redirect(url_for('login'))
    
    holidays = all_persons_that_have_a_holiday()
    
    return render_template('holiday_users_table.html', user_id=session_user_id, holidays=holidays)

@app.route("/user-info", methods=["GET"])
def user_info():
    user_id = session.get('user_id')
    if not user_id:
        flash('Login first.', 'warning')
        return redirect(url_for('login'))

    user_holiday_info = check_for_user_sent_or_approved_holidays(user_id)

    return render_template("user_info.html", user_id=user_id, user_holiday_info=user_holiday_info)

@app.route("/decline-holiday/<int:id>", methods=["POST"])
def decline_holiday(id):
    execute_db("UPDATE holiday_periods SET declined_by_user = 1 WHERE id = ?", (id,), commit=True)
    days_restored = restore_free_days_holiday_declined_user(id)
    declined_notification_message_id, substitute = holiday_declined_message(id)
    notification_seen_by_user(declined_notification_message_id, substitute)
    if declined_notification_message_id:
        flash(f'Holiday declined. {days_restored} free days restored successfully.', 'success')
    else:
        flash(f'Holiday declined. {days_restored} free days restored successfully. But failed to notify.', 'warning')
    return redirect(url_for('user_info'))

@app.route('/notifications')
def notifications():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view notifications.', 'warning')
        return redirect(url_for('login'))

 
    notifications = execute_db(
        "SELECT id, general_message FROM holiday_declined_notifications WHERE id IN (SELECT notification_id FROM notifications_read WHERE user_id = ? AND read_by_user = FALSE)",
        (user_id,), fetchall=True
    )

    col_names = ['id', 'general_message']
    notifications_data = [dict(zip(col_names, notification)) for notification in notifications]
    
    return render_template('notifications.html', notifications_data=notifications_data, user_id=user_id)

@app.route('/holiday-status')
def holiday_status():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view holiday_status', 'warning')
        return redirect(url_for('login'))
    
    user_holiday_status = select_user_substitute_approval_status(user_id)
    print(user_holiday_status)
    return render_template('holiday_status.html', user_id=user_id, user_holiday_status=user_holiday_status)

@app.route('/notifications/<int:user_id>')
def notification_read(user_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view notifications.', 'warning')
        return redirect(url_for('login'))
    
    read_by_user_notifications = execute_db(
        """SELECT 
            hdn.id, 
            hdn.general_message, 
            nr.read_by_user 
        FROM 
            holiday_declined_notifications hdn
        JOIN 
            notifications_read nr ON hdn.id = nr.notification_id
        WHERE 
            nr.user_id = ? AND 
            nr.read_by_user = TRUE
        """,
        (user_id,), fetchall=True
    )
    print(read_by_user_notifications)
    if read_by_user_notifications is None:
        notifications_data = []
    else:
        col_names = ['id', 'general_message', 'read_by_user']
        notifications_data = [dict(zip(col_names, row)) for row in read_by_user_notifications]

    return render_template('notifications_read.html', notifications_data=notifications_data, user_id=user_id)


@app.route('/mark-notification-as-read/<int:notification_id>', methods=['POST'])
def mark_notification_as_read(notification_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to mark notifications as read.', 'warning')
        return redirect(url_for('login'))

    execute_db(
        "UPDATE notifications_read SET read_by_user = TRUE WHERE notification_id = ? AND user_id = ?",
        (notification_id, user_id),
        commit=True
    )

    flash('Notification marked as read.', 'success')
    return redirect(url_for('notifications'))




@app.route("/user-settings/<int:user_id>", methods=["GET", "POST"])
def user_settings(user_id):
    session_user_id = session.get('user_id')
    session_user_id = int(session_user_id)
    
    if not session_user_id:
        return redirect(url_for('login'))

    if session_user_id != user_id:
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('dashboard'))

    user_system_role_value = user_system_role(session_user_id)
    old_password = request.form.get('old-password')
    new_password = request.form.get('new-password')
    repeat_new_password = request.form.get('repeat-new-password')

    db_password = user_db_password(session_user_id)

    email_result = execute_db("SELECT email FROM users WHERE id = ?;", (session_user_id,), fetchone=True)
    user_email_adress = email_result[0] if email_result else "Email not found"
    
    if request.method == "POST":
        if not check_password_hash(db_password, old_password):
            flash(f"Old password is incorrect. Try again.", "danger")
            return redirect(url_for('user_settings', user_id=session_user_id))

        if new_password != repeat_new_password:
            flash(f"The repeated password doesn't match the new password. Try again.", "danger")
            return redirect(url_for('user_settings', user_id=session_user_id))

     
        new_hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=8)
        change_password(user_id, new_hashed_password)
        flash("Password changed successfuly.", "success")

    return render_template("user_settings.html", user_id=session_user_id, user_email_adress=user_email_adress, user_system_role_value=user_system_role_value, )

@app.route("/update_user/<int:user_id>", methods=["POST"])
def update_user(user_id):
    if 'user_id' not in session:
        flash("Please log in to continue.", "warning")
        return redirect(url_for('login'))

    if user_system_role(session['user_id']) != 'manager':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('dashboard'))

    email = request.form.get('email')
    job_role = request.form.get('job-role')
    department = request.form.get('department')

    update_user_info(user_id, email, job_role, department)
    flash(f"Information for user ID {user_id} has been updated successfully.", "success")
    return redirect(url_for('user_settings'))


# GET API KEYs
def get_api_key(key_name):
    with open('SECRETS.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith(key_name):
                _, api_key = line.strip().split(' = ')
                return api_key
    return None


@app.route('/finance_rates_comodi', methods=["GET", "POST"])
def finance_rates_comodi():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view notifications.', 'warning')
        return redirect(url_for('login'))
    
      # Extracting Currency Exchange Rates
    url_bnr = "https://www.bnr.ro/nbrfxrates.xml"
    rates = {}
    try:
        response_bnr = requests.get(url_bnr)
        response_bnr.raise_for_status()
        tree = ET.fromstring(response_bnr.content)
        namespaces = {'ns': 'http://www.bnr.ro/xsd'}
        
       
        for rate in tree.findall('.//ns:Rate', namespaces):
            currency = rate.get('currency')
            multiplier = rate.get('multiplier', 1)  
            rates[currency] = float(rate.text) / float(multiplier)
            
   
        rates['RON'] = 1.0
    except requests.RequestException as e:
        flash(f"Error fetching currency rates: {e}", 'error')
        return redirect(url_for('index'))  
    currency_list = sorted(rates.keys())

   
    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        from_currency = request.form.get('from_currency')
        to_currency = request.form.get('to_currency')
        
        if from_currency and to_currency and amount:
            try:
                if from_currency == to_currency:
                    result = amount
                elif from_currency == 'RON':
                    result = amount * rates[to_currency]
                else:
                    result = amount * rates[from_currency] / rates[to_currency]
                    
                result = round(result, 4) 
                flash(f'{amount} {from_currency} is {result} {to_currency}', 'success')
            except KeyError:
                flash('One of the selected currencies is not available.', 'error')
        else:
            flash('Please fill in all the fields correctly.', 'error')

    # get Gold Prices
    gold_api_key_name = 'goldapi'

    url_gold = "https://www.goldapi.io/api/XAU/USD"
    headers_gold = {
        "x-access-token": get_api_key(gold_api_key_name),
        "Content-Type": "application/json"
    }
    keys_gold = ['price', 'price_gram_24k']
    key_map_gold = {
        'price': 'Uncie',
        'price_gram_24k': 'Gram',
    }

    information_gold = {}
    try:
        response_gold = requests.get(url_gold, headers=headers_gold)
        response_gold.raise_for_status()
        data_gold = response_gold.json()
        for key in keys_gold:
            if key in data_gold:
                information_gold[key_map_gold[key]] = float(data_gold[key])  
    except requests.RequestException as e:
        return f"Error fetching gold prices: {e}", 500
    
    # get Oil Prices
    oil_api_key_name = 'oilpriceapi'
    url_oil = 'https://api.oilpriceapi.com/v1/prices/latest'
    headers_oil = {
        'Authorization': get_api_key(oil_api_key_name),
        'Content-Type': 'application/json'
    }

    information_oil = {}
    try:
        response_oil = requests.get(url_oil, headers=headers_oil)
        response_oil.raise_for_status()
        data_oil = response_oil.json()['data']
        if 'price' in data_oil:
            information_oil['Brent'] = float(data_oil['price']) 
    except requests.RequestException as e:
        return f"Error fetching oil prices: {e}", 500
  
    return render_template('finance_rates_comodi.html', rates=rates, gold_info=information_gold, oil_info=information_oil, user_id=user_id, currencies=currency_list)

@app.route("/finance")
def finance():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to view notifications.', 'warning')
        return redirect(url_for('login'))
    return render_template('finance.html', user_id=user_id)




# https://pypi.org/project/yfinance/
@app.route('/stock_market', methods=['GET', 'POST'])
def stock_market():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        ticker_symbol = request.form.get('ticker_symbol').upper()
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # Set default end date to today 
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            # Fetch stock market data for ticker
            stock = yf.Ticker(ticker_symbol)
            stock_data = stock.history(start=start_date, end=end_date).reset_index()

            if not stock_data.empty:
                # Format the date and extract only below data
                data = [{'Date': record['Date'].strftime('%Y-%m-%d'), 
                         'Open': record['Open'], 
                         'High': record['High'], 
                         'Low': record['Low'], 
                         'Close': record['Close'], }
                        for record in stock_data.to_dict('records')]
            else:
                data = None
                flash('No data found for the given ticker or date range.', 'warning')

        except ValueError:
            flash('Invalid date format. Please enter a valid date.', 'warning')
            data = None

        return render_template('stock_market.html', user_id=user_id, data=data, ticker_symbol=ticker_symbol)

    return render_template('stock_market.html', user_id=user_id)


# API SEND USER DATA
#This API is used to send user data to another app. For example to the website at contact us page. 
API_KEY_USER_DATA = "API_987654321" 
@app.route('/api/users', methods=['GET'])
def authenticate_user():
    api_key = request.headers.get('Authorization')
    if api_key != API_KEY_USER_DATA:
        return jsonify({"error": "Unauthorized"}), 401

    users_data = execute_db("SELECT name, email, phone_number FROM users", fetchall=True)

    # Create a list of dictionaries, each representing a user
    formatted_users_data = [{user[0]:{"email": user[1], "phone": user[2]}} for user in users_data]

    return jsonify({"users": formatted_users_data})

if __name__ == '__main__':
    app.run( debug=True, port=5000)

