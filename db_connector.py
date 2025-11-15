import mysql.connector
from mysql.connector import Error

class DatabaseConnector:
    def __init__(self):
        self.connection = None
    
    def connect(self, host, database, user, password):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=3306,
            )
            if self.connection.is_connected():
                print("成功连接到MySQL数据库")
        except Error as e:
            print(f"连接数据库时出错: {e}")
            raise
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭")
    
    def get_connection(self):
        """获取数据库连接"""
        return self.connection