from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user


app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Teacher(User):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=False)
    subjects = db.relationship('Subject', backref='teacher', lazy=True)

class Student(User):
    __tablename__ = 'students'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    students = db.relationship('Student', backref='class', lazy=True)
    subjects = db.relationship('Subject', backref='class', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.Integer, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(300), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/director')
@login_required
def director_page():
    if current_user.role != 'Director':
        return redirect(url_for('index'))
    classes = Class.query.all()
    teachers = Teacher.query.all()
    selected_class = request.args.get('class_id')
    class_info = None
    if selected_class:
        class_info = Class.query.get(selected_class)
    return render_template('director.html', director=current_user, classes=classes, teachers=teachers, class_info=class_info)

@app.route('/teacher')
@login_required
def teacher_page():
    if current_user.role != 'Teacher':
        return redirect(url_for('index'))
    
    teacher = Teacher.query.filter_by(id=current_user.id).first()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    
    classes = {}
    student_grades = {}
    
    for subject in subjects:
        if subject.class_id not in classes:
            classes[subject.class_id] = {
                'class': Class.query.get(subject.class_id),
                'subjects': []
            }
        classes[subject.class_id]['subjects'].append(subject)
    
        # Collect grades for each student in each subject
        for student in classes[subject.class_id]['class'].students:
            if student.id not in student_grades:
                student_grades[student.id] = {}
            grades = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).all()
            student_grades[student.id][subject.id] = grades
            print(f"Grades for student {student.id} in subject {subject.id}: {[grade.grade for grade in grades]}")
    
    students = Student.query.all()
    
    return render_template('teacher.html', teacher=teacher, classes=classes, student_grades=student_grades, students=students, subjects=subjects)

@app.route('/student')
@login_required
def student_page():
    if current_user.role != 'Student':
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(id=current_user.id).first()
    subjects = Subject.query.filter_by(class_id=student.class_id).all()
    
    student_grades = {}
    homeworks = {}
    
    for subject in subjects:
        grades = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).all()
        student_grades[subject.id] = grades
        homework = Homework.query.filter_by(subject_id=subject.id).all()
        homeworks[subject.id] = homework
    
    return render_template('student.html', student=student, subjects=subjects, student_grades=student_grades, homeworks=homeworks)

@app.route('/parent')
@login_required
def parent_page():
    if current_user.role != 'Parent':
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(id=current_user.id).first()
    
    if student is None:
        flash('Нет студента, связанного с этой учетной записью родителя')
        return redirect(url_for('index'))
    
    subjects = Subject.query.filter_by(class_id=student.class_id).all()
    
    student_grades = {}
    homeworks = {}
    
    for subject in subjects:
        grades = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).all()
        student_grades[subject.id] = grades
        homework = Homework.query.filter_by(subject_id=subject.id).all()
        homeworks[subject.id] = homework
    
    return render_template('parent.html', parent=current_user, student=student, subjects=subjects, student_grades=student_grades, homeworks=homeworks)

# Добавление функциональности для директора
@app.route('/add_teacher', methods=['POST'])
@login_required
def add_teacher():
    if current_user.role != 'Director':
        return redirect(url_for('index'))
    username = request.form['username']
    last_name = request.form['last_name']
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    new_teacher = Teacher(username=username, role='Teacher', last_name=last_name, first_name=first_name, middle_name=middle_name)
    db.session.add(new_teacher)
    db.session.commit()
    return redirect(url_for('director_page'))

@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    if current_user.role != 'Director':
        return redirect(url_for('index'))
    username = request.form['username']
    last_name = request.form['last_name']
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    class_id = request.form['class']
    new_student = Student(username=username, role='Student', last_name=last_name, first_name=first_name, middle_name=middle_name, class_id=class_id)
    db.session.add(new_student)
    db.session.commit()
    return redirect(url_for('director_page'))

@app.route('/add_class', methods=['POST'])
@login_required
def add_class():
    if current_user.role != 'Director':
        return redirect(url_for('index'))
    class_name = request.form['class']
    new_class = Class(name=class_name)
    db.session.add(new_class)
    db.session.commit()
    return redirect(url_for('director_page'))

@app.route('/add_subject', methods=['POST'])
@login_required
def add_subject():
    if current_user.role != 'Director':
        return redirect(url_for('index'))
    subject_name = request.form['name']
    class_id = request.form['class_id']
    teacher_id = request.form['teacher_id']
    new_subject = Subject(name=subject_name, class_id=class_id, teacher_id=teacher_id)
    db.session.add(new_subject)
    db.session.commit()
    return redirect(url_for('director_page'))

# Добавление функциональности для учителя
@app.route('/assign_grade', methods=['POST'])
@login_required
def assign_grade():
    if current_user.role != 'Teacher':
        return redirect(url_for('index'))
    student_id = request.form['student_id']
    grade_value = request.form['grade']
    subject_id = request.form['subject_id']

    try:
        grade_value = int(grade_value)
    except ValueError:
        flash('Оценка должна быть целым числом')
        return redirect(url_for('teacher_page'))

    grade = Grade(grade=grade_value, student_id=student_id, subject_id=subject_id)
    db.session.add(grade)
    db.session.commit()
    return redirect(url_for('teacher_page'))

@app.route('/assign_homework', methods=['POST'])
@login_required
def assign_homework():
    if current_user.role != 'Teacher':
        return redirect(url_for('index'))
    subject_id = request.form['subject_id']
    homework_desc = request.form['homework']
    homework = Homework(description=homework_desc, subject_id=subject_id)
    db.session.add(homework)
    db.session.commit()
    return redirect(url_for('teacher_page'))

def init_db():
    db.create_all()
    
    # Проверяем наличие тестовых данных перед добавлением
    if not User.query.filter_by(username='director').first():
        director = User(username='director', role='Director')
        db.session.add(director)
    
    if not Teacher.query.filter_by(username='teacher').first():
        teacher = Teacher(username='teacher', role='Teacher', last_name='TeacherLast', first_name='TeacherFirst', middle_name='TeacherMiddle')
        db.session.add(teacher)
    
    if not Student.query.filter_by(username='student').first():
        student = Student(username='student', role='Student', last_name='StudentLast', first_name='StudentFirst', middle_name='StudentMiddle')
        db.session.add(student)
    
    if not User.query.filter_by(username='parent').first():
        parent = User(username='parent', role='Parent')
        db.session.add(parent)
    
    db.session.commit()

    # Создание класса и добавление студента в класс
    student = Student.query.filter_by(username='student').first()
    teacher = Teacher.query.filter_by(username='teacher').first()

    school_class = Class.query.filter_by(name='Class 1A').first()
    if not school_class:
        school_class = Class(name='Class 1A')
        db.session.add(school_class)
        db.session.commit()

    if student and school_class:
        student.class_id = school_class.id
        db.session.commit()

    # Создание предмета и назначение учителя
    if not Subject.query.filter_by(name='Math', class_id=school_class.id).first():
        subject = Subject(name='Math', class_id=school_class.id, teacher_id=teacher.id)
        db.session.add(subject)
        db.session.commit()

    # Назначение оценки и домашнего задания
    subject = Subject.query.filter_by(name='Math', class_id=school_class.id).first()
    if subject:
        if not Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first():
            grade = Grade(grade=5, student_id=student.id, subject_id=subject.id)
            db.session.add(grade)
        
        if not Homework.query.filter_by(description='Math homework', subject_id=subject.id).first():
            homework = Homework(description='Math homework', subject_id=subject.id)
            db.session.add(homework)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
