from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
import os

app = Flask(__name__)
app.secret_key = 'maruf_secret_key'
from flask_babel import Babel

# 1. Сначала создаем функцию
def get_locale():
    return 'ru'

# 2. Потом создаем объект babel и передаем ему эту функцию
babel = Babel(app, locale_selector=get_locale)
# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    q_text = db.Column(db.Text, nullable=False)
    ans_correct = db.Column(db.String(1), nullable=False)
    opt_a = db.Column(db.String(200))
    opt_b = db.Column(db.String(200))
    opt_c = db.Column(db.String(200))
    opt_d = db.Column(db.String(200))

# --- ПОЛНАЯ РУСИФИКАЦИЯ И ЗАЩИТА ---
class MyAdminView(ModelView):
    # Перевод кнопок и надписей
    column_labels = {
        'username': 'Имя пользователя',
        'password': 'Пароль',
        'subject': 'Предмет (java, architecture...)',
        'q_text': 'Текст вопроса',
        'ans_correct': 'Правильный ответ (A, B, C или D)',
        'opt_a': 'Вариант A',
        'opt_b': 'Вариант B',
        'opt_c': 'Вариант C',
        'opt_d': 'Вариант D'
    }
    
    # Текст на кнопках
    create_modal = True
    edit_modal = True

    def is_accessible(self):
        return session.get('user') == "Maruf"

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

# Главная страница админки тоже на русском
class MyHomeView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('user') == "Maruf":
            return redirect(url_for('login'))
        return self.render('admin/index.html')

# --- ИНИЦИАЛИЗАЦИЯ ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="Maruf").first():
        admin_user = User(username="Maruf", password="985453887")
        db.session.add(admin_user)
        db.session.commit()

# Создаем админку
admin = Admin(app, name='Панель Маруфа', index_view=MyHomeView(name='Главная'))
admin.add_view(MyAdminView(User, db.session, name="Пользователи"))
admin.add_view(MyAdminView(Question, db.session, name="Вопросы тестов"))

# --- МАРШРУТЫ ---
@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('index.html', username=session['user'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session['user'] = u
            return redirect(url_for('index'))
        error = "Неверный логин или пароль!"
    return render_template('login.html', error=error)

@app.route('/quiz/<subject>', methods=['GET', 'POST'])
def quiz(subject):
    if 'user' not in session: return redirect(url_for('login'))
    db_questions = Question.query.filter_by(subject=subject).all()
    questions = [{'id': q.id, 'q': q.q_text, 'a': q.ans_correct, 
                  'options': {'A': q.opt_a, 'B': q.opt_b, 'C': q.opt_c, 'D': q.opt_d}} for q in db_questions]
    
    results, score = None, 0
    if request.method == 'POST':
        results = {}
        for q in questions:
            user_ans = request.form.get(str(q['id']))
            if user_ans == q['a']: score += 4
            results[q['id']] = {'user_ans': user_ans, 'correct_ans': q['a']}
    return render_template('quiz.html', questions=questions, results=results, score=score, subject=subject)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)