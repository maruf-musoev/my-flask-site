from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_babel import Babel
import os

app = Flask(__name__)
app.secret_key = 'maruf_secret_key'

# --- НАСТРОЙКА ЯЗЫКА ---
def get_locale():
    return 'ru'

babel = Babel(app, locale_selector=get_locale)

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
# Используем твое название переменной из Vercel
database_url = os.environ.get('ХРАНИЛИЩЕ_URL') or os.environ.get('POSTGRES_URL')

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_system.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- МОДЕЛИ ---
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

# --- АДМИНКА ---
class MyAdminView(ModelView):
    column_labels = {
        'username': 'Имя пользователя', 'password': 'Пароль',
        'subject': 'Предмет', 'q_text': 'Текст вопроса',
        'ans_correct': 'Верный ответ',
        'opt_a': 'Вариант A', 'opt_b': 'Вариант B',
        'opt_c': 'Вариант C', 'opt_d': 'Вариант D'
    }
    def is_accessible(self):
        # Только ты (Maruf) можешь заходить в админку
        return session.get('user') == "Maruf"

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class MyHomeView(AdminIndexView):
    @expose('/')
    def index(self):
        if session.get('user') != "Maruf": return redirect(url_for('login'))
        return self.render('admin/index.html')

admin = Admin(app, name='Панель Маруфа', index_view=MyHomeView(name='Главная'))
admin.add_view(MyAdminView(User, db.session, name="Пользователи"))
admin.add_view(MyAdminView(Question, db.session, name="Вопросы тестов"))

# --- МАРШРУТЫ САЙТА ---

@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('index.html', username=session['user'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session['user'] = u
            return redirect(url_for('index'))
        flash("Неверный логин или пароль")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        if not User.query.filter_by(username=u).first():
            new_user = User(username=u, password=p)
            db.session.add(new_user)
            db.session.commit()
            session['user'] = u
            return redirect(url_for('index'))
        else:
            flash("Такой пользователь уже существует")
    return render_template('register.html')

@app.route('/quiz/<subject>', methods=['GET', 'POST'])
def quiz(subject):
    if 'user' not in session: return redirect(url_for('login'))
    db_qs = Question.query.filter_by(subject=subject).all()
    questions = [{'id': q.id, 'q': q.q_text, 'a': q.ans_correct, 
                  'options': {'A': q.opt_a, 'B': q.opt_b, 'C': q.opt_c, 'D': q.opt_d}} for q in db_qs]
    results, score = None, 0
    if request.method == 'POST':
        results = {}
        for q in questions:
            ans = request.form.get(str(q['id']))
            if ans == q['a']: score += 4
            results[q['id']] = {'user_ans': ans, 'correct_ans': q['a']}
    return render_template('quiz.html', questions=questions, results=results, score=score, subject=subject)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Авто-создание твоего админ-аккаунта
        if not User.query.filter_by(username="Maruf").first():
            db.session.add(User(username="Maruf", password="985453887"))
            db.session.commit()
    app.run(debug=True)