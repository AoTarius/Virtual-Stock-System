# 初始化用户的股票持有记录
# 直接运行就可以

import sqlite3

def initialize_userStocks_db(db_path):
    """Initializes the UserDb SQLite database with the required schema."""
    conn = sqlite3.connect(db_path)

    # Create the UserStocks table (SQLite-compatible)
    # 分别是 用户id，股票代码，操作时间，操作类型，持有股数，单价
    conn.execute('''
        CREATE TABLE IF NOT EXISTS UserStocks (
            user_id   INTEGER NOT NULL,
            stockID   TEXT    NOT NULL,
            time      TEXT    NOT NULL,
            operation TEXT    NOT NULL,
            piles     INTEGER NOT NULL,
            unitPrice REAL    NOT NULL,
            cost      REAL    NOT NULL,
            PRIMARY KEY(user_id, stockID, time)
        )
    ''')
    conn.commit()
    conn.close()
    print("创建完成")

# 重置目标用户的股票记录
def reset_user_stocks(db_path, user_id):
    conn = sqlite3.connect(db_path)
    conn.execute('''
        DELETE FROM UserStocks
        WHERE user_id = ?
    ''', (user_id,))

    conn.commit()
    conn.close()
    print("用户的股票记录已重置")

# 为目标用户插入一支股票
# 默认设置：操作时间为当前时间，交易股数10，单价为5.0
# 股票代码 000001
def insert_default_stock(db_path, user_id, stockID='000001', piles=10, unitPrice=5.0):
    import datetime
    cost = piles * unitPrice
    conn = sqlite3.connect(db_path)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute('''
        INSERT OR IGNORE INTO UserStocks (user_id, stockID, time, operation, piles, unitPrice, cost)
        VALUES (?, ?, ?, '购买', ?, ?, ?)
    ''', (user_id, stockID, current_time, piles, unitPrice, cost))
    conn.commit()
    conn.close()
    print("默认股票插入完成")

if __name__ == "__main__":
    initialize_userStocks_db('myproject/templates/db/userStocks.db')
    # reset_user_stocks('myproject/templates/db/userStocks.db', 1) # 重置用户1的股票记录
    insert_default_stock('myproject/templates/db/userStocks.db', 1) # 插入默认股票记录