from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from teacher_service import TeacherService
from db_connector import DatabaseConnector
import json
from io import BytesIO

app = Flask(__name__)

# 初始化数据库连接
db_connector = DatabaseConnector()
db_connector.connect(host="localhost", database="teacher_research_system", 
                    user="root", password="20050318")
teacher_service = TeacherService(db_connector)

@app.route('/')
def index():
    """首页 - 提供四个主要功能入口"""
    return render_template('index.html')

# ========== 论文相关路由 ==========
@app.route('/papers')
def papers_home():
    """论文管理首页"""
    return render_template('papers/index.html')

@app.route('/papers/add', methods=['GET', 'POST'])
def add_paper():
    """添加论文"""
    if request.method == 'POST':
        data = request.form
        authors = []
        
        # 解析作者数据
        for i in range(1, int(data['author_count']) + 1):
            teacher_id = data[f'author_{i}_id']
            rank = int(data[f'author_{i}_rank'])
            is_corresponding = f'author_{i}_corresponding' in data
            authors.append((teacher_id, rank, is_corresponding))
        
        # 调用服务层添加论文
        success, message = teacher_service.add_paper(
            paper_id=data['paper_id'],
            title=data['title'],
            journal=data['journal'],
            pub_year=int(data['pub_year']),
            paper_type=int(data['paper_type']),
            paper_level=int(data['paper_level']),
            authors=authors
        )
        
        if success:
            return redirect(url_for('papers_home'))
        else:
            return render_template('papers/add.html', error=message)
    
    return render_template('papers/add.html')

@app.route('/papers/delete', methods=['GET', 'POST'])
def delete_paper():
    """删除论文"""
    if request.method == 'POST':
        paper_id = request.form['paper_id']
        success, message = teacher_service.delete_paper(paper_id)
        
        if success:
            return redirect(url_for('papers_home'))
        else:
            return render_template('papers/delete.html', error=message)
    
    return render_template('papers/delete.html')

@app.route('/papers/update', methods=['GET', 'POST'])
def update_paper():
    """更新论文信息"""
    if request.method == 'POST':
        data = request.form
        updates = {}
        
        if data['title']: updates['title'] = data['title']
        if data['journal']: updates['journal'] = data['journal']
        if data['pub_year']: updates['year'] = int(data['pub_year'])
        if data['paper_type']: updates['paper_type'] = int(data['paper_type'])
        if data['paper_level']: updates['paper_level'] = int(data['paper_level'])
        
        success, message = teacher_service.update_paper(
            paper_id=data['paper_id'],
            **updates
        )
        
        if success:
            return redirect(url_for('papers_home'))
        else:
            return render_template('papers/update.html', error=message)
    
    return render_template('papers/update.html')

@app.route('/papers/query', methods=['GET', 'POST'])
def query_papers():
    """查询教师论文"""
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        start_year = int(request.form['start_year']) if request.form['start_year'] else None
        end_year = int(request.form['end_year']) if request.form['end_year'] else None
        
        success, result = teacher_service.get_teacher_papers(teacher_id, start_year, end_year)
        
        if success:
            return render_template('papers/query_result.html', papers=result)
        else:
            return render_template('papers/query.html', error=result)
    
    return render_template('papers/query.html')

@app.route('/papers/authors/add', methods=['GET', 'POST'])
def add_paper_author():
    """添加论文作者"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.add_paper_author(
            paper_id=data['paper_id'],
            teacher_id=data['teacher_id'],
            author_rank=int(data['author_rank']),
            is_corresponding='is_corresponding' in data
        )
        
        if success:
            return redirect(url_for('papers_home'))
        else:
            return render_template('papers/add_author.html', error=message)
    
    return render_template('papers/add_author.html')

@app.route('/papers/authors/delete', methods=['GET', 'POST'])
def delete_paper_author():
    """删除论文作者"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.delete_paper_author(
            paper_id=data['paper_id'],
            teacher_id=data['teacher_id']
        )
        
        if success:
            return redirect(url_for('papers_home'))
        else:
            return render_template('papers/delete_author.html', error=message)
    
    return render_template('papers/delete_author.html')

