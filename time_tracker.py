"""
Minimal Professional Project Time Tracker (Windows)

Features:
- Start / Stop timer per project (single active timer)
- Multiple projects
- Notes per time entry
- Daily & weekly totals
- Export to CSV (Excel-friendly)
- Auto-save on close (SQLite)
- Simple, minimal, Apple-like UI using Tkinter

Build EXE:
  pip install pyinstaller
  pyinstaller --onefile --noconsole time_tracker.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import time
import csv
from datetime import datetime, timedelta

DB_FILE = "time_tracker.db"

class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")
        self.root.geometry("950x600")
        self.root.configure(bg="#f5f5f7")

        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        self.create_tables()

        self.active_project_id = None
        self.start_time = None

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=26)
        style.configure("TButton", padding=6)

        self.build_ui()
        self.refresh_projects()
        self.refresh_entries()
        self.update_timer()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )""")

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration INTEGER,
            note TEXT
        )""")
        self.conn.commit()

    def build_ui(self):
        left = tk.Frame(self.root, bg="#f5f5f7")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(left, text="Projects", bg="#f5f5f7", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.project_list = tk.Listbox(left, width=25, height=15)
        self.project_list.pack(pady=5)

        tk.Button(left, text="+ Add Project", command=self.add_project).pack(fill=tk.X, pady=2)
        tk.Button(left, text="▶ Start", command=self.start_timer).pack(fill=tk.X, pady=2)
        tk.Button(left, text="■ Stop", command=self.stop_timer).pack(fill=tk.X, pady=2)

        right = tk.Frame(self.root, bg="#ffffff")
        right.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.timer_label = tk.Label(right, text="00:00:00", font=("Segoe UI", 28, "bold"), bg="#ffffff")
        self.timer_label.pack(anchor="w")

        tk.Label(right, text="Note", bg="#ffffff").pack(anchor="w")
        self.note_entry = tk.Entry(right)
        self.note_entry.pack(fill=tk.X, pady=4)

        columns = ("project", "start", "end", "duration", "note")
        self.tree = ttk.Treeview(right, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.title())
        self.tree.pack(expand=True, fill=tk.BOTH, pady=8)

        bottom = tk.Frame(right, bg="#ffffff")
        bottom.pack(fill=tk.X)

        tk.Button(bottom, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT)
        tk.Button(bottom, text="Daily / Weekly Totals", command=self.show_totals).pack(side=tk.LEFT, padx=5)

    def refresh_projects(self):
        self.project_list.delete(0, tk.END)
        self.cursor.execute("SELECT name FROM projects ORDER BY name")
        for row in self.cursor.fetchall():
            self.project_list.insert(tk.END, row[0])

    def refresh_entries(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.cursor.execute("""
        SELECT projects.name, start_time, end_time, duration, note
        FROM entries JOIN projects ON entries.project_id = projects.id
        ORDER BY start_time DESC
        """)
        for r in self.cursor.fetchall():
            self.tree.insert("", tk.END, values=(r[0], r[1], r[2], self.format_time(r[3]), r[4]))

    def add_project(self):
        name = tk.simpledialog.askstring("New Project", "Project name:")
        if name:
            try:
                self.cursor.execute("INSERT INTO projects(name) VALUES (?)", (name,))
                self.conn.commit()
                self.refresh_projects()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Project already exists")

    def start_timer(self):
        if self.active_project_id:
            messagebox.showwarning("Running", "Timer already running")
            return
        selection = self.project_list.curselection()
        if not selection:
            return
        project_name = self.project_list.get(selection[0])
        self.cursor.execute("SELECT id FROM projects WHERE name=?", (project_name,))
        self.active_project_id = self.cursor.fetchone()[0]
        self.start_time = time.time()

    def stop_timer(self):
        if not self.active_project_id:
            return
        end = time.time()
        duration = int(end - self.start_time)
        self.cursor.execute(
            "INSERT INTO entries(project_id, start_time, end_time, duration, note) VALUES (?,?,?,?,?)",
            (self.active_project_id, datetime.fromtimestamp(self.start_time), datetime.fromtimestamp(end), duration, self.note_entry.get())
        )
        self.conn.commit()
        self.active_project_id = None
        self.start_time = None
        self.note_entry.delete(0, tk.END)
        self.timer_label.config(text="00:00:00")
        self.refresh_entries()

    def update_timer(self):
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            self.timer_label.config(text=self.format_time(elapsed))
        self.root.after(1000, self.update_timer)

    def format_time(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:02}"

    def show_totals(self):
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        self.cursor.execute("SELECT SUM(duration) FROM entries WHERE date(start_time)=?", (today,))
        daily = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(duration) FROM entries WHERE date(start_time)>=?", (week_start,))
        weekly = self.cursor.fetchone()[0] or 0
        messagebox.showinfo("Totals", f"Today: {self.format_time(daily)}\nThis Week: {self.format_time(weekly)}")

    def export_csv(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if not file:
            return
        self.cursor.execute("""
        SELECT projects.name, start_time, end_time, duration, note
        FROM entries JOIN projects ON entries.project_id = projects.id
        """)
        with open(file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Project", "Start", "End", "Duration (sec)", "Note"])
            writer.writerows(self.cursor.fetchall())
        messagebox.showinfo("Export", "CSV exported successfully")

    def on_close(self):
        self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()
