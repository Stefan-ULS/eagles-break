import sqlite3
from datetime import datetime

def execute_db(query, args=(), fetchone=False, fetchall=False, commit=False, lastrowid=False):
    try:
        with sqlite3.connect("company_holiday_app.db") as con:
            cur = con.cursor()
            cur.execute(query, args)
            if commit:
                con.commit()
                if lastrowid:
                    return cur.lastrowid
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        con.rollback()
        return None


def fetch_pending_holidays_for_substitute(substitute_id):
    user_role = execute_db("SELECT system_role FROM users WHERE id = ?", (substitute_id,), fetchone=True)
    query_result = None  
    
    if user_role and user_role[0] != 'manager': 
        query_result = execute_db("""
        SELECT notifications.id, notifications.message FROM notifications 
        JOIN users ON notifications.sender_id = users.id 
        WHERE notifications.receiver_id = ? 
        AND notifications.status = 'Pending'
        """, (substitute_id,), fetchall=True)
    
    if query_result is None:
        print("Query failed for some reason or user is a manager.")
        return []
    
    return [{'id': row[0], 'message': row[1]} for row in query_result]

def fetch_manager_approval_request(user_id):
    # First, check if the user is a manager.
    user_role = execute_db("SELECT system_role FROM users WHERE id = ?", (user_id,), fetchone=True)
    
    if user_role is None:
        print("User not found.")
        return []

    if user_role[0] == 'manager':
        query_result = execute_db("""
            SELECT notifications.id, notifications.message 
            FROM notifications 
            WHERE notifications.receiver_id = ? 
            AND (notifications.status IS NULL OR (notifications.status != 'Accepted' AND notifications.status != 'Declined'))
        """, (user_id,), fetchall=True)

        if query_result is None:
            print("Query failed for some reason.")
            return []

        return [{'id': row[0], 'message': row[1]} for row in query_result]
    else:
        return []


def check_for_holidays(user_id):
    query_result = execute_db("""
                                SELECT holiday_periods.period, users.name, declined_by_user
                                FROM holiday_periods 
                                JOIN users ON users.id = holiday_periods.user_id 
                                WHERE holiday_periods.substitute = ? 
                                AND holiday_periods.approval_status = 'Accepted' 
                                AND holiday_periods.manager_approval_status = 'Accepted';
                            """, (user_id,), fetchall=True)

    if not query_result:
        return 0
    
    column_names = ['period', 'name', 'declined_by_user']
    info = [dict(zip(column_names, info)) for info in query_result]

    return info

def check_for_user_sent_or_approved_holidays(user_id):
    query_result = execute_db("""
                                SELECT 
                                    holiday_periods.id, 
                                    holiday_periods.period, 
                                    substitute_users.name AS substitute_name, 
                                    users.name 
                                FROM holiday_periods 
                                JOIN users ON holiday_periods.user_id = users.id 
                                JOIN users AS substitute_users ON holiday_periods.substitute = substitute_users.id 
                                WHERE users.id = ? 
                                AND holiday_periods.approval_status = 'Accepted' 
                                AND holiday_periods.manager_approval_status = 'Accepted'
                                AND holiday_periods.declined_by_user = 0;
                            """, (user_id,), fetchall=True)

    if not query_result:
        return []
    
    column_names = ['id', 'period', 'substitute', 'name']
    info = [dict(zip(column_names, info)) for info in query_result]

    return info

def fetch_notifications(user_id):
    result = execute_db("SELECT message, related_holiday_id FROM notifications WHERE receiver_id = ? AND status = 'Pending'", (user_id,), fetchall=True)
    print(f"Fetched Notifications: {result}")
    return result

def get_users(user_id):
    result = execute_db("SELECT name, job_role FROM users WHERE id != ?", (user_id,), fetchall=True)
    if not result:
        print("No other users found in the database.")
        return []
    
    column_names = ['name', 'job_role']
    users = [dict(zip(column_names, user)) for user in result] 
    
    return users

def update_user_free_days(related_holiday_id):
    query_result = execute_db(
        "SELECT number_of_days_requested, user_id FROM holiday_periods WHERE id = ? AND approval_status = 'Accepted' AND manager_approval_status = 'Accepted';", 
        (related_holiday_id,), 
        fetchone=True
    )

    if not query_result:
        print("Holiday ID not found or not approved.")
        return

    number_of_days_approved, user_id = query_result
    print(f"Days Approved: {number_of_days_approved}, User ID: {user_id}")  # DEBUG

    # Update the number of days used by the user
    execute_db(
        "UPDATE users SET number_of_days_used = COALESCE(number_of_days_used, 0) + ? WHERE id = ?;", 
        (number_of_days_approved, user_id), 
        commit=True
    )

    # Update the number of free days remaining for the user
    execute_db(
        "UPDATE users SET number_of_free_days = number_of_free_days - ? WHERE id = ?;", 
        (number_of_days_approved, user_id), 
        commit=True
    )

