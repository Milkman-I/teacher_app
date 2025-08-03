
import sqlite3

def create_exam_table():
    conn = sqlite3.connect("Teachers.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            group_id INTEGER,
            teacher_id TEXT
        )
    """)
    conn.commit()
    conn.close()

create_exam_table()

def create_exam(title, date, group_id, teacher_id):
    conn = sqlite3.connect("Teachers.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO exams (title, date, group_id, teacher_id) VALUES (?, ?, ?, ?)", (title, date, group_id, teacher_id))
    exam_id = cur.lastrowid
    conn.commit()
    conn.close()
    return exam_id

def get_exams_for_group(group_id):
    conn = sqlite3.connect("Teachers.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM exams WHERE group_id = ?", (group_id,))
    exams = cur.fetchall()
    conn.close()
    return exams

def get_exam_by_id(exam_id):
    conn = sqlite3.connect("Teachers.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,))
    exam = cur.fetchone()
    conn.close()
    return exam

def delete_exam(exam_id):
    conn = sqlite3.connect("Teachers.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM exams WHERE exam_id = ?", (exam_id,))
    conn.commit()
    conn.close()
    return True
