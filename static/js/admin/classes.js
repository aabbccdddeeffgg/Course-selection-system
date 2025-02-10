document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('add-class-form').addEventListener('submit', async function (e) {
        e.preventDefault();
        const courseId = document.getElementById('add-course-id').value;
        const teacherId = document.getElementById('add-teacher-id').value;
        const classTime = document.getElementById('add-class-time').value;
        try {
            const response = await fetch("/admin/add_class", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    course_id: courseId,
                    teacher_id: teacherId,
                    class_time: classTime
                })
            });
            const data = await response.json();
            alert(data.message);
            if (data.success) {
                location.reload();
            }
        } catch (error) {
            console.error('添加班级失败:', error);
            alert('添加班级失败，请稍后重试');
        }
    });


    // 展开学生列表
    document.querySelectorAll('.manage-students-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const classRow = this.closest('.class-row');
            const studentRow = classRow.nextElementSibling;
            const isVisible = studentRow.style.display === 'table-row';
            if (!isVisible) {
                const courseId = classRow.dataset.course;
                const teacherId = classRow.dataset.teacher;
                console.log('Course ID:', courseId, 'Teacher ID:', teacherId); // 添加日志输出
                try {
                    const response = await fetch("/admin/class_students", {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded'
                        },
                        body: `course_id=${courseId}&teacher_id=${teacherId}`
                    });
                    const data = await response.json();
                    const tbody = studentRow.querySelector('.students-body');
                    tbody.innerHTML = '';
                    if (data.students && data.students.length > 0) {
                        data.students.forEach(student => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${student[0]}</td>
                                <td>${student[1]}</td>
                                <td><input type="number" value="${student[2] || ''}" 
                                          onchange="updateGrade('${student[0]}', '${courseId}', this.value)"></td>
                                <td>
                                    <button class="delete-student-btn" 
                                            onclick="deleteStudent('${student[0]}', '${courseId}')">删除</button>
                                </td>
                            `;
                            tbody.appendChild(tr);
                        });
                    } else {
                        tbody.innerHTML = '<tr><td colspan="4">暂无学生信息</td></tr>';
                    }
                    studentRow.style.display = 'table-row';
                } catch (error) {
                    console.error('加载学生信息失败:', error);
                    alert('无法加载学生列表');
                }
            } else {
                studentRow.style.display = 'none';
            }
        });
    });

    // 编辑班级信息
    document.querySelectorAll('.edit-class-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const classRow = this.closest('.class-row');
            const courseId = classRow.dataset.course;
            const currentTeacherId = classRow.dataset.teacher;
            document.getElementById('editCourseId').value = courseId;
            document.getElementById('editTeacherId').value = currentTeacherId;
            document.getElementById('newClassTime').value = classRow.cells[4].textContent;

            try {
                const response = await fetch("/admin/get_teachers_by_course", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({course_id: courseId})
                });
                const data = await response.json();
                const selectElement = document.getElementById('newTeacherId');
                selectElement.innerHTML = '';
                data.teachers.forEach(teacher => {
                    const option = document.createElement('option');
                    option.value = teacher[0];
                    option.textContent = teacher[1];
                    if (teacher[0] === currentTeacherId) {
                        option.selected = true;
                    }
                    selectElement.appendChild(option);
                });
                document.getElementById('editClassModal').style.display = 'block';
            } catch (error) {
                console.error('获取教师信息失败:', error);
                alert('无法加载教师列表');
            }
        });
    });

    // 编辑班级表单提交
    document.getElementById('editClassForm').addEventListener('submit', async function (e) {
        e.preventDefault();
        const oldCourseId = document.getElementById('editCourseId').value;
        const oldTeacherId = document.getElementById('editTeacherId').value;
        const newTeacherId = document.getElementById('newTeacherId').value;
        const newClassTime = document.getElementById('newClassTime').value;
        try {
            const response = await fetch("/admin/update_class", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    old_course_id: oldCourseId,
                    old_teacher_id: oldTeacherId,
                    new_teacher_id: newTeacherId,
                    new_class_time: newClassTime
                })
            });
            const data = await response.json();
            alert(data.message);
            if (data.success) {
                location.reload();
            }
        } catch (error) {
            console.error('更新班级信息失败:', error);
            alert('更新班级信息失败，请稍后重试');
        }
    });

    // 添加学生功能
    document.querySelectorAll('.add-student-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const classRow = this.closest('.student-list').previousElementSibling;
            document.getElementById('addCourseId').value = classRow.dataset.course;
            document.getElementById('addTeacherId').value = classRow.dataset.teacher;
            document.getElementById('addStudentModal').style.display = 'block';
        });
    });

    // 添加学生表单提交
    document.getElementById('addStudentForm').addEventListener('submit', async function (e) {
        e.preventDefault();
        const studentId = document.getElementById('newStudentId').value;
        const courseId = document.getElementById('addCourseId').value;
        const teacherId = document.getElementById('addTeacherId').value;
        try {
            const response = await fetch("/admin/add_student", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    student_id: studentId,
                    course_id: courseId,
                    teacher_id: teacherId
                })
            });
            const data = await response.json();
            alert(data.message);
            if (data.success) {
                location.reload();
            }
        } catch (error) {
            console.error('添加学生失败:', error);
            alert('添加学生失败，请稍后重试');
        }
    });

    // 更新成绩
    window.updateGrade = async function (studentId, courseId, newGrade) {
        try {
            const response = await fetch("/admin/update_grade", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    student_id: studentId,
                    course_id: courseId,
                    new_grade: newGrade
                })
            });
            const data = await response.json();
            alert(data.message);
        } catch (error) {
            console.error('更新成绩失败:', error);
            alert('更新成绩失败，请稍后重试');
        }
    };

    // 删除学生
    window.deleteStudent = async function (studentId, courseId) {
        if (!confirm(`确定要删除学生 ${studentId} 的选课记录吗？`)) return;
        try {
            const response = await fetch("/admin/delete_student", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    student_id: studentId,
                    course_id: courseId
                })
            });
            const data = await response.json();
            if (data.success) {
                location.reload();
            } else {
                alert(data.message);
            }
        } catch (error) {
            console.error('删除学生失败:', error);
            alert('删除学生失败，请稍后重试');
        }
    };

    // 关闭编辑班级模态框
    document.getElementById('closeEditModal').addEventListener('click', function () {
        document.getElementById('editClassModal').style.display = 'none';
    });

    // 关闭添加学生模态框
    document.getElementById('closeAddStudentModal').addEventListener('click', function () {
        document.getElementById('addStudentModal').style.display = 'none';
    });
});