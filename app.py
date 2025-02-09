from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
import bcrypt  # 导入 bcrypt 库

app = Flask(__name__,template_folder='templates')
app.secret_key = "123456"  # 用于管理 session

# 数据库配置
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'xk_system'

mysql = MySQL(app)

# 密码加密函数
def hash_password(password):
    # 生成盐值并哈希密码
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

# 密码验证函数
def verify_password(stored_password, input_password):
    # 验证输入的密码是否与存储的哈希密码匹配
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_password.encode('utf-8'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ID = request.form['ID']
        password = request.form['password']

        # 查询数据库验证用户名是否存在
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT ID, username, password FROM user WHERE ID = %s", (ID,))
        user = cursor.fetchone()

        if not user:
            # 如果用户名不存在，提示用户
            flash("用户名不存在，请检查后重试！", "error")
        else:
            # 验证密码是否正确
            if verify_password(user[2], password):  # user[2] 是存储的哈希密码
                # 登录成功，根据 ID 的首字母判断角色
                first_letter = user[0][0].upper()  # 获取 ID 的首字母并转为大写
                if first_letter == 'S':
                    session['role'] = 'student'
                elif first_letter == 'T':
                    session['role'] = 'teacher'
                elif first_letter == 'A':
                    session['role'] = 'admin'
                else:
                    flash("无效的用户角色！", "error")
                    return redirect(url_for('login'))

                session['ID'] = user[0]  # 存储用户 ID
                session['name'] = user[1]  # 存储用户姓名

                # 根据角色跳转到对应的页面
                return redirect(url_for(f'{session["role"]}_dashboard'))
            else:
                # 密码错误，提示用户
                flash("密码错误，请检查后重试！", "error")

    return render_template('auth/login.html')



@app.route('/student')
def student_dashboard():
    if session.get('role') == 'student':
        return redirect(url_for('student_courses'))  # 重定向到 student_courses 视图函数
    else:
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))


# app.py
# app.py
from flask import jsonify

