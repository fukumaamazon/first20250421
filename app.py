# from flask import Flask, render_template, request, redirect, flash, url_for
from flask import Flask, render_template, request, redirect, flash, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DB_PATH = os.path.join(os.path.dirname(__file__), 'cafe_management.db')

# ===== DB操作関数 =====
def insert_item(name, initial_stock):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO items (name, initial_stock) VALUES (?, ?)", (name, initial_stock))
    conn.commit()
    conn.close()

# ===== TOP画面のあれこれ =====
@app.route('/')
def index():
    return render_template('index.html')


# ===== 材料登録画面 =====
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        initial_stock = request.form['initial_stock']
        if not name or not initial_stock.isdigit():
            flash("有効な名前と在庫数を入力してください", "danger")
        else:
            insert_item(name, int(initial_stock))
            flash(f"「{name}」を初期在庫 {initial_stock} で登録しました！", "success")
            return redirect(url_for('items'))  # ← 一覧ページにリダイレクト
    return render_template('add_item.html')

# ===== 材料一覧表示 =====
@app.route('/items')
def items():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, initial_stock FROM items")
    items_list = c.fetchall()
    conn.close()
    return render_template('items.html', items=items_list)


# ===== 材料編集フォームと更新処理 =====
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        # フォームから送られたデータで更新
        name = request.form['name']
        initial_stock = request.form['initial_stock']

        if not name or not initial_stock.isdigit():
            flash("正しい名前と在庫数を入力してください。", "danger")
            return redirect(url_for('edit_item', item_id=item_id))

        c.execute("UPDATE items SET name = ?, initial_stock = ? WHERE id = ?",
                  (name, int(initial_stock), item_id))
        conn.commit()
        conn.close()

        flash("材料を更新しました。", "success")
        return redirect(url_for('items'))

    # GETリクエスト → 編集フォームを表示
    c.execute("SELECT id, name, initial_stock FROM items WHERE id = ?", (item_id,))
    item = c.fetchone()
    conn.close()

    if item is None:
        flash("指定された材料が見つかりません。", "danger")
        return redirect(url_for('items'))

    return render_template('edit_item.html', item=item)


# ===== 材料削除処理 =====
@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 対象の材料が存在するかチェック
    c.execute("SELECT id FROM items WHERE id = ?", (item_id,))
    item = c.fetchone()

    if item:
        c.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        flash("材料を削除しました。", "success")
    else:
        flash("指定された材料が見つかりませんでした。", "danger")

    conn.close()
    return redirect(url_for('items'))

# ===ここから下は入出庫履歴(logs)について===

from datetime import datetime

# ===== 入出庫履歴の登録画面と処理 =====
@app.route('/add_log', methods=['GET', 'POST'])
def add_log():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        item_id = request.form['item_id']
        change = request.form['change']
        note = request.form['note']

        if not item_id or not change.lstrip('-').isdigit():
            flash("正しい材料と入出庫数を入力してください。", "danger")
            return redirect(url_for('add_log'))

        # ✅ user_idを省略して登録するよう修正
        c.execute(
            "INSERT INTO logs (item_id, change, timestamp, note) VALUES (?, ?, ?, ?)",
            (int(item_id), int(change), datetime.now(), note)
        )
        conn.commit()
        conn.close()
        flash("入出庫履歴を登録しました。", "success")
        return redirect(url_for('items'))
    else:
        c.execute("SELECT id, name FROM items")
        items = c.fetchall()
        conn.close()
        return render_template('add_log.html', items=items)

# ======入出庫履歴(logs)の一覧表示======
@app.route('/logs')
def logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # logs.id を取得に追加！
    c.execute("""
        SELECT logs.id, logs.timestamp, items.name, logs.change, logs.note
        FROM logs
        JOIN items ON logs.item_id = items.id
        ORDER BY logs.timestamp DESC
    """)
    logs_list = c.fetchall()
    conn.close()

    return render_template('logs.html', logs=logs_list)

# ======入出庫履歴(logs)の編集機能======

