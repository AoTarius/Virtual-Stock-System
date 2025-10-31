# 运行此脚本以获取A股股票列表，并保存到SQLite数据库和CSV文件中。
# 数据将保存到../db/目录下的stocks.db数据库和stocks.csv文件中
# 建议优先使用get_stock-1.py脚本进行简单收集

import akshare as ak
import pandas as pd
import sqlite3
import time
from typing import List, Dict
from pathlib import Path

class StockDataCollector:
    def __init__(self, db_path: str = None):
        # 如果没有提供 db_path，则将数据库保存在项目根的 db 目录下
        if db_path is None:
            db_dir = Path(__file__).resolve().parents[2] / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "stocks.db")
        else:
            self.db_path = db_path

        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                market TEXT NOT NULL,
                industry TEXT,
                listing_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("数据库初始化完成")
    
    def get_all_stocks(self) -> pd.DataFrame:
        """获取所有A股股票列表"""
        try:
            print("正在获取股票列表...")
            
            # 获取沪深京A股列表
            stock_info_a_code_name_df = ak.stock_info_a_code_name()
            
            # 获取各个市场的股票
            stock_sh = ak.stock_info_sh_name_code()  # 上海证券交易所
            stock_sz = ak.stock_info_sz_name_code()  # 深圳证券交易所
            stock_bj = ak.stock_info_bj_name_code()  # 北京证券交易所
            
            # 合并所有股票数据
            all_stocks = []
            
            # 处理A股数据
            if not stock_info_a_code_name_df.empty:
                for _, row in stock_info_a_code_name_df.iterrows():
                    all_stocks.append({
                        'symbol': row['code'],
                        'name': row['name'],
                        'market': self._get_market_by_symbol(row['code'])
                    })
            
            # 处理上海股市数据
            if not stock_sh.empty:
                for _, row in stock_sh.iterrows():
                    all_stocks.append({
                        'symbol': row['COMPANY_CODE'],
                        'name': row['COMPANY_ABBR'],
                        'market': 'SH'
                    })
            
            # 处理深圳股市数据  
            if not stock_sz.empty:
                for _, row in stock_sz.iterrows():
                    all_stocks.append({
                        'symbol': row['A股代码'],
                        'name': row['A股简称'],
                        'market': 'SZ'
                    })
            
            # 处理北京股市数据
            if not stock_bj.empty:
                for _, row in stock_bj.iterrows():
                    all_stocks.append({
                        'symbol': row['证券代码'],
                        'name': row['证券简称'],
                        'market': 'BJ'
                    })
            
            df = pd.DataFrame(all_stocks)
            print(f"共获取到 {len(df)} 只股票")
            return df
            
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def _get_market_by_symbol(self, symbol: str) -> str:
        """根据股票代码判断市场"""
        if symbol.startswith('6'):
            return 'SH'  # 上海
        elif symbol.startswith('0') or symbol.startswith('3'):
            return 'SZ'  # 深圳
        elif symbol.startswith('4') or symbol.startswith('8'):
            return 'BJ'  # 北京
        else:
            return 'OTHER'
    
    def save_to_database(self, df: pd.DataFrame):
        """保存到数据库"""
        if df.empty:
            print("没有数据可保存")
            return
        
        conn = sqlite3.connect(self.db_path)
        try:
            # 使用INSERT OR REPLACE来处理重复数据
            df.to_sql('stocks_temp', conn, if_exists='replace', index=False)
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO stocks (symbol, name, market)
                SELECT symbol, name, market FROM stocks_temp
            ''')
            conn.commit()
            print(f"成功保存 {len(df)} 条股票数据到数据库")
            
        except Exception as e:
            print(f"保存到数据库失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = "stocks.csv"):
        """保存到CSV文件"""
        if df.empty:
            print("没有数据可保存")
            return
        
        try:
            # 将 CSV 保存到与数据库相同的目录（通常是项目根的 db 目录）
            db_dir = Path(self.db_path).resolve().parent
            db_dir.mkdir(parents=True, exist_ok=True)
            filepath = db_dir / filename
            df.to_csv(str(filepath), index=False, encoding='utf-8-sig')
            print(f"成功保存 {len(df)} 条股票数据到 {filepath}")
        except Exception as e:
            print(f"保存到CSV失败: {e}")
    
    def get_stock_details(self, symbol: str) -> Dict:
        """获取股票详细信息"""
        try:
            stock_individual_info_em_df = ak.stock_individual_info_em(symbol=symbol)
            return stock_individual_info_em_df.to_dict()
        except Exception as e:
            print(f"获取股票 {symbol} 详细信息失败: {e}")
            return {}

def main():
    # 创建收集器实例
    collector = StockDataCollector()
    
    # 获取所有股票数据
    stocks_df = collector.get_all_stocks()
    
    if not stocks_df.empty:
        # 保存到数据库
        collector.save_to_database(stocks_df)
        
        # 保存到CSV
        collector.save_to_csv(stocks_df)
        
        # 显示前10条数据
        print("\n前10条股票数据:")
        print(stocks_df.head(10))
        
        # 按市场统计
        market_stats = stocks_df['market'].value_counts()
        print(f"\n各市场股票数量统计:")
        for market, count in market_stats.items():
            print(f"{market}: {count} 只")
    else:
        print("未能获取到股票数据")

if __name__ == "__main__":
    main()