@app.route('/student/course', methods=['GET', 'POST'])
def student_courses():
    if session.get('role') != 'student':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    # 获取当前页码，默认为1
    page = request.args.get('page', 1, type=int)
    per_page = 5  # 每页显示的记录数

    # 获取搜索参数
    semester = request.args.get('semester', '')
    course_id = request.args.get('course_id', '')
    course_name = request.args.get('course_name', '')
    teacher_id = request.args.get('teacher_id', '')
    teacher_name = request.args.get('teacher_name', '')
    credit = request.args.get('credit', '')
    class_time = request.args.get('class_time', '')

    # 构建查询条件
    conditions = []
    params = []

    if semester:
        conditions.append("c.semester LIKE %s")
        params.append(f'%{semester}%')
    if course_id:
        conditions.append("c.course_id LIKE %s")
        params.append(f'%{course_id}%')
    if course_name:
        conditions.append("c.course_name LIKE %s")
        params.append(f'%{course_name}%')
    if teacher_id:
        conditions.append("cl.teacher_id LIKE %s")
        params.append(f'%{teacher_id}%')
    if teacher_name:
        conditions.append("t.name LIKE %s")
        params.append(f'%{teacher_name}%')
    if credit:
        conditions.append("c.credit LIKE %s")
        params.append(f'%{credit}%')
    if class_time:
        conditions.append("cl.class_time LIKE %s")
        params.append(f'%{class_time}%')

    base_query = """
        SELECT c.semester, c.course_id, c.course_name, cl.teacher_id, t.name AS teacher_name, c.credit, cl.class_time
        FROM course c
        JOIN class cl ON c.course_id = cl.course_id
        JOIN teacher t ON cl.teacher_id = t.teacher_id
    """

    if conditions:
        query = f"{base_query} WHERE {' AND '.join(conditions)} LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
    else:
        query = f"{base_query} LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])

    # 从数据库中获取课程信息
    cursor = mysql.connection.cursor()
    cursor.execute(query, params)
    courses = cursor.fetchall()

    # 获取总记录数
    if conditions:
        count_query = f"SELECT COUNT(*) FROM course c JOIN class cl ON c.course_id = cl.course_id JOIN teacher t ON cl.teacher_id = t.teacher_id WHERE {' AND '.join(conditions)}"
        cursor.execute(count_query, params[:-2])
    else:
        cursor.execute("SELECT COUNT(*) FROM class")
    total_count = cursor.fetchone()[0]
    cursor.close()

    # 计算总页数
    total_pages = (total_count // per_page) + 1

    # 处理选课请求
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        student_id = session.get('ID')  # 从 session 中获取学号
        teacher_id = request.form.get('teacher_id')
        # 检查是否已经选过该课程
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM course_selection WHERE student_id = %s AND course_id = %s", (student_id, course_id))
        enrollment = cursor.fetchone()
        cursor.close()

        if enrollment:
            return jsonify({'success': False, 'message': '您已经选过该课程，选课失败！'})
        else:
            # 插入选课记录到数据库，成绩置为空
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO course_selection (student_id, course_id, grade, teacher_id) VALUES (%s, %s, NULL, %s)", (student_id, course_id, teacher_id))
            mysql.connection.commit()
            cursor.close()
            return jsonify({'success': True, 'message': '选课成功！'})

    return render_template('student/course.html', courses=courses, page=page, total_pages=total_pages, semester=semester, course_id=course_id, course_name=course_name, teacher_id=teacher_id, teacher_name=teacher_name, credit=credit, class_time=class_time)


# app.py
# app.py
@app.route('/student/enrollments', methods=['GET', 'POST'])
def student_enrollments():
    if session.get('role') != 'student':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    student_id = session.get('ID')  # 从 session 中获取学号

    # 获取当前页码，默认为1
    page = request.args.get('page', 1, type=int)
    per_page = 5  # 每页显示的记录数

    # 获取搜索参数
    semester = request.args.get('semester', '')
    course_id = request.args.get('course_id', '')
    course_name = request.args.get('course_name', '')
    teacher_id = request.args.get('teacher_id', '')
    teacher_name = request.args.get('teacher_name', '')
    credit = request.args.get('credit', '')
    class_time = request.args.get('class_time', '')

    # 构建查询条件
    conditions = []
    params = []

    if semester:
        conditions.append("c.semester LIKE %s")
        params.append(f'%{semester}%')
    if course_id:
        conditions.append("c.course_id LIKE %s")
        params.append(f'%{course_id}%')
    if course_name:
        conditions.append("c.course_name LIKE %s")
        params.append(f'%{course_name}%')
    if teacher_id:
        conditions.append("t.teacher_id LIKE %s")
        params.append(f'%{teacher_id}%')
    if teacher_name:
        conditions.append("t.name LIKE %s")
        params.append(f'%{teacher_name}%')
    if credit:
        conditions.append("c.credit LIKE %s")
        params.append(f'%{credit}%')
    if class_time:
        conditions.append("cl.class_time LIKE %s")
        params.append(f'%{class_time}%')

    # 基础查询
    base_query = """
        SELECT c.semester, c.course_id, c.course_name, cs.teacher_id, t.name AS teacher_name, c.credit, cl.class_time
        FROM course_selection cs
        JOIN course c ON cs.course_id = c.course_id
        JOIN class cl ON cs.course_id = cl.course_id AND cs.teacher_id = cl.teacher_id
        JOIN teacher t ON cs.teacher_id = t.teacher_id
    """
    params.append(student_id)

    # 构建最终查询
    if conditions:
        query = f"{base_query} WHERE {' AND '.join(conditions)} AND cs.student_id = %s AND cs.grade IS NULL LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
    else:
        query = f"{base_query} WHERE cs.student_id = %s AND cs.grade IS NULL LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])

    # 执行查询
    cursor = mysql.connection.cursor()
    cursor.execute(query, params)
    courses = cursor.fetchall()

    # 计算总学分
    total_credits = sum(course[5] for course in courses)  # course[5] 是学分字段

    # 构建计数查询
    if conditions:
        count_query = f"SELECT COUNT(*) FROM course_selection cs JOIN course c ON cs.course_id = c.course_id JOIN class cl ON c.course_id = cl.course_id JOIN teacher t ON cs.teacher_id = t.teacher_id WHERE cs.student_id = %s AND cs.grade IS NULL AND {' AND '.join(conditions)}"
        params_count = [student_id] + params[:-3]  # 只包含查询参数，不包含分页参数
    else:
        count_query = f"SELECT COUNT(*) FROM course_selection cs JOIN course c ON cs.course_id = c.course_id JOIN class cl ON c.course_id = cl.course_id JOIN teacher t ON cs.teacher_id = t.teacher_id WHERE cs.student_id = %s AND cs.grade IS NULL"
        params_count = [student_id]

    # 执行计数查询
    cursor.execute(count_query, params_count)
    total_count = cursor.fetchone()[0]
    cursor.close()

    # 计算总页数
    total_pages = (total_count // per_page) + 1

    # 处理退课请求
    if request.method == 'POST':
        course_id = request.form.get('course_id')

        # 检查是否已经选过该课程
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM course_selection WHERE student_id = %s AND course_id = %s",
                       (student_id, course_id))
        enrollment = cursor.fetchone()

        if enrollment:
            # 删除选课记录
            cursor.execute("DELETE FROM course_selection WHERE student_id = %s AND course_id = %s",
                           (student_id, course_id))
            mysql.connection.commit()
            cursor.close()
            return jsonify({'success': True, 'message': '退课成功！'})
        else:
            cursor.close()
            return jsonify({'success': False, 'message': '您没有选过该课程，退课失败！'})

    return render_template('student/enrollments.html', courses=courses, page=page, total_pages=total_pages,
                           semester=semester, course_id=course_id, course_name=course_name, teacher_id=teacher_id,
                           teacher_name=teacher_name, credit=credit, class_time=class_time, total_credits=total_credits)

@app.route('/student/profile', methods=['GET', 'POST'])
def student_profile():
    if session.get('role') != 'student':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    student_id = session.get('ID')  # 从 session 中获取学号

    # 获取学生个人信息
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT name, student_id, gender, age, d.dept_name FROM student s JOIN department d ON s.dept_id = d.dept_id WHERE student_id = %s", (student_id,))
    student_info = cursor.fetchone()

    # 获取当前页码，默认为1
    page = request.args.get('page', 1, type=int)
    per_page = 5  # 每页显示的记录数

    # 获取搜索参数
    semester = request.args.get('semester', '')

    # 构建查询条件
    conditions = []
    params = [student_id]

    if semester:
        conditions.append("c.semester LIKE %s")
        params.append(f'{semester}')

    # 基础查询
    base_query = """
        SELECT c.semester, c.course_id, c.course_name, cs.grade, c.credit
        FROM course_selection cs
        JOIN course c ON cs.course_id = c.course_id
    """

    # 构建最终查询
    if conditions:
        query = f"{base_query} WHERE cs.student_id = %s AND {' AND '.join(conditions)} LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
    else:
        query = f"{base_query} WHERE cs.student_id = %s LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])

    # 执行查询
    cursor.execute(query, params)
    grades = cursor.fetchall()

    # 构建计数查询
    if conditions:
        count_query = f"SELECT COUNT(*) FROM course_selection cs JOIN course c ON cs.course_id = c.course_id WHERE cs.student_id = %s AND {' AND '.join(conditions)}"
        params_count = [student_id] + params[1:-2]  # 跳过 student_id，去掉分页参数
    else:
        count_query = f"SELECT COUNT(*) FROM course_selection cs JOIN course c ON cs.course_id = c.course_id WHERE cs.student_id = %s"
        params_count = [student_id]

    # 执行计数查询
    cursor.execute(count_query, params_count)
    total_count = cursor.fetchone()[0]
    cursor.close()

    # 计算总页数
    total_pages = (total_count // per_page) + 1

    # 计算加权平均成绩
    total_weighted_grades = 0
    total_credits = 0
    for grade in grades:
        if grade[3]:  # 如果成绩不为空
            total_weighted_grades += float(grade[3]) * float(grade[4])
            total_credits += float(grade[4])

    average_grade = total_weighted_grades / total_credits if total_credits > 0 else None

    return render_template('student/profile.html', student_info=student_info, grades=grades, page=page, total_pages=total_pages, semester=semester, average_grade=average_grade, overall_credicts=total_credits)

@app.route('/student/timetable', methods=['GET'])
def student_timetable():
    if session.get('role') != 'student':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    student_id = session.get('ID')  # 从 session 中获取学号
    cursor = mysql.connection.cursor()

    # 获取搜索的学期参数
    semester = request.args.get("semester", "").strip()

    # 初始化课表：12 行（第1～12节）、7 列（星期一～星期天）
    timetable = [["" for _ in range(7)] for _ in range(12)]

    if semester:
        # 根据学期查询该学生的课程安排
        cursor.execute(
            "SELECT course_name, class_time "
            "FROM class cl JOIN course c ON cl.course_id = c.course_id "
            "JOIN course_selection cs ON c.course_id = cs.course_id AND cl.teacher_id = cs.teacher_id "
            "WHERE cs.student_id = %s AND semester = %s",
            (student_id, semester)
        )
        courses = cursor.fetchall()
        # 定义星期对应顺序
        days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期天"]
        for course in courses:
            course_name = course[0]
            class_time = course[1]  # 格式如 "星期一1-4节"
            m = re.search(r"(星期[一二三四五六天])(\d+)-(\d+)节", class_time)
            if m:
                day_str = m.group(1)
                start_period = int(m.group(2))
                end_period = int(m.group(3))
                try:
                    col = days.index(day_str)
                except ValueError:
                    continue  # 若解析失败则跳过
                # 填入课程名称到对应的行
                for period in range(start_period, end_period + 1):
                    if 1 <= period <= 12:
                        timetable[period - 1][col] = course_name
    cursor.close()

    return render_template("student/timetable.html",
                           semester=semester,
                           timetable=timetable)

@app.route('/student/change_password', methods=['GET', 'POST'])
def student_change_password():
    if session.get('role') != 'student':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        student_id = session.get('ID')  # 从 session 中获取学号
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 验证新密码和确认新密码是否一致
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '新密码和确认新密码不一致，请重新输入！'})

        # 查询数据库验证旧密码是否正确
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT password FROM user WHERE ID = %s", (student_id,))
        user = cursor.fetchone()

        if not user or not verify_password(user[0], old_password):  # 验证旧密码
            cursor.close()
            return jsonify({'success': False, 'message': '旧密码不正确，请检查后重试！'})

        # 更新密码（加密新密码）
        hashed_new_password = hash_password(new_password)
        cursor.execute("UPDATE user SET password = %s WHERE ID = %s", (hashed_new_password, student_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'success': True, 'message': '密码修改成功！'})

    return render_template('student/change_password.html')