@app.route('/edit_log/<int:log_id>', methods=['GET', 'POST'])
def edit_log(log_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        item_id = request.form['item_id']
        change = request.form['change']
        note = request.form['note']

        if not item_id or not change.lstrip('-').isdigit():
            flash("正しい材料と入出庫数を入力してください。", "danger")
            return redirect(url_for('edit_log', log_id=log_id))

        c.execute("""
            UPDATE logs
            SET item_id = ?, change = ?, note = ?
            WHERE id = ?
        """, (int(item_id), int(change), note, log_id))

        conn.commit()
        conn.close()
        flash("入出庫履歴を更新しました。", "success")
        return redirect(url_for('logs'))

    # GETリクエスト：対象のログを取得
    c.execute("SELECT id, item_id, change, note FROM logs WHERE id = ?", (log_id,))
    log = c.fetchone()

    c.execute("SELECT id, name FROM items")  # 材料一覧
    items = c.fetchall()
    conn.close()

    if log is None:
        flash("指定された履歴が見つかりません。", "danger")
        return redirect(url_for('logs'))

    return render_template('edit_log.html', log=log, items=items)

# ===== 入出庫履歴の削除処理 =====
@app.route('/delete_log/<int:log_id>')
def delete_log(log_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 削除前に対象が存在するか確認（任意）
    c.execute("SELECT id FROM logs WHERE id = ?", (log_id,))
    log = c.fetchone()

    if log:
        c.execute("DELETE FROM logs WHERE id = ?", (log_id,))
        conn.commit()
        flash("入出庫履歴を削除しました。", "success")
    else:
        flash("指定された履歴が見つかりませんでした。", "danger")

    conn.close()
    return redirect(url_for('logs'))

# パスワードを安全に保存するため
# 変更前（現在）
# from werkzeug.security import generate_password_hash

# 変更後（修正）
from werkzeug.security import generate_password_hash, check_password_hash


# ===== ユーザー登録画面と処理（強化版） =====
@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = 'user'  # 必要に応じて 'admin' などに変更可

        if not username or not password:
            flash("ユーザー名とパスワードは必須です。", "danger")
            return redirect(url_for('register'))

        # すでに同名ユーザーがいるかチェック
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            flash("このユーザー名はすでに使われています。", "danger")
            conn.close()
            return redirect(url_for('register'))

        # パスワードをハッシュ化して保存
        password_hash = generate_password_hash(password)

        # ユーザー登録
        c.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role)
        )
        conn.commit()
        conn.close()

        flash("✅ 登録完了しました！", "success")
        return redirect(url_for('login'))

    conn.close()
    return render_template('register.html')

# ===== ユーザーログイン処理 =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            flash("ログインに成功しました。", "success")
            return redirect(url_for('index'))
        else:
            flash("ユーザー名またはパスワードが違います。", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

# ===== ログアウト処理 =====
@app.route('/logout')
def logout():
    session.clear()
    flash("ログアウトしました。", "info")
    return redirect(url_for('login'))

# ===== ユーザー一覧表示 =====
@app.route('/users')
def users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    users_list = c.fetchall()
    conn.close()
    return render_template('users.html', users=users_list)

# ===== ユーザー編集フォームと処理 =====
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']

        if not username:
            flash("ユーザー名は必須です。", "danger")
            return redirect(url_for('edit_user', user_id=user_id))

        c.execute("UPDATE users SET username = ?, role = ? WHERE id = ?", (username, role, user_id))
        conn.commit()
        conn.close()

        flash("ユーザー情報を更新しました。", "success")
        return redirect(url_for('users'))

    # GETの場合、編集フォームを表示
    c.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()

    if user is None:
        flash("ユーザーが見つかりません。", "danger")
        return redirect(url_for('users'))

    return render_template('edit_user.html', user=user)

# ===== ユーザー削除 =====
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ユーザーが存在するか確認
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()

    if user:
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash("ユーザーを削除しました。", "success")
    else:
        flash("ユーザーが見つかりませんでした。", "danger")

    conn.close()
    return redirect(url_for('users'))


# コードを追加するときはここから上へ
# ===== アプリ起動 =====
if __name__ == '__main__':
    # app.run(debug=True)
    app.run(debug=True, port=5050)