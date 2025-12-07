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
    db.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    ''')
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    db = get_db()
    
    stats = db.execute('SELECT COUNT(*) AS total, SUM(done) AS done FROM tasks').fetchone()
    total = stats['total'] if stats['total'] is not None else 0
    done = stats['done'] if stats['done'] is not None else 0
    pending = total - done
    
    pct_done = (done / total * 100) if total else 0
    
    tasks = db.execute('SELECT * FROM tasks ORDER BY id DESC').fetchall()
    
    return render_template(
        'index.html',
        tasks=tasks, 
        total=total, 
        done=done, 
        pending=pending, 
        pct_done=round(pct_done, 1)
    )

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title','').strip()
    if title:
        db = get_db()
        db.execute('INSERT INTO tasks (title, created_at) VALUES (?,?)', (title, datetime.utcnow().isoformat()))
        db.commit()
    return redirect(url_for('index'))

@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle(task_id):
    db = get_db()
    row = db.execute('SELECT done FROM tasks WHERE id=?', (task_id,)).fetchone()
    if row:
        new = 0 if row['done'] else 1
        db.execute('UPDATE tasks SET done=? WHERE id=?', (new, task_id))
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
    stats = db.execute('SELECT COUNT(*) AS total, SUM(done) AS done FROM tasks').fetchone()
    total = stats['total'] if stats['total'] is not None else 0
    done = stats['done'] if stats['done'] is not None else 0
    
    return jsonify({
        'total': total,
        'done': done,
        'pending': total - done,
    })


with app.app_context():
    init_db()
    
if __name__ == '__main__':
    app.run(debug=True, port=5000)