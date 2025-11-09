# 快速初始化用户1数据脚本

from initialize_UserDb import initialize_user_db, create_default_user, reset_user_data, delete_user
from initialize_UserStocksDb import initialize_userStocks_db, reset_user_stocks, insert_default_stock
from StockOperations import deposit_funds, deduct_funds
DB_PATH_USER = 'myproject/templates/db/user.db'
DB_PATH_USERSTOCKS = 'myproject/templates/db/userStocks.db'

if __name__ == "__main__":
    # initialize_user_db(DB_PATH_USER) # 初始化用户数据库
    # reset_user_data(DB_PATH_USER, 1)  # 重置用户1的数据
    # create_default_user(DB_PATH_USER) # 创建默认用户1

    # initialize_userStocks_db(DB_PATH_USERSTOCKS) # 初始化用户股票持有记录数据库
    # reset_user_stocks(DB_PATH_USERSTOCKS, 1)  # 重置用户1的股票记录
    # insert_default_stock(DB_PATH_USERSTOCKS, 1)  # 插入默认股票记录

    # deposit_funds(1, 1000)  # 用户1充值1000
    # deduct_funds(1, 200)    # 用户1扣款200
    delete_user(DB_PATH_USER)  # 删除指定用户