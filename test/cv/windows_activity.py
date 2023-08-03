import sqlite3
from datetime import datetime
import pytz




# Connect to the SQLite database
conn = sqlite3.connect('windows_activity.db')

# Create a table to store window activity
conn.execute('''
    CREATE TABLE IF NOT EXISTS window_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        window_id TEXT,
        status TEXT,
        window_title TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

# Insert window activity data into the table
def insert_window_activity(window_id, status, window_title):
    current_time = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("INSERT INTO window_activity (window_id, status, window_title, timestamp) VALUES (?, ?, ?, ?)",
                 (window_id, status, window_title, current_time))
    conn.commit()  # Commit the changes

def retrieve_window_activity():
    cursor = conn.cursor()
    # cursor.execute("SELECT * FROM window_activity")
    cursor.execute("SELECT * FROM window_activity ORDER BY timestamp DESC LIMIT 5")
    rows = cursor.fetchall()
    return rows

# Close the database connection
def close_connection():
    conn.close()
