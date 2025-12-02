import aiosqlite
import json
from datetime import datetime
import uuid
import os

DB_PATH = "pomelo.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if updated_at exists (migration)
        # aiosqlite doesn't support PRAGMA table_info easily in the same way, 
        # but we can try-catch or check schema. 
        # For simplicity in this async version, we'll assume new DB or handle migration carefully.
        # Let's just run the add column and ignore error if exists
        try:
            await db.execute('ALTER TABLE conversations ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except Exception:
            pass

        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await db.commit()

async def get_setting(key):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT value FROM settings WHERE key = ?', (key,)) as cursor:
            result = await cursor.fetchone()
            return result['value'] if result else None

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        await db.commit()

async def create_conversation(title="New Chat"):
    conversation_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO conversations (id, title) VALUES (?, ?)',
            (conversation_id, title)
        )
        await db.commit()
    return conversation_id

async def add_message(conversation_id, role, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)',
            (conversation_id, role, content)
        )
        # Update conversation timestamp
        await db.execute(
            'UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (conversation_id,)
        )
        await db.commit()

async def get_conversations(limit=50, offset=0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?', 
            (limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_messages(conversation_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
            (conversation_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def delete_conversation(conversation_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
        await db.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        await db.commit()

async def update_conversation_title(conversation_id, title):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE conversations SET title = ? WHERE id = ?',
            (title, conversation_id)
        )
        await db.commit()