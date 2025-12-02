
import glob
import os
import pandas as pd

def convert_mt4_to_vnpy(input_file, output_file, symbol="XAUUSD", exchange="FOREX"):
    """
    将MT4格式的CSV文件转换为vn.py可导入的格式
    
    参数:
    input_file: 输入的MT4格式CSV文件路径
    output_file: 输出的vn.py格式CSV文件路径
    symbol: 品种代码，默认为XAUUSD
    exchange: 交易所，默认为FOREX
    """
    try:
        # 读取MT4格式的CSV文件
        df = pd.read_csv(input_file, delimiter='\t')

        # 合并日期和时间列，创建datetime
        if '<TIME>' in df.columns:
            # 如果有时间列，合并日期和时间
            df['datetime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'], format='%Y.%m.%d %H:%M:%S')
        else:
            # 如果没有时间列，添加默认时间
            df['datetime'] = pd.to_datetime(df['<DATE>'] + ' 00:00:00', format='%Y.%m.%d %H:%M:%S')
        
        # 重命名列以符合vn.py格式
        df_renamed = df.rename(columns={
            '<OPEN>': 'open',
            '<HIGH>': 'high', 
            '<LOW>': 'low',
            '<CLOSE>': 'close',
            '<TICKVOL>': 'volume'
        })
        
        # 选择并重新排列列
        vnpy_df = df_renamed[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
        vnpy_df['datetime'] = vnpy_df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 添加symbol和exchange列
        # vnpy_df['symbol'] = symbol
        # vnpy_df['exchange'] = exchange
        # vnpy_df['interval'] = '1h'  # 根据你的数据频率设置，这里是1小时
        
        # 重新排列列顺序以符合vn.py格式
        # final_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'symbol', 'exchange', 'interval']
        final_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        vnpy_df = vnpy_df[final_columns]
        
        # 保存为CSV文件
        vnpy_df.to_csv(output_file, index=False)
        
        print(f"转换完成！输出文件: {output_file}")
        print(f"共转换 {len(vnpy_df)} 行数据")
        return True
        
    except Exception as e:
        print(f"转换文件 {input_file} 时出错: {str(e)}")
        return False


def convert_all_mt4_files():
    """
    转换当前目录下所有的MT4格式CSV文件
    """
    # 获取当前目录下所有的CSV文件
    csv_files = glob.glob("*.csv")
    
    # 过滤掉已经转换过的文件（包含_format后缀的）
    input_files = [f for f in csv_files if not f.endswith("_format.csv")]
    
    if not input_files:
        print("当前目录下没有找到需要转换的CSV文件")
        return
    
    print(f"找到 {len(input_files)} 个需要转换的文件:")
    for file in input_files:
        print(f"  - {file}")
    
    success_count = 0
    
    # 逐个转换文件
    for input_file in input_files:
        # 生成输出文件名：原文件名 + _format.csv
        base_name = os.path.splitext(input_file)[0]  # 去掉扩展名
        output_file = base_name + "_format.csv"
        
        # 转换文件
        if convert_mt4_to_vnpy(input_file, output_file):
            success_count += 1
    
    print(f"\n转换完成！成功转换 {success_count}/{len(input_files)} 个文件")
# 使用示例
if __name__ == "__main__":
    convert_all_mt4_files()
    print("程序执行完毕！")