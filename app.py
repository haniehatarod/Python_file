from flask import Flask, g, render_template, request, redirect, url_for, jsonify 
import sqlite3
from datetime import datetime

DB = 'todo.db'
app = Flask(__name__)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    # Check if table exists and get columns
    cursor = db.execute("PRAGMA table_info(tasks)")
    columns = [row[1] for row in cursor.fetchall()]
    table_exists = len(columns) > 0
    
    db.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'todo',
        created_at TEXT NOT NULL
    );
    ''')
    db.commit()
    
    # Add status column if table existed but column doesn't exist
    if table_exists and 'status' not in columns:
        try:
            db.execute('ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT "todo"')
            db.commit()
            # Migrate existing data: done=1 -> status='done', done=0 -> status='todo'
            db.execute('UPDATE tasks SET status = CASE WHEN done = 1 THEN "done" ELSE "todo" END')
            db.commit()
        except Exception as e:
            print(f"Migration error: {e}")
            db.rollback()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    db = get_db()
    
    # Get stats
    total = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0] or 0
    done = db.execute('SELECT COUNT(*) FROM tasks WHERE status = "done"').fetchone()[0] or 0
    in_progress = db.execute('SELECT COUNT(*) FROM tasks WHERE status = "in_progress"').fetchone()[0] or 0
    pending = db.execute('SELECT COUNT(*) FROM tasks WHERE status = "todo"').fetchone()[0] or 0
    
    tasks_rows = db.execute('SELECT * FROM tasks ORDER BY id DESC').fetchall()
    # Convert rows to dictionaries for easier template access
    tasks = []
    for row in tasks_rows:
        task = dict(row)
        # Ensure status exists, fallback to done field
        if 'status' not in task or not task['status']:
            task['status'] = 'done' if task.get('done', 0) else 'todo'
        tasks.append(task)
    
    return render_template(
        'index.html',
        tasks=tasks, 
        total=total, 
        done=done,
        in_progress=in_progress,
        pending=pending
    )

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title','').strip()
    if title:
        db = get_db()
        db.execute('INSERT INTO tasks (title, status, created_at) VALUES (?,?,?)', 
                  (title, 'todo', datetime.utcnow().isoformat()))
        db.commit()
    return redirect(url_for('index'))

@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle(task_id):
    db = get_db()
    row = db.execute('SELECT status, done FROM tasks WHERE id=?', (task_id,)).fetchone()
    if row:
        # Get status, fallback to done field if status doesn't exist
        try:
            current_status = row['status'] if row['status'] else ('done' if row['done'] else 'todo')
        except (KeyError, IndexError):
            current_status = 'done' if row['done'] else 'todo'
        # Toggle between todo and done
        new_status = 'done' if current_status == 'todo' else 'todo'
        db.execute('UPDATE tasks SET status=?, done=? WHERE id=?', 
                  (new_status, 1 if new_status == 'done' else 0, task_id))
        db.commit()
    return redirect(url_for('index'))

@app.route('/update_status/<int:task_id>', methods=['POST'])
def update_status(task_id):
    new_status = request.form.get('status', 'todo')
    if new_status in ['todo', 'in_progress', 'done']:
        db = get_db()
        db.execute('UPDATE tasks SET status=?, done=? WHERE id=?', 
                  (new_status, 1 if new_status == 'done' else 0, task_id))
        db.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>', methods=['POST'])
def delete(task_id):
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    db.commit()
    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0] or 0
    done = db.execute('SELECT COUNT(*) FROM tasks WHERE status = "done"').fetchone()[0] or 0
    in_progress = db.execute('SELECT COUNT(*) FROM tasks WHERE status = "in_progress"').fetchone()[0] or 0
    pending = db.execute('SELECT COUNT(*) FROM tasks WHERE status = "todo"').fetchone()[0] or 0
    
    return jsonify({
        'total': total,
        'done': done,
        'in_progress': in_progress,
        'pending': pending,
    })


with app.app_context():
    init_db()
    
if __name__ == '__main__':
    app.run(debug=True, port=5000)