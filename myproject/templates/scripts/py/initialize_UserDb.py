# 初始化 UserDb 数据库的脚本
# 直接运行就可以

import sqlite3

def initialize_user_db(db_path):
    """Initializes the UserDb SQLite database with the required schema."""
    conn = sqlite3.connect(db_path)

    # Create the Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id     INTEGER(10)   NOT NULL UNIQUE,
            username    CHAR(30)      NOT NULL,
            deposit     REAL          NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id)
        )
    ''')
    conn.commit()
    conn.close()
    print("创建完成")

# 创建默认用户
def create_default_user(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute('''
        INSERT OR IGNORE INTO Users (user_id, username, deposit)
        VALUES (1, '用户1', 0)
    ''')
    conn.commit()
    conn.close()
    print("默认用户创建完成")

if __name__ == "__main__":
    initialize_user_db('myproject/templates/db/user.db')
    create_default_user('myproject/templates/db/user.db')