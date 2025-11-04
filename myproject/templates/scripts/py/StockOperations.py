# 此文件设计基本操作功能

import sqlite3

# 用户购买股票，返回bool值表示是否购买成功
def buy_stock(user_id, stockID, time, piles, unitPrice):
    """
    传入参数：
    user_id: 用户ID
    stockID: 股票代码
    time: 操作时间
    piles: 购买股数
    unitPrice: 单价
    """
    cost = piles * unitPrice

    # 从存款扣除cost金额
    user_db_path = 'myproject/templates/db/user.db'
    user_conn = sqlite3.connect(user_db_path)
    # 检查用户余额是否足够
    cursor = user_conn.execute('''
        SELECT deposit FROM Users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    if row is None:
        print(f"用户：{user_id}不存在")
        user_conn.close()
        return
    current_deposit = row[0]
    if current_deposit < cost:
        print(f"用户：{user_id}余额不足，无法购买股票")
        user_conn.close()
        return False
    else:
        # 扣除用户存款
        user_conn.execute('''
            UPDATE Users
            SET deposit = deposit - ?
            WHERE user_id = ?
        ''', (cost, user_id))
        # 添加股票记录
        stock_db_path = 'myproject/templates/db/userStocks.db'
        conn = sqlite3.connect(stock_db_path)
        conn.execute('''
            INSERT OR IGNORE INTO UserStocks (user_id, stockID, time, operation, piles, unitPrice, cost)
            VALUES (?, ?, ?, '购买', ?, ?, ?)
        ''', (user_id, stockID, time, time, piles, unitPrice. cost))

        conn.commit()
        conn.close()
        print(f"用户：{user_id}股票购买完成")
        return True

# 用户充值
def deposit_funds(user_id, amount):
    """
    传入参数：
    user_id: 用户ID
    amount: 充值金额
    """
    db_path = 'myproject/templates/db/user.db'
    conn = sqlite3.connect(db_path)
    conn.execute('''
        UPDATE Users
        SET deposit = deposit + ?
        WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()
    print("用户：{user_id}充值完成")