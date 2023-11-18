import sqlite3
from datetime import datetime
# db manipulation


def execute_db(query, args=(), fetchone=False, fetchall=False, commit=False):
    try:
        with sqlite3.connect("company_holiday_app.db") as con:
            cur = con.cursor()
            cur.execute(query, args)
            if commit:
                con.commit()
                return cur.lastrowid 
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        con.rollback()
        return None




def get_manager():
    manager, = execute_db("SELECT id from users WHERE system_role = 'manager';", fetchone=True)

    return manager


def holiday_declined_message(holiday_id):
    try:
        substitute_and_days = execute_db(
            "SELECT period, user_id, substitute FROM holiday_periods WHERE id = ? AND declined_by_user = 1",
            (holiday_id,), fetchone=True)

        if not substitute_and_days:
            print("No such declined holiday found.")
            return None

        period, user_id, substitute = substitute_and_days

        # Get the user's names
        user_name_info = execute_db("SELECT name FROM users WHERE id = ?", (user_id,), fetchone=True)
        substitute_name_info = execute_db("SELECT name FROM users WHERE id = ?", (substitute,), fetchone=True)

        user_name = user_name_info[0] if user_name_info else "Unknown User"
        substitute_name = substitute_name_info[0] if substitute_name_info else "Unknown Substitute"

        decline_message = f"Dear {substitute_name}, {user_name} has declined holiday in period {period}."
        notification_type = "Holiday Declined"

        # Insert the notification and get the notification ID
        notification_id = execute_db(
            "INSERT INTO holiday_declined_notifications (holiday_id, general_message, notification_type) VALUES (?, ?, ?)",
            (holiday_id, decline_message, notification_type),
            commit=True
        )

        if notification_id:
            return notification_id, substitute
        else:
            print("Failed to retrieve the notification ID.")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def notification_seen_by_user(notification_id, user_id):
    try:
        execute_db(
            "INSERT INTO notifications_read (notification_id, user_id, read_by_user) VALUES (?, ?, FALSE)",
            (notification_id, user_id),
            commit=True
        )
    except Exception as e:
        print(f"Error marking notification as seen by user: {e}")