@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') == 'teacher':
        return redirect(url_for('teacher_courses'))
    else:
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))


@app.route('/teacher/course', methods=['GET', 'POST'])
def teacher_courses():
    # 权限检查：只有教师才能访问
    if session.get('role') != 'teacher':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 5  # 每页显示的记录数

    # 搜索参数（教师端只保留学期、课程名、学分和上课时间）
    semester   = request.args.get('semester', '')
    course_name = request.args.get('course_name', '')
    credit     = request.args.get('credit', '')
    class_time = request.args.get('class_time', '')

    # 获取当前教师的ID（假设登录后将教师ID存储在 session 中）
    teacher_id = session.get('ID')

    # 构建查询条件：首先限定只显示当前教师的课程
    conditions = ["cl.teacher_id = %s"]
    params = [teacher_id]

    if semester:
        conditions.append("c.semester LIKE %s")
        params.append(f'%{semester}%')
    if course_name:
        conditions.append("c.course_name LIKE %s")
        params.append(f'%{course_name}%')
    if credit:
        conditions.append("c.credit LIKE %s")
        params.append(f'%{credit}%')
    if class_time:
        conditions.append("cl.class_time LIKE %s")
        params.append(f'%{class_time}%')

    # 构建基础查询语句
    base_query = """
        SELECT c.semester, c.course_id, c.course_name, cl.teacher_id, t.name AS teacher_name, c.credit, cl.class_time
        FROM course c
        JOIN class cl ON c.course_id = cl.course_id
        JOIN teacher t ON cl.teacher_id = t.teacher_id
    """

    # 如果有搜索条件，则添加 WHERE 子句，并加入 LIMIT 和 OFFSET
    if conditions:
        query = f"{base_query} WHERE {' AND '.join(conditions)} LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
    else:
        query = f"{base_query} LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])

    # 执行查询
    cursor = mysql.connection.cursor()
    cursor.execute(query, params)
    courses = cursor.fetchall()

    # 获取总记录数以计算分页（注意这里不包含 LIMIT 和 OFFSET 参数）
    if conditions:
        count_query = f"""
            SELECT COUNT(*)
            FROM course c
            JOIN class cl ON c.course_id = cl.course_id
            JOIN teacher t ON cl.teacher_id = t.teacher_id
            WHERE {' AND '.join(conditions)}
        """
        # 去除 LIMIT 和 OFFSET 部分的参数（即最后两个参数）
        cursor.execute(count_query, params[:-2])
    else:
        cursor.execute("SELECT COUNT(*) FROM class")
    total_count = cursor.fetchone()[0]
    cursor.close()

    # 计算总页数
    total_pages = (total_count // per_page) + (1 if total_count % per_page > 0 else 0)

    return render_template(
        'teacher/course.html',
        courses=courses,
        page=page,
        total_pages=total_pages,
        semester=semester,
        course_name=course_name,
        credit=credit,
        class_time=class_time
    )
@app.route('/teacher/course/course_detail', methods=['GET'])
def course_detail():
    # 权限验证：仅允许教师访问
    if session.get('role') != 'teacher':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    # 获取请求参数中的课程号和教师号
    course_id = request.args.get('course_id')
    teacher_id = request.args.get('teacher_id')
    if not course_id or not teacher_id:
        flash("参数错误！", "error")
        return redirect(url_for('teacher_courses'))

    cursor = mysql.connection.cursor()

    # 查询当前课程的基本信息（学期、课程号、课程名、教师信息、学分、上课时间）
    course_query = """
        SELECT c.semester, c.course_id, c.course_name, cl.teacher_id, t.name AS teacher_name, c.credit, cl.class_time
        FROM course c
        JOIN class cl ON c.course_id = cl.course_id
        JOIN teacher t ON cl.teacher_id = t.teacher_id
        WHERE c.course_id = %s AND cl.teacher_id = %s
    """
    cursor.execute(course_query, (course_id, teacher_id))
    course = cursor.fetchone()
    if not course:
        flash("找不到该课程信息！", "error")
        return redirect(url_for('teacher_courses'))

    # 查询本课程中选课学生的学院分布情况
    dept_query = """
        SELECT d.dept_name, COUNT(*) as count
        FROM course_selection cs
        JOIN student s ON cs.student_id = s.student_id
        JOIN department d ON s.dept_id = d.dept_id
        WHERE cs.course_id = %s AND cs.teacher_id = %s
        GROUP BY d.dept_name
    """
    cursor.execute(dept_query, (course_id, teacher_id))
    dept_data = cursor.fetchall()
    # 将结果拆分为学院名称列表和对应的数量列表
    dept_labels = [row[0] for row in dept_data]
    dept_counts = [row[1] for row in dept_data]

    # 查询本课程中学生的平均总成绩分布情况
    # 计算每个学生在course_selection表中所有分数的平均值，然后统计选了本课程的学生的平均成绩落入四个区间的数量
    grade_query = """
        SELECT
            CASE 
                WHEN avg_grade < 60 THEN '不及格'
                WHEN avg_grade BETWEEN 60 AND 70 THEN '中'
                WHEN avg_grade BETWEEN 71 AND 85 THEN '良'
                WHEN avg_grade BETWEEN 86 AND 100 THEN '优'
            END as grade_category,
            COUNT(*) as count
        FROM (
            SELECT student_id, AVG(grade) as avg_grade
            FROM course_selection
            WHERE grade IS NOT NULL
            GROUP BY student_id
        ) AS t
        WHERE student_id IN (
            SELECT student_id FROM course_selection
            WHERE course_id = %s AND teacher_id = %s
        )
        GROUP BY grade_category
    """
    cursor.execute(grade_query, (course_id, teacher_id))
    grade_data = cursor.fetchall()
    # 将查询结果拆分为标签列表和数据列表
    grade_labels = []
    grade_counts = []
    for row in grade_data:
        grade_labels.append(row[0])
        grade_counts.append(row[1])
    cursor.close()

    # 为了确保四个区间都显示，即使某个区间没有数据也补0
    expected_grades = ['不及格', '中', '良', '优']
    grade_dict = {label: 0 for label in expected_grades}
    for label, count in zip(grade_labels, grade_counts):
        grade_dict[label] = count
    # 按照预设顺序返回
    grade_labels = list(grade_dict.keys())
    grade_counts = list(grade_dict.values())

    # 将课程信息及饼图数据传递给模板
    return render_template('teacher/course_detail.html',
                           course=course,
                           dept_labels=dept_labels,
                           dept_counts=dept_counts,
                           grade_labels=grade_labels,
                           grade_counts=grade_counts)



@app.route('/teacher/grade_submit', methods=['GET', 'POST'])
def grade_submit():
    # 权限校验：仅允许教师访问
    if session.get('role') != 'teacher':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    # 获取课程号与教师号（由前一页面传递）
    course_id = request.args.get('course_id')
    teacher_id = request.args.get('teacher_id')
    if not course_id or not teacher_id:
        flash("缺少必要参数！", "error")
        return redirect(url_for('teacher_courses'))
    #获取当前正在打分的课程名
    cursor = mysql.connection.cursor()
    query = """
        SELECT c.course_name
        FROM course c
        JOIN class cl ON c.course_id = cl.course_id
        WHERE c.course_id = %s AND cl.teacher_id = %s
    """
    cursor.execute(query, (course_id, teacher_id))
    result = cursor.fetchone()
    course_name = result[0] if result else ""
    cursor.close()

    # 获取当前页码，默认第一页
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示的记录数

    # 处理成绩提交（POST 请求）
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        for sid in student_ids:
            grade_input = request.form.get('grade_' + sid).strip()  # 获取输入并去掉首尾空白
            # 如果成绩输入为空，则将 grade 设为 None，这样会写入数据库的 NULL 值
            if grade_input == "":
                grade_value = None
            else:
                try:
                    grade_value = int(grade_input)
                except ValueError:
                    # 如果转换失败，你可以选择抛出异常或设为默认值
                    grade_value = None
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE course_selection SET grade = %s WHERE student_id = %s AND course_id = %s AND teacher_id = %s",
                (grade_value, sid, course_id, teacher_id)
            )
            mysql.connection.commit()
            cursor.close()
        flash("成绩提交成功！", "success")
        return redirect(url_for('grade_submit', course_id=course_id, teacher_id=teacher_id, page=page))

    # GET 请求：处理搜索条件
    search_student_id = request.args.get('student_id', '').strip()
    search_student_name = request.args.get('student_name', '').strip()

    # 构造查询语句
    base_query = """
        SELECT s.student_id, s.name, s.gender, d.dept_name, cs.grade
        FROM course_selection cs
        JOIN student s ON cs.student_id = s.student_id
        JOIN department d ON s.dept_id = d.dept_id
        JOIN course c ON cs.course_id = c.course_id
        WHERE cs.course_id = %s AND cs.teacher_id = %s
    """
    params = [course_id, teacher_id]
    if search_student_id:
        base_query += " AND s.student_id LIKE %s"
        params.append(f"%{search_student_id}%")
    if search_student_name:
        base_query += " AND s.name LIKE %s"
        params.append(f"%{search_student_name}%")

    # 统计总记录数以计算分页
    count_query = "SELECT COUNT(*) FROM (" + base_query + ") AS count_table"
    cursor = mysql.connection.cursor()
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    total_pages = (total_count // per_page) + (1 if total_count % per_page != 0 else 0)

    # 添加分页限制
    base_query += " LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])
    cursor.execute(base_query, params)
    students = cursor.fetchall()
    cursor.close()

    return render_template('teacher/grade_submit.html',
                           course_id=course_id,
                           teacher_id=teacher_id,
                           students=students,
                           course_name=course_name,
                           search_student_id=search_student_id,
                           search_student_name=search_student_name,
                           page=page,
                           total_pages=total_pages)




@app.route('/teacher/change_password', methods=['GET', 'POST'])
def teacher_change_password():
    if session.get('role') != 'teacher':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        teacher_id = session.get('ID')  # 从 session 中获取学号
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 验证新密码和确认新密码是否一致
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '新密码和确认新密码不一致，请重新输入！'})

        # 查询数据库验证旧密码是否正确
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT password FROM user WHERE ID = %s", (teacher_id,))
        user = cursor.fetchone()

        if not user or not verify_password(user[0], old_password):  # 验证旧密码
            cursor.close()
            return jsonify({'success': False, 'message': '旧密码不正确，请检查后重试！'})

        # 更新密码（加密新密码）
        hashed_new_password = hash_password(new_password)
        cursor.execute("UPDATE user SET password = %s WHERE ID = %s", (hashed_new_password, teacher_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'success': True, 'message': '密码修改成功！'})

    return render_template('teacher/change_password.html')


