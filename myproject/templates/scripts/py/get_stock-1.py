# 获取A股所有股票代码和名称，并保存为CSV和JSON格式的文件
# 运行此脚本需要安装akshare库：pip install akshare
# 数据将保存到../db/目录下，文件名包含时间戳以避免覆盖

import akshare as ak
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

def simple_stock_collector():
    """简单的股票数据收集器"""
    print("开始收集股票数据...")
    
    try:
        # 获取A股所有股票代码和名称
        stock_df = ak.stock_info_a_code_name()
        
        if not stock_df.empty:
            # 重命名列
            stock_df = stock_df.rename(columns={'code': 'symbol', 'name': 'name'})
            
            # 添加市场信息
            stock_df['market'] = stock_df['symbol'].apply(
                lambda x: 'SH' if x.startswith('6') else 'SZ' if x.startswith('0') or x.startswith('3') else 'BJ'
            )
            
            # 保存到CSV/JSON：使用基于脚本位置的 db 文件夹，这样无论从哪个工作目录运行脚本都能正确定位
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 脚本位于 scripts/py/，所以 parents[2] 指向项目根目录 finance_system
            db_dir = Path(__file__).resolve().parents[2] / "db"
            db_dir.mkdir(parents=True, exist_ok=True)

            filename = db_dir / f"stocks_{timestamp}.csv"
            # pandas 支持 path-like，但为了兼容性我们传入字符串
            stock_df.to_csv(str(filename), index=False, encoding='utf-8-sig')

            # 保存到JSON
            json_filename = db_dir / f"stocks_{timestamp}.json"
            stock_df.to_json(str(json_filename), orient='records', force_ascii=False, indent=2)
            
            print(f"成功收集 {len(stock_df)} 只股票")
            print(f"数据已保存到: {filename} 和 {json_filename}")
            
            # 显示统计信息
            print(f"\n市场分布:")
            print(stock_df['market'].value_counts())
            
            return stock_df
        else:
            print("未能获取到股票数据")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"收集股票数据时出错: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # 运行简单的收集器
    df = simple_stock_collector()
    
    if not df.empty:
        print("\n前5条数据示例:")
        print(df.head())