import sqlite3

# connection to the SQLite database
conn = sqlite3.connect('company_holiday_app.db')

# cursor to execute SQL commands
c = conn.cursor()


# Create the 'users' table 
c.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone_number TEXT,
    password_hash TEXT NOT NULL,
    number_of_free_days INTEGER DEFAULT 21,
    number_of_days_used INTEGER,
    system_role TEXT
    );
    ''')

# Create the 'holiday_periods' table with an approval_status field
c.execute('''
CREATE TABLE holiday_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period TEXT NOT NULL,
    approval_status TEXT,
    user_id INTEGER,
    substitute INTEGER,
    manager_approval_status TEXT,
    number_of_days_requested INTEGER,
    declined_by_user BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (substitute) REFERENCES users (id)
    );
        ''')

c.execute('''
    CREATE TABLE holiday_declined_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holiday_id INTEGER,
        substitute_id INTEGER,
        manager_id INTEGER,
        substitute_message TEXT,
        manager_message TEXT,
        general_message TEXT,
        notification_type TEXT,
        FOREIGN KEY (holiday_id) REFERENCES holiday_periods (id),
        FOREIGN KEY (substitute_id) REFERENCES users (id),
        FOREIGN KEY (manager_id) REFERENCES users (id)
    );
    ''')
c.execute('''

CREATE TABLE notifications_read (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id INTEGER,
    user_id INTEGER,
    read_by_user BOOLEAN,
    FOREIGN KEY (notification_id) REFERENCES holiday_declined_notifications (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
    );
          ''')

# Create the 'delegates' table

c.execute('''
CREATE TABLE delegates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id_vacancy INTEGER,
    user_id_responsible INTEGER,
    FOREIGN KEY (user_id_vacancy) REFERENCES users (id),
    FOREIGN KEY (user_id_responsible) REFERENCES users (id)
    );
        ''')

# create notifications table

c.execute(''' 
    CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT 0,
        related_holiday_id INTEGER,
        status TEXT,
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id),
        FOREIGN KEY (related_holiday_id) REFERENCES holiday_periods (id)
        );
            ''')

# Commit changes and close the connection
conn.commit()
conn.close()
