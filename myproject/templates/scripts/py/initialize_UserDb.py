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
            password    CHAR(64)      NOT NULL,
            funds       REAL          NOT NULL DEFAULT 0,
            total_input REAL          NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id)
        )
    ''')
    conn.commit()
    conn.close()
    print("创建完成")

# 创建默认用户
def create_default_user(db_path):
    password = 'password111'  # 默认密码
    conn = sqlite3.connect(db_path)
    conn.execute('''
        INSERT OR IGNORE INTO Users (user_id, username, password, funds)
        VALUES (1, '用户1', ?, 0)
    ''', (password,))
    conn.commit()
    conn.close()
    print("默认用户创建完成")

# 重置用户目标用户数据
def reset_user_data(db_path, user_id):
    conn = sqlite3.connect(db_path)
    conn.execute('''
        DELETE FROM Users
        WHERE user_id = ?
    ''', (user_id,))

    conn.commit()
    conn.close()
    print("用户{}数据已重置".format(user_id))

if __name__ == "__main__":
    initialize_user_db('myproject/templates/db/user.db') # 初始化数据库
    create_default_user('myproject/templates/db/user.db') # 创建默认用户
    # reset_user_data('myproject/templates/db/user.db', 1)  # 重置用户1的数据