@app.route('/papers/authors/update_rank', methods=['GET', 'POST'])
def update_paper_author_rank():
    """更新论文作者排名"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.update_paper_author_rank(
            paper_id=data['paper_id'],
            teacher_id=data['teacher_id'],
            new_rank=int(data['new_rank'])
        )
        
        if success:
            return redirect(url_for('papers_home'))
        else:
            return render_template('papers/update_author_rank.html', error=message)
    
    return render_template('papers/update_author_rank.html')

@app.route('/papers/authors/list', methods=['GET', 'POST'])
def list_paper_authors():
    """查询论文所有作者"""
    if request.method == 'POST':
        paper_id = request.form['paper_id']
        success, result = teacher_service.get_paper_authors(paper_id)
        
        if success:
            return render_template('papers/author_list.html', authors=result)
        else:
            return render_template('papers/list_authors.html', error=result)
    
    return render_template('papers/list_authors.html')

# ========== 项目相关路由 ==========
@app.route('/projects')
def projects_home():
    """项目管理首页"""
    return render_template('projects/index.html')

@app.route('/projects/add', methods=['GET', 'POST'])
def add_project():
    """添加项目"""
    if request.method == 'POST':
        data = request.form
        participants = []
        
        # 解析参与者数据
        for i in range(1, int(data['participant_count']) + 1):
            teacher_id = data[f'participant_{i}_id']
            rank = int(data[f'participant_{i}_rank'])
            funding = float(data[f'participant_{i}_funding'])
            participants.append((teacher_id, rank, funding))
        
        # 调用服务层添加项目
        success, message = teacher_service.add_project(
            project_id=data['project_id'],
            name=data['project_name'],
            source=data['project_source'],
            project_type=int(data['project_type']),
            start_year=int(data['start_year']),
            end_year=int(data['end_year']),
            total_funding=float(data['total_funding']),
            participants=participants
        )
        
        if success:
            return redirect(url_for('projects_home'))
        else:
            return render_template('projects/add.html', error=message)
    
    return render_template('projects/add.html')

@app.route('/projects/delete', methods=['GET', 'POST'])
def delete_project():
    """删除项目"""
    if request.method == 'POST':
        project_id = request.form['project_id']
        success, message = teacher_service.delete_project(project_id)
        
        if success:
            return redirect(url_for('projects_home'))
        else:
            return render_template('projects/delete.html', error=message)
    
    return render_template('projects/delete.html')

@app.route('/projects/update', methods=['GET', 'POST'])
def update_project():
    """更新项目信息"""
    if request.method == 'POST':
        data = request.form
        updates = {}
        
        if data['project_name']: updates['project_name'] = data['project_name']
        if data['project_source']: updates['project_source'] = data['project_source']
        if data['project_type']: updates['project_type'] = int(data['project_type'])
        if data['start_year']: updates['start_year'] = int(data['start_year'])
        if data['end_year']: updates['end_year'] = int(data['end_year'])
        
        success, message = teacher_service.update_project(
            project_id=data['project_id'],
            **updates
        )
        
        if success:
            return redirect(url_for('projects_home'))
        else:
            return render_template('projects/update.html', error=message)
    
    return render_template('projects/update.html')

@app.route('/projects/query', methods=['GET', 'POST'])
def query_projects():
    """查询教师项目"""
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        start_year = int(request.form['start_year']) if request.form['start_year'] else None
        end_year = int(request.form['end_year']) if request.form['end_year'] else None
        
        success, result = teacher_service.get_teacher_projects(teacher_id, start_year, end_year)
        
        if success:
            return render_template('projects/query_result.html', projects=result)
        else:
            return render_template('projects/query.html', error=result)
    
    return render_template('projects/query.html')

@app.route('/projects/participants/add', methods=['GET', 'POST'])
def add_project_participant():
    """添加项目参与者"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.add_project_participant(
            project_id=data['project_id'],
            teacher_id=data['teacher_id'],
            participant_rank=int(data['participant_rank']),
            funding=float(data['funding'])
        )
        
        if success:
            return redirect(url_for('projects_home'))
        else:
            return render_template('projects/add_participant.html', error=message)
    
    return render_template('projects/add_participant.html')

@app.route('/projects/participants/delete', methods=['GET', 'POST'])
def delete_project_participant():
    """删除项目参与者"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.delete_project_participant(
            project_id=data['project_id'],
            teacher_id=data['teacher_id']
        )
        
        if success:
            return redirect(url_for('projects_home'))
        else:
            return render_template('projects/delete_participant.html', error=message)
    
    return render_template('projects/delete_participant.html')

@app.route('/projects/participants/update_funding', methods=['GET', 'POST'])
def update_project_funding():
    """更新项目参与者经费"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.update_project_funding(
            project_id=data['project_id'],
            teacher_id=data['teacher_id'],
            new_funding=float(data['new_funding'])
        )
        
        if success:
            return redirect(url_for('projects_home'))
        else:
            return render_template('projects/update_funding.html', error=message)
    
    return render_template('projects/update_funding.html')

