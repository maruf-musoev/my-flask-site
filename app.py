import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_babel import Babel
import os

# ИСПРАВЛЕНО: Добавлены подчеркивания __name__
app = Flask(__name__) 
app.secret_key = 'maruf_secret_key'

# --- ЯЗЫК ---
def get_locale():
    return 'ru'
babel = Babel(app, locale_selector=get_locale)

# --- БАЗА ДАННЫХ ---
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
    ans_correct = db.Column(db.Text, nullable=False) # Изменено на Text для длинных ответов
    opt_a = db.Column(db.String(200))
    opt_b = db.Column(db.String(200))
    opt_c = db.Column(db.String(200))
    opt_d = db.Column(db.String(200))
    # ДОБАВЛЕНО: Поле для типа вопроса (single, multi, match)
    q_type = db.Column(db.String(20), default='single')

# --- АДМИНКА ---
class MyAdminView(ModelView):
    column_labels = {
        'username': 'Имя пользователя', 'password': 'Пароль',
        'subject': 'Предмет', 'q_text': 'Текст вопроса',
        'ans_correct': 'Верный ответ',
        'opt_a': 'Вариант A', 'opt_b': 'Вариант B',
        'opt_c': 'Вариант C', 'opt_d': 'Вариант D',
        'q_type': 'Тип вопроса'
    }
    def is_accessible(self):
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

# --- МАРШРУТЫ ---
@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    unique_subjects = db.session.query(Question.subject.distinct()).all()
    subjects = [s[0] for s in unique_subjects]
    return render_template('index.html', username=session['user'], subjects=subjects)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session['user'] = u
            return redirect(url_for('index'))
        flash("Ошибка входа")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        if not User.query.filter_by(username=u).first():
            db.session.add(User(username=u, password=p))
            db.session.commit()
            session['user'] = u
            return redirect(url_for('index'))
        flash("Логин занят")
    return render_template('register.html')
import random # ОБЯЗАТЕЛЬНО проверь, что эта строка есть в самом верху файла!

@app.route('/quiz/<subject>', methods=['GET', 'POST'])
def quiz(subject):
    if 'user' not in session: return redirect(url_for('login'))
    
    search_subject = subject.strip()
    db_qs = db.session.query(Question).filter(Question.subject.ilike(search_subject)).all()
    
    # ПРЕОБРАЗУЕМ В СПИСОК И ПЕРЕМЕШИВАЕМ ВОПРОСЫ
    questions_list = list(db_qs)
    random.shuffle(questions_list)
    
    # ПОДГОТОВКА ВОПРОСОВ ДЛЯ ШАБЛОНА
    questions_to_render = []
    for q in questions_list:
        # Собираем варианты ответов в список кортежей
        opts = [
            ('A', q.opt_a), ('B', q.opt_b), 
            ('C', q.opt_c), ('D', q.opt_d)
        ]
        
        # Запоминаем текущую правильную букву из базы
        correct_ans = str(q.ans_correct).strip()
        
        # Если это обычный тест (single), перемешиваем варианты ответов
        if q.q_type == 'single':
            # Находим текст правильного ответа
            correct_text = ""
            if correct_ans == 'A': correct_text = q.opt_a
            elif correct_ans == 'B': correct_text = q.opt_b
            elif correct_ans == 'C': correct_text = q.opt_c
            elif correct_ans == 'D': correct_text = q.opt_d
            
            # Перемешиваем сами варианты
            random.shuffle(opts)
            
            # Находим, под какой буквой теперь текст правильного ответа
            for i, opt in enumerate(opts):
                if opt[1] == correct_text:
                    correct_ans = chr(65 + i) # Новая буква (A, B, C или D)
        
        # Формируем словарь для передачи в quiz.html
        questions_to_render.append({
            'id': q.id,
            'q': q.q_text,
            'a': correct_ans,
            'type': q.q_type,
            'options': {chr(65 + i): opt[1] for i, opt in enumerate(opts)}
        })

    results, score = None, 0
    if request.method == 'POST':
        results = {}
        # Используем данные из базы для проверки (db_qs), 
        # но сравниваем с логикой перемешанных ответов
        for q_data in questions_to_render:
            user_ans = ""
            q_id_str = str(q_data['id'])
            
            if q_data['type'] == 'match':
                ans_list = []
                for i in range(1, 6):
                    val = request.form.get(f"{q_id_str}_{i}")
                    if val: ans_list.append(f"{chr(64+i)}-{val}")
                user_ans = ", ".join(ans_list)
            elif q_data['type'] == 'multi':
                selected = request.form.getlist(q_id_str)
                user_ans = ", ".join(sorted(selected))
            else:
                user_ans = request.form.get(q_id_str) or ""

            # Считаем баллы (2 балла за вопрос)
            if user_ans.strip() == q_data['a']:
                score += 2
            
            results[q_data['id']] = {'user_ans': user_ans, 'correct_ans': q_data['a']}
    
    from urllib.parse import unquote
    clean_subject = unquote(subject)
    
    # САМОЕ ВАЖНОЕ: этот return должен быть СНАРУЖИ блока if request.method == 'POST'
    return render_template('quiz.html', 
                           questions=questions_to_render, 
                           results=results, 
                           score=score, 
                           subject=clean_subject)
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# КРИТИЧЕСКИЙ БЛОК ДЛЯ СОЗДАНИЯ ТАБЛИЦ
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="Maruf").first():
        db.session.add(User(username="Maruf", password="985453887"))
        db.session.commit()

# ИСПРАВЛЕНО: Добавлены подчеркивания __name__ == "__main__"
if __name__ == '__main__':
    app.run(debug=True)