import re
from flask import render_template, request, session, redirect, flash, url_for


# 假设 mysql 已经初始化

@app.route('/teacher/profile', methods=['GET'])
def teacher_profile():
    # 权限校验
    if session.get('role') != 'teacher':
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))

    teacher_id = session.get("ID")
    cursor = mysql.connection.cursor()

    # 查询教师个人信息
    cursor.execute(
        "SELECT teacher_id, name, title, dept_name "
        "FROM teacher t JOIN department d ON t.dept_id = d.dept_id "
        "WHERE teacher_id = %s",
        (teacher_id,)
    )
    teacher_info = cursor.fetchone()  # 返回 (teacher_id, name, title, dept_name)

    # 获取搜索的学期参数
    semester = request.args.get("semester", "").strip()

    # 初始化课表：12 行（第1～12节）、7 列（星期一～星期天）
    timetable = [["" for _ in range(7)] for _ in range(12)]

    if semester:
        # 根据学期查询该教师的课程安排，假设 class 表中有 course_name、class_time、semester、teacher_id 等字段
        cursor.execute(
            "SELECT course_name, class_time "
            "FROM class cl JOIN course c ON cl.course_id = c.course_id "
            "WHERE teacher_id = %s AND semester = %s",
            (teacher_id, semester)
        )
        courses = cursor.fetchall()
        # 定义星期对应顺序（注意：有的系统可能用“星期日”，这里统一使用“星期天”）
        days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期天"]
        for course in courses:
            course_name = course[0]
            class_time = course[1]  # 格式如 "星期一1-4节"
            m = re.search(r"(星期[一二三四五六天])(\d+)-(\d+)节", class_time)
            if m:
                day_str = m.group(1)
                start_period = int(m.group(2))
                end_period = int(m.group(3))
                try:
                    col = days.index(day_str)
                except ValueError:
                    continue  # 若解析失败则跳过
                # 填入课程名称到对应的行（周期为 start_period 到 end_period，对应表格行 index 为 period-1）
                for period in range(start_period, end_period + 1):
                    if 1 <= period <= 12:
                        timetable[period - 1][col] = course_name
    cursor.close()

    return render_template("teacher/profile.html",
                           teacher_info=teacher_info,
                           semester=semester,
                           timetable=timetable)


@app.route('/admin')
def admin_dashboard():
    if session.get('role') == 'admin':
        return render_template('admin/dashboard.html')
    else:
        flash("您没有权限访问该页面！", "error")
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('role', None)
    session.pop('ID', None)
    flash("您已成功登出！", "success")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)