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
    cost = float(piles) * float(unitPrice)

    user_db_path = 'myproject/templates/db/user.db'
    user_conn = sqlite3.connect(user_db_path)
    # 检查用户余额是否足够
    cursor = user_conn.execute('''
        SELECT funds FROM Users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    if row is None:
        print(f"用户：{user_id}不存在")
        user_conn.close()
        return
    current_funds = row[0]
    if current_funds < cost:
        print(f"用户：{user_id}余额不足，无法购买股票")
        user_conn.close()
        return False
    else:
       # 调用函数进行扣款
        deduct_funds(user_id, cost)
        # 添加股票记录
        stock_db_path = 'myproject/templates/db/userStocks.db'
        conn = sqlite3.connect(stock_db_path)
        conn.execute('''
            INSERT OR IGNORE INTO UserStocks (user_id, stockID, time, operation, piles, unitPrice, cost)
            VALUES (?, ?, ?, '购买', ?, ?, ?)
        ''', (user_id, stockID, time, piles, unitPrice, cost))

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
        SET funds = funds + ?
        WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()
    print(f"用户：{user_id}充值完成")

# 用户扣款
def deduct_funds(user_id, amount):
    """
    传入参数：
    user_id: 用户ID
    amount: 扣款金额
    """
    db_path = 'myproject/templates/db/user.db'
    conn = sqlite3.connect(db_path)
    conn.execute('''
        UPDATE Users
        SET funds = funds - ?
        WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()
    print(f"用户：{user_id}扣款完成")


if __name__ == "__main__":
    # 示例操作
    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # deposit_funds(1, 1000)  # 用户1充值1000
    buy_stock(1, '000001', current_time, 10, 5.0)  # 用户1购买股票000001，10股，单价5.0