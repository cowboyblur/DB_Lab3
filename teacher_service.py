from db_connector import DatabaseConnector

class TeacherService:
    def __init__(self, db_connector):
        # 初始化函数，接收一个数据库连接器作为参数
        self.db = db_connector
    
    # ========== 论文相关操作 ==========
    def add_paper(self, paper_id, title, journal, pub_year, paper_type, paper_level, authors):
        """
        添加论文及作者信息
        authors格式: [(teacher_id, author_rank, is_corresponding), ...]
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 检查论文类型和级别是否有效
            if paper_type not in [1, 2, 3, 4] or paper_level not in range(1, 7):
                return False, "无效的论文类型或级别"
            
            # 检查是否有且只有一位通讯作者
            corresponding_authors = [a for a in authors if a[2]]
            if len(corresponding_authors) != 1:
                return False, "一篇论文必须有且只有一位通讯作者"
            
            # 检查作者排名是否唯一
            ranks = [a[1] for a in authors]
            if len(ranks) != len(set(ranks)):
                return False, "作者排名不能重复"
            max_rank = max(rank for _, rank, _ in authors)
            
            # 检查作者排名是否连续
            if max_rank != len(set(authors)):
                return False, "作者排名必须连续"
            
            # 插入论文信息
            cursor.execute(
                "INSERT INTO paper (paper_id, title, journal, pub_year, paper_type, paper_level) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (paper_id, title, journal, pub_year, paper_type, paper_level)
            )
            
            # 插入作者信息
            for teacher_id, rank, is_corresponding in authors:
                cursor.execute(
                    "INSERT INTO paper_author (paper_id, teacher_id, author_rank, is_corresponding) "
                    "VALUES (%s, %s, %s, %s)",
                    (paper_id, teacher_id, rank, is_corresponding)
                )
            
            connection.commit()
            return True, "论文添加成功"
        except Exception as e:
            connection.rollback()
            return False, f"添加论文失败: {str(e)}"
        finally:
            cursor.close()
    
    def update_paper(self, paper_id, title=None, journal=None, year=None, paper_type=None, paper_level=None):
        """更新论文基本信息"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 构建更新语句
            updates = []
            params = []
            if title is not None:
                updates.append("title = %s")
                params.append(title)
            if journal is not None:
                updates.append("journal = %s")
                params.append(journal)
            if year is not None:
                updates.append("pub_year = %s")
                params.append(year)
            if paper_type is not None:
                if paper_type not in [1, 2, 3, 4]:
                    return False, "无效的论文类型"
                updates.append("paper_type = %s")
                params.append(paper_type)
            if paper_level is not None:
                if paper_level not in range(1, 7):
                    return False, "无效的论文级别"
                updates.append("paper_level = %s")
                params.append(paper_level)
            
            if not updates:
                return False, "没有提供更新内容"
            
            params.append(paper_id)
            query = f"UPDATE paper SET {', '.join(updates)} WHERE paper_id = %s"
            cursor.execute(query, params)
            connection.commit()
            return True, "论文更新成功"
        except Exception as e:
            connection.rollback()
            return False, f"更新论文失败: {str(e)}"
        finally:
            cursor.close()
    
    def delete_paper(self, paper_id):
        """删除论文及其作者关联"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            cursor.execute("DELETE FROM paper WHERE paper_id = %s", (paper_id,))
            connection.commit()
            return True, "论文删除成功"
        except Exception as e:
            connection.rollback()
            return False, f"删除论文失败: {str(e)}"
        finally:
            cursor.close()
    
    def get_teacher_papers(self, teacher_id, start_year=None, end_year=None):
        """查询教师发表的论文及详细作者信息"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 查询论文基本信息及作者在该论文中的详细信息
            query = """
                SELECT 
                    p.paper_id,
                    p.title,
                    p.journal,
                    p.pub_year,
                    p.paper_type,
                    p.paper_level,
                    pa.author_rank,
                    pa.is_corresponding,
                    (SELECT COUNT(*) FROM paper_author WHERE paper_id = p.paper_id) AS author_count,
                    (SELECT GROUP_CONCAT(t.name ORDER BY pa2.author_rank SEPARATOR ', ') 
                     FROM paper_author pa2 
                     JOIN teacher t ON pa2.teacher_id = t.teacher_id 
                     WHERE pa2.paper_id = p.paper_id) AS all_authors
                FROM paper p
                JOIN paper_author pa ON p.paper_id = pa.paper_id
                WHERE pa.teacher_id = %s
            """
            params = [teacher_id]
            
            if start_year and end_year:
                query += " AND p.pub_year BETWEEN %s AND %s"
                params.extend([start_year, end_year])
            
            query += " ORDER BY p.pub_year DESC, pa.author_rank"
            
            cursor.execute(query, params)
            papers = cursor.fetchall()
            
            # 转换枚举值为可读文本
            paper_type_map = {1: "full paper", 2: "short paper", 3: "poster paper", 4: "demo paper"}
            paper_level_map = {
                1: "CCF-A", 2: "CCF-B", 3: "CCF-C", 
                4: "中文CCF-A", 5: "中文CCF-B", 6: "无级别"
            }
            
            for paper in papers:
                paper['paper_type_text'] = paper_type_map.get(paper['paper_type'], "未知类型")
                paper['paper_level_text'] = paper_level_map.get(paper['paper_level'], "未知级别")
                paper['is_corresponding_text'] = "是" if paper['is_corresponding'] else "否"
            
            return True, papers
        except Exception as e:
            return False, f"查询论文失败: {str(e)}"
        finally:
            cursor.close()

    def add_paper_author(self, paper_id, teacher_id, author_rank, is_corresponding):
        """添加论文作者关系，插入到指定排名，后续排名自动后移"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # 检查论文和教师是否存在
            cursor.execute("SELECT 1 FROM paper WHERE paper_id = %s", (paper_id,))
            if not cursor.fetchone():
                return False, "论文不存在"
            
            cursor.execute("SELECT 1 FROM teacher WHERE teacher_id = %s", (teacher_id,))
            if not cursor.fetchone():
                return False, "教师不存在"

            # 检查是否已经是作者
            cursor.execute(
                "SELECT 1 FROM paper_author WHERE paper_id = %s AND teacher_id = %s",
                (paper_id, teacher_id)
            )
            if cursor.fetchone():
                return False, "该教师已经是这篇论文的作者"

            # 检查通讯作者数量
            if is_corresponding:
                cursor.execute(
                    "SELECT COUNT(*) FROM paper_author WHERE paper_id = %s AND is_corresponding = TRUE",
                    (paper_id,)
                )
                if cursor.fetchone()[0] >= 1:
                    return False, "一篇论文最多只能有一位通讯作者"

            # 获取当前最大排名
            cursor.execute(
                "SELECT COALESCE(MAX(author_rank), 0) FROM paper_author WHERE paper_id = %s",
                (paper_id,)
            )
            max_rank = cursor.fetchone()[0]

            # 检查排名是否有效（必须>=1）
            if author_rank < 1 or author_rank > max_rank + 1:
                return False, "排名必须大于等于1并不大于总人数"

            # 如果插入位置在现有排名范围内，需要后移后续排名
            if author_rank <= max_rank:
                cursor.execute(
                    "UPDATE paper_author SET author_rank = author_rank + 1 "
                    "WHERE paper_id = %s AND author_rank >= %s",
                    (paper_id, author_rank)
                )

            # 插入新作者
            cursor.execute(
                "INSERT INTO paper_author (paper_id, teacher_id, author_rank, is_corresponding) "
                "VALUES (%s, %s, %s, %s)",
                (paper_id, teacher_id, author_rank, is_corresponding)
            )

            connection.commit()
            return True, "作者添加成功，排名已调整"
        except Exception as e:
            connection.rollback()
            return False, f"添加作者失败: {str(e)}"
        finally:
            cursor.close()

    def delete_paper_author(self, paper_id, teacher_id):
        """删除论文作者关系，并将后续排名前移"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # 获取被删除作者的排名
            cursor.execute(
                "SELECT author_rank FROM paper_author "
                "WHERE paper_id = %s AND teacher_id = %s",
                (paper_id, teacher_id)
            )
            result = cursor.fetchone()
            if not result:
                return False, "找不到指定的作者关系"

            deleted_rank = result[0]

            # 删除作者
            cursor.execute(
                "DELETE FROM paper_author WHERE paper_id = %s AND teacher_id = %s",
                (paper_id, teacher_id)
            )

            # 将后续排名前移
            cursor.execute(
                "UPDATE paper_author SET author_rank = author_rank - 1 "
                "WHERE paper_id = %s AND author_rank > %s",
                (paper_id, deleted_rank)
            )

            connection.commit()
            return True, "作者删除成功，排名已调整"
        except Exception as e:
            connection.rollback()
            return False, f"删除作者失败: {str(e)}"
        finally:
            cursor.close()

    def update_paper_author_rank(self, paper_id, teacher_id, new_rank):
        """更新作者排名，自动调整其他作者的排名"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # 获取当前排名
            cursor.execute(
                "SELECT author_rank FROM paper_author "
                "WHERE paper_id = %s AND teacher_id = %s",
                (paper_id, teacher_id)
            )
            result = cursor.fetchone()
            if not result:
                return False, "找不到指定的作者关系"

            current_rank = result[0]

            if current_rank == new_rank:
                return True, "排名未改变"

            # 获取当前最大排名
            cursor.execute(
                "SELECT COALESCE(MAX(author_rank), 0) FROM paper_author WHERE paper_id = %s",
                (paper_id,)
            )
            max_rank = cursor.fetchone()[0]

            if new_rank < 1 or new_rank > max_rank + 1:
                return False, f"新排名必须在1到{max_rank + 1}之间"

            # 临时将当前作者的排名设置为0（避免唯一约束冲突）
            cursor.execute(
                "UPDATE paper_author SET author_rank = 0 "
                "WHERE paper_id = %s AND teacher_id = %s",
                (paper_id, teacher_id)
            )

            # 调整其他作者的排名
            if new_rank > current_rank:
                # 排名后移（从current_rank+1到new_rank-1的排名减1）
                cursor.execute(
                    "UPDATE paper_author SET author_rank = author_rank - 1 "
                    "WHERE paper_id = %s AND author_rank > %s AND author_rank <= %s",
                    (paper_id, current_rank, new_rank - 1)
                )
            else:
                # 排名前移（从new_rank到current_rank-1的排名加1）
                cursor.execute(
                    "UPDATE paper_author SET author_rank = author_rank + 1 "
                    "WHERE paper_id = %s AND author_rank >= %s AND author_rank < %s",
                    (paper_id, new_rank, current_rank)
                )

            # 设置新排名
            cursor.execute(
                "UPDATE paper_author SET author_rank = %s "
                "WHERE paper_id = %s AND teacher_id = %s AND author_rank = 0",
                (new_rank, paper_id, teacher_id)
            )

            connection.commit()
            return True, "作者排名更新成功"
        except Exception as e:
            connection.rollback()
            return False, f"更新作者排名失败: {str(e)}"
        finally:
            cursor.close()
    
    def get_paper_authors(self, paper_id):
        """获取论文的所有作者信息（按排名排序）"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute(
                "SELECT pa.teacher_id, t.name, pa.author_rank, pa.is_corresponding "
                "FROM paper_author pa "
                "JOIN teacher t ON pa.teacher_id = t.teacher_id "
                "WHERE pa.paper_id = %s "
                "ORDER BY pa.author_rank",
                (paper_id,)
            )
            
            authors = cursor.fetchall()
            return True, authors
        except Exception as e:
            return False, f"查询论文作者失败: {str(e)}"
        finally:
            cursor.close()
    
    # ========== 项目相关操作 ==========
    def add_project(self, project_id, name, source, project_type, start_year, end_year, total_funding, participants):
        """
        添加项目及参与者信息
        participants格式: [(teacher_id, rank, funding), ...]
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 检查项目类型是否有效
            if project_type not in range(1, 6):
                return False, "无效的项目类型"
            
            # 检查参与者经费总和是否等于项目总经费
            total_participant_funding = sum(p[2] for p in participants)
            if abs(total_participant_funding - total_funding) > 0.01:  # 允许浮点误差
                return False, "参与者经费总和必须等于项目总经费"
            
            # 检查排名是否唯一
            ranks = [p[1] for p in participants]
            if len(ranks) != len(set(ranks)):
                return False, "参与者排名不能重复"
            
            # 检查排名是否连续
            max_rank = max(rank for _, rank, _ in participants)
            if max_rank != len(set(participants)):
                return False, "参与者排名必须连续"
            
            if start_year >= end_year:
                return False, "项目开始年份必须小于结束年份"
            
            # 插入项目信息
            cursor.execute(
                "INSERT INTO project (project_id, project_name, project_source, project_type, start_year, end_year, total_funding) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (project_id, name, source, project_type, start_year, end_year, total_funding)
            )
            
            # 插入参与者信息
            for teacher_id, rank, funding in participants:
                cursor.execute(
                    "INSERT INTO project_participant (project_id, teacher_id, participant_rank, funding) "
                    "VALUES (%s, %s, %s, %s)",
                    (project_id, teacher_id, rank, funding)
                )
            
            connection.commit()
            return True, "项目添加成功"
        except Exception as e:
            connection.rollback()
            return False, f"添加项目失败: {str(e)}"
        finally:
            cursor.close()
            

    def delete_project(self, project_id):
        """删除项目及其参与者关联"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            cursor.execute("DELETE FROM project WHERE project_id = %s", (project_id,))
            connection.commit()
            return True, "项目删除成功"
        except Exception as e:
            connection.rollback()
            return False, f"删除项目失败: {str(e)}"
        finally:
            cursor.close()

    def update_project(self, project_id, project_name=None, project_source=None, project_type=None, start_year=None, end_year=None):
        """更新项目基本信息"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 构建更新语句
            updates = []
            params = []
            if project_name is not None:
                updates.append("project_name = %s")
                params.append(project_name)
            if project_source is not None:
                updates.append("project_source = %s")
                params.append(project_source)
            if project_type is not None:
                if project_type not in [1, 2, 3, 4, 5]:
                    return False, "无效的论文类型"
                updates.append("project_type = %s")
                params.append(project_type)
            if start_year is not None:
                updates.append("start_year = %s")
                params.append(start_year)
            if end_year is not None:
                updates.append("end_year = %s")
                params.append(end_year)
            cursor.execute(
                "SELECT start_year, end_year FROM project "
                "WHERE project_id = %s",
                (project_id,)
            )
            result = cursor.fetchone()
            start_year_check = max(result[0], start_year) if start_year is not None else result[0]
            end_year_check = min(result[1], end_year) if end_year is not None else result[1]
            if start_year_check >= end_year_check:
                return False, "项目开始年份必须小于结束年份"
            if not updates:
                return False, "没有提供更新内容"
            
            params.append(project_id)
            query = f"UPDATE project SET {', '.join(updates)} WHERE project_id = %s"
            cursor.execute(query, params)
            connection.commit()
            return True, "项目更新成功"
        except Exception as e:
            connection.rollback()
            return False, f"更新项目失败: {str(e)}"
        finally:
            cursor.close()
    
    def get_teacher_projects(self, teacher_id, start_year=None, end_year=None):
        """查询教师参与的项目及详细参与信息"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 查询项目基本信息及教师在该项目中的详细信息
            query = """
                SELECT 
                    p.project_id,
                    p.project_name,
                    p.project_source,
                    p.project_type,
                    p.start_year,
                    p.end_year,
                    p.total_funding,
                    pp.participant_rank,
                    pp.funding,
                    pp.funding/p.total_funding*100 AS funding_percentage,
                    (SELECT COUNT(*) FROM project_participant WHERE project_id = p.project_id) AS participant_count,
                    (SELECT GROUP_CONCAT(t.name ORDER BY pp2.participant_rank SEPARATOR ', ') 
                     FROM project_participant pp2 
                     JOIN teacher t ON pp2.teacher_id = t.teacher_id 
                     WHERE pp2.project_id = p.project_id) AS all_participants
                FROM project p
                JOIN project_participant pp ON p.project_id = pp.project_id
                WHERE pp.teacher_id = %s
            """
            params = [teacher_id]
            
            if start_year and end_year:
                query += " AND (p.start_year <= %s AND p.end_year >= %s)"
                params.extend([end_year, start_year])
            
            query += " ORDER BY p.start_year DESC, pp.participant_rank"
            
            cursor.execute(query, params)
            projects = cursor.fetchall()
            
            # 转换枚举值为可读文本
            project_type_map = {
                1: "国家级项目", 2: "省部级项目", 3: "市厅级项目",
                4: "企业合作项目", 5: "其它类型项目"
            }
            
            for project in projects:
                project['project_type_text'] = project_type_map.get(project['project_type'], "未知类型")
                project['duration'] = f"{project['start_year']}-{project['end_year']}"
                project['funding_percentage'] = round(project['funding_percentage'], 2)
            
            return True, projects
        except Exception as e:
            return False, f"查询项目失败: {str(e)}"
        finally:
            cursor.close()
    
    def add_project_participant(self, project_id, teacher_id, participant_rank, funding):
        """添加项目参与者，插入到指定排名，后续排名自动后移，并更新项目总经费"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # 检查项目和教师是否存在
            cursor.execute("SELECT 1 FROM project WHERE project_id = %s", (project_id,))
            if not cursor.fetchone():
                return False, "项目不存在"
            
            cursor.execute("SELECT 1 FROM teacher WHERE teacher_id = %s", (teacher_id,))
            if not cursor.fetchone():
                return False, "教师不存在"

            # 检查是否已经是参与者
            cursor.execute(
                "SELECT 1 FROM project_participant WHERE project_id = %s AND teacher_id = %s",
                (project_id, teacher_id)
            )
            if cursor.fetchone():
                return False, "该教师已经是这个项目的参与者"
            # 获取当前最大排名和总经费
            cursor.execute(
                "SELECT COALESCE(MAX(participant_rank), 0), total_funding FROM project "
                "LEFT JOIN project_participant USING(project_id) "
                "WHERE project_id = %s GROUP BY project_id",
                (project_id,)
            )
            result = cursor.fetchone()
            max_rank = result[0]
            current_total_funding = result[1]

            # 检查排名是否有效（必须>=1）
            if participant_rank < 1 or participant_rank > max_rank + 1:
                return False, "排名必须大于等于1并不大于总人数"

            # 如果插入位置在现有排名范围内，需要后移后续排名
            if participant_rank <= max_rank:
                cursor.execute(
                    "UPDATE project_participant SET participant_rank = participant_rank + 1 "
                    "WHERE project_id = %s AND participant_rank >= %s",
                    (project_id, participant_rank)
                )

            # 插入新参与者
            cursor.execute(
                "INSERT INTO project_participant (project_id, teacher_id, participant_rank, funding) "
                "VALUES (%s, %s, %s, %s)",
                (project_id, teacher_id, participant_rank, funding)
            )

            # 更新项目总经费
            cursor.execute(
                "UPDATE project SET total_funding = total_funding + %s "
                "WHERE project_id = %s",
                (funding, project_id)
            )

            connection.commit()
            return True, "参与者添加成功，排名和总经费已调整"
        except Exception as e:
            connection.rollback()
            return False, f"添加参与者失败: {str(e)}"
        finally:
            cursor.close()

    def delete_project_participant(self, project_id, teacher_id):
        """删除项目参与者，并将后续排名前移，同时更新项目总经费"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # 获取被删除参与者的排名和经费
            cursor.execute(
                "SELECT participant_rank, funding FROM project_participant "
                "WHERE project_id = %s AND teacher_id = %s",
                (project_id, teacher_id)
            )
            result = cursor.fetchone()
            if not result:
                return False, "找不到指定的参与者关系"

            deleted_rank = result[0]
            deleted_funding = result[1]

            # 删除参与者
            cursor.execute(
                "DELETE FROM project_participant WHERE project_id = %s AND teacher_id = %s",
                (project_id, teacher_id)
            )

            # 将后续排名前移
            cursor.execute(
                "UPDATE project_participant SET participant_rank = participant_rank - 1 "
                "WHERE project_id = %s AND participant_rank > %s",
                (project_id, deleted_rank)
            )

            # 更新项目总经费
            cursor.execute(
                "UPDATE project SET total_funding = total_funding - %s "
                "WHERE project_id = %s",
                (deleted_funding, project_id)
            )

            connection.commit()
            return True, "参与者删除成功，排名和总经费已调整"
        except Exception as e:
            connection.rollback()
            return False, f"删除参与者失败: {str(e)}"
        finally:
            cursor.close()

    def update_project_funding(self, project_id, teacher_id, new_funding):
        """更新项目参与者经费，同时调整项目总经费"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 获取当前经费和项目总经费
            cursor.execute(
                "SELECT funding FROM project_participant "
                "WHERE project_id = %s AND teacher_id = %s",
                (project_id, teacher_id)
            )
            result = cursor.fetchone()
            if not result:
                return False, "找不到指定的项目参与者"
            
            old_funding = result[0]
            funding_diff = new_funding - old_funding
            
            # 更新参与者经费
            cursor.execute(
                "UPDATE project_participant SET funding = %s "
                "WHERE project_id = %s AND teacher_id = %s",
                (new_funding, project_id, teacher_id)
            )
            
            # 更新项目总经费
            cursor.execute(
                "UPDATE project SET total_funding = total_funding + %s "
                "WHERE project_id = %s",
                (funding_diff, project_id)
            )
            
            connection.commit()
            return True, "项目经费更新成功"
        except Exception as e:
            connection.rollback()
            return False, f"更新项目经费失败: {str(e)}"
        finally:
            cursor.close()

    def update_project_participant_rank(self, project_id, teacher_id, new_rank):
        """更新参与者排名，自动调整其他参与者的排名"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # 获取当前排名
            cursor.execute(
                "SELECT participant_rank FROM project_participant "
                "WHERE project_id = %s AND teacher_id = %s",
                (project_id, teacher_id)
            )
            result = cursor.fetchone()
            if not result:
                return False, "找不到指定的参与者关系"

            current_rank = result[0]

            if current_rank == new_rank:
                return True, "排名未改变"

            # 获取当前最大排名
            cursor.execute(
                "SELECT COALESCE(MAX(participant_rank), 0) FROM project_participant "
                "WHERE project_id = %s",
                (project_id,)
            )
            max_rank = cursor.fetchone()[0]

            if new_rank < 1 or new_rank > max_rank:
                return False, f"新排名必须在1到{max_rank}之间"

            # 临时将当前参与者的排名设置为0（避免唯一约束冲突）
            cursor.execute(
                "UPDATE project_participant SET participant_rank = 0 "
                "WHERE project_id = %s AND teacher_id = %s",
                (project_id, teacher_id)
            )

            # 调整其他参与者的排名
            if new_rank > current_rank:
                # 排名后移（从current_rank+1到new_rank的排名减1）
                cursor.execute(
                    "UPDATE project_participant SET participant_rank = participant_rank - 1 "
                    "WHERE project_id = %s AND participant_rank > %s AND participant_rank <= %s",
                    (project_id, current_rank, new_rank)
                )
            else:
                # 排名前移（从new_rank到current_rank-1的排名加1）
                cursor.execute(
                    "UPDATE project_participant SET participant_rank = participant_rank + 1 "
                    "WHERE project_id = %s AND participant_rank >= %s AND participant_rank < %s",
                    (project_id, new_rank, current_rank)
                )

            # 设置新排名
            cursor.execute(
                "UPDATE project_participant SET participant_rank = %s "
                "WHERE project_id = %s AND teacher_id = %s AND participant_rank = 0",
                (new_rank, project_id, teacher_id)
            )

            connection.commit()
            return True, "参与者排名更新成功"
        except Exception as e:
            connection.rollback()
            return False, f"更新参与者排名失败: {str(e)}"
        finally:
            cursor.close()

    def get_project_participants(self, project_id):
        """获取项目的所有参与者信息（按排名排序）"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT pp.teacher_id, t.name, pp.participant_rank, pp.funding "
                "FROM project_participant pp "
                "JOIN teacher t ON pp.teacher_id = t.teacher_id "
                "WHERE pp.project_id = %s "
                "ORDER BY pp.participant_rank",
                (project_id,)
            )

            participants = cursor.fetchall()
            return True, participants
        except Exception as e:
            return False, f"查询项目参与者失败: {str(e)}"
        finally:
            cursor.close()
    # ========== 课程相关操作 ==========
    def assign_course_teaching(self, course_id, teacher_id, year, semester, hours):
        """分配课程教学任务"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 获取课程总学时
            cursor.execute(
                "SELECT total_hours FROM course WHERE course_id = %s",
                (course_id,)
            )
            result = cursor.fetchone()
            if not result:
                return False, "找不到指定的课程"
            
            total_hours = result[0]
            
            # 获取当前学期该课程已分配的总学时
            cursor.execute(
                "SELECT SUM(teaching_hours) FROM course_teaching "
                "WHERE course_id = %s AND course_year = %s AND semester = %s",
                (course_id, year, semester)
            )
            current_total = cursor.fetchone()[0] or 0
            
            # 检查分配后是否超过总学时
            if current_total == 0 and hours == total_hours:
            
                # 插入或更新教学任务
                cursor.execute(
                    "INSERT INTO course_teaching (course_id, teacher_id, course_year, semester, teaching_hours) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE teaching_hours = teaching_hours + %s",
                    (course_id, teacher_id, year, semester, hours, hours)
                )
                
                connection.commit()
                return True, "课程教学任务分配成功"
            else:
                return False, "同学期已有分配，无法增加"
        except Exception as e:
            connection.rollback()
            return False, f"分配课程教学任务失败: {str(e)}"
        finally:
            cursor.close()
    
    def adjust_course_teaching(self, course_id, teacher_id_from, teacher_id_to, year, semester, hours):
        """
        调整课程教学任务，从一个教师转移学时到另一个教师
        确保总学时不变
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 检查两个教师是否不同
            if teacher_id_from == teacher_id_to:
                return False, "不能在同一教师之间转移学时"
            
            # 检查转出教师是否有足够的学时
            cursor.execute(
                "SELECT teaching_hours FROM course_teaching "
                "WHERE course_id = %s AND teacher_id = %s AND course_year = %s AND semester = %s",
                (course_id, teacher_id_from, year, semester)
            )
            result = cursor.fetchone()
            if not result or result[0] < hours:
                return False, "转出教师没有足够的学时可以转移"
            
            # 减少转出教师的学时
            cursor.execute("DELETE FROM course_teaching "
                "WHERE course_id = %s AND teacher_id = %s AND course_year = %s AND semester = %s", 
                (course_id, teacher_id_from, year, semester)
            )
            
            cursor.execute(
                "INSERT INTO course_teaching (course_id, teacher_id, course_year, semester, teaching_hours) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE teaching_hours = teaching_hours + %s",
                (course_id, teacher_id_to, year, semester, hours, hours)
            )
            
            connection.commit()
            return True, "课程教学任务调整成功"
        except Exception as e:
            connection.rollback()
            return False, f"调整课程教学任务失败: {str(e)}"
        finally:
            cursor.close()
    
    def remove_course_teaching(self, course_id, teacher_id, year, semester):
        """移除教师的部分课程教学任务"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # 检查教师是否有足够的学时可以移除
            cursor.execute(
                "SELECT teaching_hours FROM course_teaching "
                "WHERE course_id = %s AND teacher_id = %s AND course_year = %s AND semester = %s",
                (course_id, teacher_id, year, semester)
            )
            result1 = cursor.fetchone()
            if not result1:
                return False, "找不到指定的课程教学任务"
            current_hours = result1[0]
            
            # 获取课程总学时
            cursor.execute(
                "SELECT total_hours FROM course WHERE course_id = %s",
                (course_id,)
            )
            result2 = cursor.fetchone()
            if not result2:
                return False, "找不到指定的课程"
            
            total_hours = result2[0]
            
            if current_hours != total_hours:
                return False, "该课程不是由该教师主讲，无法移除"

            cursor.execute("DELETE FROM course_teaching "
                "WHERE course_id = %s AND teacher_id = %s AND course_year = %s AND semester = %s", 
                (course_id, teacher_id, year, semester)
            )
            
            connection.commit()
            return True, "课程教学任务移除成功"
        except Exception as e:
            connection.rollback()
            return False, f"移除课程教学任务失败: {str(e)}"
        finally:
            cursor.close()
    
    def get_teacher_courses(self, teacher_id, start_year=None, end_year=None):
        """查询教师主讲的课程及详细教学信息"""
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 查询课程基本信息及教师在该课程中的详细信息
            query = """
                SELECT 
                    c.course_id,
                    c.course_name,
                    c.total_hours,
                    c.course_type,
                    ct.course_year,
                    ct.semester,
                    ct.teaching_hours,
                    ct.teaching_hours/c.total_hours*100 AS hours_percentage,
                    (SELECT SUM(teaching_hours) FROM course_teaching 
                     WHERE course_id = c.course_id AND course_year = ct.course_year 
                     AND semester = ct.semester) AS total_assigned_hours,
                    (SELECT COUNT(*) FROM course_teaching 
                     WHERE course_id = c.course_id AND course_year = ct.course_year 
                     AND semester = ct.semester) AS teacher_count,
                    (SELECT GROUP_CONCAT(t.name ORDER BY ct2.teacher_id SEPARATOR ', ') 
                     FROM course_teaching ct2 
                     JOIN teacher t ON ct2.teacher_id = t.teacher_id 
                     WHERE ct2.course_id = c.course_id AND ct2.course_year = ct.course_year 
                     AND ct2.semester = ct.semester) AS all_teachers
                FROM course c
                JOIN course_teaching ct ON c.course_id = ct.course_id
                WHERE ct.teacher_id = %s
            """
            params = [teacher_id]
            
            if start_year and end_year:
                query += " AND ct.course_year BETWEEN %s AND %s"
                params.extend([start_year, end_year])
            
            query += " ORDER BY ct.course_year DESC, ct.semester"
            
            cursor.execute(query, params)
            courses = cursor.fetchall()
            
            # 转换枚举值为可读文本
            course_type_map = {1: "本科生课程", 2: "研究生课程"}
            semester_map = {1: "春季学期", 2: "夏季学期", 3: "秋季学期"}
            
            for course in courses:
                course['course_type_text'] = course_type_map.get(course['course_type'], "未知类型")
                course['semester_text'] = semester_map.get(course['semester'], "未知学期")
                course['year_semester'] = f"{course['course_year']} {course['semester_text']}"
                course['hours_percentage'] = round(course['hours_percentage'], 2)
            
            return True, courses
        except Exception as e:
            return False, f"查询课程失败: {str(e)}"
        finally:
            cursor.close()