@app.route('/projects/participants/update_rank', methods=['GET', 'POST'])
def update_project_participant_rank():
    """更新项目参与者排名"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.update_project_participant_rank(
            project_id=data['project_id'],
            teacher_id=data['teacher_id'],
            new_rank=int(data['new_rank'])
        )
        
        if success:
            return redirect(url_for('projects_home'))
        else:
            return render_template('projects/update_participant_rank.html', error=message)
    
    return render_template('projects/update_participant_rank.html')

@app.route('/projects/participants/list', methods=['GET', 'POST'])
def list_project_participants():
    """查询项目所有参与者"""
    if request.method == 'POST':
        project_id = request.form['project_id']
        success, result = teacher_service.get_project_participants(project_id)
        
        if success:
            return render_template('projects/participant_list.html', participants=result)
        else:
            return render_template('projects/list_participants.html', error=result)
    
    return render_template('projects/list_participants.html')

# ========== 课程相关路由 ==========
@app.route('/courses')
def courses_home():
    """课程管理首页"""
    return render_template('courses/index.html')

@app.route('/courses/assign', methods=['GET', 'POST'])
def assign_course():
    """分配教学任务"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.assign_course_teaching(
            course_id=data['course_id'],
            teacher_id=data['teacher_id'],
            year=int(data['year']),
            semester=int(data['semester']),
            hours=int(data['hours'])
        )
        
        if success:
            return redirect(url_for('courses_home'))
        else:
            return render_template('courses/assign.html', error=message)
    
    return render_template('courses/assign.html')

@app.route('/courses/adjust', methods=['GET', 'POST'])
def adjust_course():
    """调整教学任务"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.adjust_course_teaching(
            course_id=data['course_id'],
            teacher_id_from=data['teacher_id_from'],
            teacher_id_to=data['teacher_id_to'],
            year=int(data['year']),
            semester=int(data['semester']),
            hours=int(data['hours'])
        )
        
        if success:
            return redirect(url_for('courses_home'))
        else:
            return render_template('courses/adjust.html', error=message)
    
    return render_template('courses/adjust.html')

@app.route('/courses/remove', methods=['GET', 'POST'])
def remove_course():
    """移除教学任务"""
    if request.method == 'POST':
        data = request.form
        success, message = teacher_service.remove_course_teaching(
            course_id=data['course_id'],
            teacher_id=data['teacher_id'],
            year=int(data['year']),
            semester=int(data['semester'])
        )
        
        if success:
            return redirect(url_for('courses_home'))
        else:
            return render_template('courses/remove.html', error=message)
    
    return render_template('courses/remove.html')

@app.route('/courses/query', methods=['GET', 'POST'])
def query_courses():
    """查询教师课程"""
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        start_year = int(request.form['start_year']) if request.form['start_year'] else None
        end_year = int(request.form['end_year']) if request.form['end_year'] else None
        
        success, result = teacher_service.get_teacher_courses(teacher_id, start_year, end_year)
        
        if success:
            return render_template('courses/query_result.html', courses=result)
        else:
            return render_template('courses/query.html', error=result)
    
    return render_template('courses/query.html')

# ========== 教师总览路由 ==========
@app.route('/overview', methods=['GET', 'POST'])
def teacher_overview():
    """教师教学科研总览"""
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        start_year = int(request.form['start_year']) if request.form['start_year'] else None
        end_year = int(request.form['end_year']) if request.form['end_year'] else None
        
        # 查询教师基本信息
        connection = db_connector.get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM teacher WHERE teacher_id = %s", (teacher_id,))
        teacher_info = cursor.fetchone()
        cursor.close()
        
        if not teacher_info:
            return render_template('overview.html', error="找不到指定的教师")
        
        # 转换枚举值为可读文本
        gender_map = {1: "男", 2: "女"}
        title_map = {
            1: "博士后", 2: "助教", 3: "讲师", 4: "副教授", 5: "特任教授",
            6: "教授", 7: "助理研究员", 8: "特任副研究员", 
            9: "副研究员", 10: "特任研究员", 11: "研究员"
        }
        
        teacher_info['gender_text'] = gender_map.get(teacher_info['gender'], "未知")
        teacher_info['title_text'] = title_map.get(teacher_info['title'], "未知")
        
        # 查询论文信息
        success_papers, papers = teacher_service.get_teacher_papers(teacher_id, start_year, end_year)
        
        # 查询项目信息
        success_projects, projects = teacher_service.get_teacher_projects(teacher_id, start_year, end_year)
        
        # 查询课程信息
        success_courses, courses = teacher_service.get_teacher_courses(teacher_id, start_year, end_year)
        
        return render_template('overview/result.html',
                             teacher=teacher_info,
                             papers=papers if success_papers else [],
                             projects=projects if success_projects else [],
                             courses=courses if success_courses else [],
                             error_papers=None if success_papers else papers,
                             error_projects=None if success_projects else projects,
                             error_courses=None if success_courses else courses)
    
    return render_template('overview/index.html')

if __name__ == '__main__':
    app.run(debug=True)