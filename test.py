from db_connector import DatabaseConnector
from teacher_service import TeacherService

# 初始化数据库连接
db_connector = DatabaseConnector()
db_connector.connect(host="localhost", database="teacher_research_system", 
                    user="root", password="20050318")

# 创建服务对象
teacher_service = TeacherService(db_connector)

# # 示例：添加论文
# result, message = teacher_service.add_paper(
#     paper_id="0001",
#     title="ZB+tree: 一种 ZNS SSD 感知的新型索引结构",
#     journal="计算机研究与发展",
#     pub_year=2023,
#     paper_type=1,
#     paper_level=4,
#     authors=[
#         ("00001", 1, False),  # (teacher_id, rank, is_corresponding)
#         ("00007", 2, True)
#     ]
# )
# print(message)

# 示例：查询教师论文
success, papers = teacher_service.get_teacher_papers("00001", 2022, 2023)
if success:
    for paper in papers:
        print(paper['title'], paper['journal'], paper['pub_year'], paper['paper_type_text'], paper['paper_level_text'], paper['author_rank'])

# # 示例：添加项目
# result, message = teacher_service.add_project(
#     project_id="PROJ0001",
#     name="面向异构混合内存的 NVM 感知索引及自适应学习方法研究",
#     source="国家自然科学基金委",
#     project_type=1,
#     start_year=2021,
#     end_year=2024,
#     total_funding=580000,
#     participants=[
#         ("00003", 1, 300000),  # (teacher_id, rank, funding)
#         ("00004", 2, 280000)
#     ]
# )
# print(message)

# # 示例：调整项目经费
# result, message = teacher_service.update_project_funding(
#     project_id="PROJ0001",
#     teacher_id="00003",
#     new_funding=350000
# )
# print(message)

# 关闭数据库连接
db_connector.disconnect()