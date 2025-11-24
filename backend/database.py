import sqlite3
import json
from datetime import datetime
import uuid
import os

DB_PATH = "pomelo.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def create_conversation(title="New Chat"):
    conn = get_db_connection()
    cursor = conn.cursor()
    conversation_id = str(uuid.uuid4())
    cursor.execute(
        'INSERT INTO conversations (id, title) VALUES (?, ?)',
        (conversation_id, title)
    )
    conn.commit()
    conn.close()
    return conversation_id

def add_message(conversation_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)',
        (conversation_id, role, content)
    )
    # Update conversation timestamp
    cursor.execute(
        'UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (conversation_id,)
    )
    conn.commit()
    conn.close()

def get_conversations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM conversations ORDER BY updated_at DESC')
    conversations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return conversations

def get_messages(conversation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
        (conversation_id,)
    )
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def delete_conversation(conversation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
    cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
    conn.commit()
    conn.close()

def update_conversation_title(conversation_id, title):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE conversations SET title = ? WHERE id = ?',
        (title, conversation_id)
    )
    conn.commit()
    conn.close()

# Initialize DB on module load
init_db()