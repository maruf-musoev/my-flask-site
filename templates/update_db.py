from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Добавляем колонку q_type
        db.session.execute(text("ALTER TABLE question ADD COLUMN q_type VARCHAR(20) DEFAULT 'single'"))
        db.session.commit()
        print("🔥 Красава, Маруф! База успешно обновлена!")
    except Exception as e:
        db.session.rollback()
        print(f"Заметка: {e}")
        print("Скорее всего, колонка уже добавлена. Можешь проверять сайт!")