def all_persons_that_have_a_holiday():
    result = execute_db("""
                          SELECT
                            u1.name AS holiday_name, 
                            u2.name AS substitute_name, 
                            hp.period AS holiday_period, 
                            IFNULL(hp.number_of_days_requested, 'N/A') AS number_of_days
                          FROM 
                            holiday_periods AS hp
                          JOIN 
                            users AS u1 ON hp.user_id = u1.id
                          JOIN 
                            users AS u2 ON hp.substitute = u2.id
                          LEFT JOIN 
                            holiday_declined_notifications AS hdn ON hp.id = hdn.holiday_id
                          WHERE 
                            hp.manager_approval_status = 'Accepted' 
                            AND hdn.holiday_id IS NULL
                          ORDER BY 
                            hp.id DESC;
                        """, fetchall=True)
    if result is None:
        return []
    
    col_names = ['name', 'substitute', 'period', 'nrOfDays']
    user_data = [dict(zip(col_names, user)) for user in result]

    today = datetime.today().date()

    for data in user_data:
        # Extract the end date from the 'period' string and convert it to date 
        end_date_str = data['period'].split('-')[1].strip()
        end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()
        data['status'] = 'green' if end_date >= today else 'red'
        
    return user_data


def select_user_substitute_approval_status(user_id):
    result = execute_db('''
                        SELECT 
                            hp.period,
                            hp.approval_status,
                            hp.manager_approval_status,
                            u.name AS user_name,
                            s.name AS substitute_name
                        FROM 
                            holiday_periods AS hp
                        JOIN 
                            users AS u ON hp.user_id = u.id
                        LEFT JOIN 
                            users AS s ON hp.substitute = s.id
                        WHERE u.id = ?
                        ORDER BY 
                            hp.period DESC
                        ''',(user_id,), fetchall=True)
    if result is None:
            return []
        
    col_names = ['hp_period', 'hp_approval_status', 'hp_manager_approval_status', 's_name']
    user_holiday_data = [dict(zip(col_names, user_holiday)) for user_holiday in result]
    print(user_holiday_data)
    return user_holiday_data


def user_db_password(user_id):
    password, = execute_db("SELECT password_hash FROM users WHERE id = ?", (user_id,), fetchone=True)
    if password is None:
        return
    return password


def change_password(user_id, new_hashed_password):
    try:
        execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (new_hashed_password, user_id), commit=True)
        print("Password updated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

def user_system_role(user_id):
    try:
        role, = execute_db("SELECT system_role FROM users WHERE id = ?", (user_id,), fetchone=True)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None  
    
    return role

def get_all_users():
    result = execute_db("SELECT id, name, email, phone_number, system_role, job_role, team, department_id FROM users", fetchall=True)

    if not result:
        return 0
    
    column_names = ['id', 'name', 'email', 'phone_number', 'system_role', 'job_role', 'team', 'department_id']
    users = [dict(zip(column_names, user)) for user in result]

    return users

def update_user_info(user_id, email, job_role, department):
    try:
        execute_db(
            "UPDATE users SET email = ?, job_role = ?, department = ? WHERE id = ?",
            (email, job_role, department, user_id),
            commit=True
        )
        print(f"User {user_id}'s information updated successfully.")
    except Exception as e:
        print(f"An error occurred while updating user {user_id}'s information: {e}")


def restore_free_days_holiday_declined_user(holiday_id):
    #  get the number of days that were requested in the declined holiday
    holiday_info = execute_db(
        "SELECT user_id, number_of_days_requested FROM holiday_periods WHERE id = ? AND declined_by_user = 1",
        (holiday_id,), fetchone=True)
    
    if holiday_info:
        user_id, number_of_days_requested = holiday_info
        
        # restore the number of free days and update the number of days used for the user
        execute_db(
            '''
            UPDATE users 
            SET number_of_free_days = number_of_free_days + ?,
                number_of_days_used = number_of_days_used - ?
            WHERE id = ?
            ''',
            (number_of_days_requested, number_of_days_requested, user_id), commit=True)
        
        return number_of_days_requested
    else:
        print("No such declined holiday found.") 

def get_all_users_and_their_status_for_manager():
    data = execute_db('''
                        SELECT 
                            u.id,
                            u.name,
                            u.email,
                            u.phone_number,
                            u.number_of_free_days,
                            u.number_of_days_used
                        FROM 
                            users u
                      ''', fetchall=True)
    
    if data is None:
        return []

    # Adjust column names to match the SQL query
    col_names = ['id', 'name', 'email', 'phone_number', 'number_of_free_days', 'number_of_days_used']

    # Use a different variable name inside the list comprehension
    user_data_for_manager = [dict(zip(col_names, user_data)) for user_data in data]
    print(user_data_for_manager)
    return user_data_for_manager