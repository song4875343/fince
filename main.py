import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                             NavigationToolbar2Tk)
import matplotlib.pyplot as plt
import ctypes  # 添加这行
import baostock as bs
import datetime
from tkinter import messagebox
import os
import json
# 在创建窗口之前添加这两行
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass
# 在创建 Figure 时设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题

def load_stock_list():
    try:
        if os.path.exists('stock_history.json'):
            with open('stock_history.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载股票列表失败: {e}")
    return []

def save_stock_list():
    try:
        with open('stock_history.json', 'w', encoding='utf-8') as f:
            json.dump(stock_history, f, ensure_ascii=False)
    except Exception as e:
        print(f"保存股票列表失败: {e}")

def update_stock_history(code, name):
    # 检查是否已存在
    for stock in stock_history:
        if stock['code'] == code:
            stock_history.remove(stock)
            break
    
    # 添加新记录到开头
    stock_history.insert(0, {'code': code, 'name': name})
    
    # 只保留最新的5个记录
    while len(stock_history) > 5:
        stock_history.pop()
    
    # 更新列表框
    update_listbox()

def update_listbox():
    history_listbox.delete(0, tk.END)
    for stock in stock_history:
        history_listbox.insert(tk.END, f"{stock['name']}({stock['code']})")

def on_select_stock(event):
    selection = history_listbox.curselection()
    if selection:
        index = selection[0]
        selected_stock = stock_history[index]
        stock_code_entry.delete(0, tk.END)
        stock_code_entry.insert(0, selected_stock['code'].replace('sh.', '').replace('sz.', ''))
        get_stock_data()

# 加载历史记录
stock_history = load_stock_list()

def calculate_pivot_points():
    try:
        high = float(high_entry.get())
        low = float(low_entry.get())
        close = float(close_entry.get())
        open_price = float(open_entry.get())
        
        # 计算枢轴点
        pivot = (high + low + close) / 3
        
        # 计算支撑位和压力位
        s1 = (2 * pivot) - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        r1 = (2 * pivot) - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        
        # 更新标签
        pivot_label.config(text=f"枢轴点(P): {pivot:.2f}")
        r1_label.config(text=f"压力位1(R1): {r1:.2f}")
        r2_label.config(text=f"压力位2(R2): {r2:.2f}")
        r3_label.config(text=f"压力位3(R3): {r3:.2f}")
        s1_label.config(text=f"支撑位1(S1): {s1:.2f}")
        s2_label.config(text=f"支撑位2(S2): {s2:.2f}")
        s3_label.config(text=f"支撑位3(S3): {s3:.2f}")
        
        # 清除旧图
        ax.clear()
        
        # 绘制K线图
        width = 0.6
        if close > open_price:
            color = 'red'
        else:
            color = 'green'
            
        # 绘制实体部分
        ax.bar(1, close - open_price, width, bottom=min(open_price, close), color=color)
        # 绘制上下影线
        ax.plot([1, 1], [low, high], color='black', linewidth=1)
        
        # 绘制支撑位和压力位
        lines = [
            (r3, 'R3', 'red'),
            (r2, 'R2', 'red'),
            (r1, 'R1', 'red'),
            (pivot, 'P', 'black'),
            (s1, 'S1', 'green'),
            (s2, 'S2', 'green'),
            (s3, 'S3', 'green')
        ]
        
        for price, label, color in lines:
            ax.axhline(y=price, color=color, linestyle='--', alpha=0.5)
            ax.text(1.2, price, f'{label}: {price:.2f}', color=color)
        
        # 设置图表范围和标签
        ax.set_xlim(0.5, 1.5)
        ax.set_ylim(min(low, s3) * 0.99, max(high, r3) * 1.01)
        ax.set_title('股票价格与枢轴点')
        ax.set_ylabel('价格')
        ax.grid(True, linestyle='--', alpha=0.3)
        
        # 更新画布
        canvas.draw()
        
    except ValueError:
        print("请输入有效的数字")

def get_stock_data():
    try:
        code = stock_code_entry.get()
        end_date = date_entry.get()
        
        # 格式化股票代码
        if code.startswith('6'):
            code = 'sh.' + code
        else:
            code = 'sz.' + code
            
        # 登录系统
        bs.login()
        
        # 获取股票基本信息
        rs = bs.query_stock_basic(code=code)
        stock_info = rs.get_data()
        if stock_info.empty:
            messagebox.showerror("错误", "没有找到股票信息")
            return
        stock_name = stock_info['code_name'][0]
        
        # 获取日线数据
        end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        start_date = (end_date_obj - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        
        rs = bs.query_history_k_data_plus(code,
            "date,open,high,low,close",
            start_date=start_date,
            end_date=end_date,
            frequency="d")
        daily_data = rs.get_data()
        
        # 获取周线数据（获取更长时间以确保至少有一周完整数据）
        week_start_date = (end_date_obj - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(code,
            "date,open,high,low,close",
            start_date=week_start_date,
            end_date=end_date,
            frequency="w")
        weekly_data = rs.get_data()
        
        if daily_data.empty or weekly_data.empty:
            messagebox.showerror("错误", "没有找到数据")
            return
            
        # 获取最近三个交���日的数据
        last_three_days = daily_data.tail(3)
        # 获取最近一周的数据
        last_week = weekly_data.tail(1).iloc[0]
        
        # 计算周线枢轴点
        week_high = float(last_week['high'])
        week_low = float(last_week['low'])
        week_close = float(last_week['close'])
        
        week_pivot = (week_high + week_low + week_close) / 3
        week_s1 = (2 * week_pivot) - week_high
        week_s2 = week_pivot - (week_high - week_low)
        week_s3 = week_low - 2 * (week_high - week_pivot)
        week_r1 = (2 * week_pivot) - week_low
        week_r2 = week_pivot + (week_high - week_low)
        week_r3 = week_high + 2 * (week_pivot - week_low)
        
        # 清除旧图并调整布局
        ax.clear()
        fig.subplots_adjust(left=0.08, right=0.92, top=0.9, bottom=0.15)
        
        # 获取所有价格点（包括周线）
        all_prices = []
        # 添加周线价格点
        all_prices.extend([week_high, week_low, week_close, 
                         week_pivot, week_s1, week_s2, week_s3, 
                         week_r1, week_r2, week_r3])
        
        # 添加日线价格点
        for i, (_, row) in enumerate(last_three_days.iterrows()):
            # 计算枢轴点
            high = float(row['high'])
            low = float(row['low'])
            close = float(row['close'])
            open_price = float(row['open'])
            
            pivot = (high + low + close) / 3
            s1 = (2 * pivot) - high
            s2 = pivot - (high - low)
            s3 = low - 2 * (high - pivot)
            r1 = (2 * pivot) - low
            r2 = pivot + (high - low)
            r3 = high + 2 * (pivot - low)
            
            # 绘制K线
            width = 0.15
            if close > open_price:
                color = 'red'
                bottom = open_price
                height = close - open_price
            else:
                color = 'green'
                bottom = close
                height = open_price - close
                
            # 绘制实体部分
            ax.bar(i+1, height, width, bottom=bottom, color=color)
            # 绘制上下影线
            ax.plot([i+1, i+1], [low, high], color='black', linewidth=1)
            
            # 标注OHLC价格和圆点
            ohlc_points = [
                (open_price, 'O'),
                (high, 'H'),
                (low, 'L'),
                (close, 'C')
            ]
            
            for price, label in ohlc_points:
                # 绘制圆点
                ax.plot(i+1, price, 'o', color='blue', markersize=4)
                # 添加价���标注
                ax.text(i+1 + 0.1, price, f'{price:.2f}', 
                       color='blue', va='center', ha='left', fontsize=8)
            
            # 为每天绘制独立的支撑位和压力位线条
            lines = [
                (r3, 'R3', 'red'),
                (r2, 'R2', 'red'),
                (r1, 'R1', 'red'),
                (pivot, 'P', 'black'),
                (s1, 'S1', 'green'),
                (s2, 'S2', 'green'),
                (s3, 'S3', 'green')
            ]
            
            # 计算线条的开始和结束位置
            x_start = i + 1 - 0.2
            x_end = i + 1 + 0.2
            
            for price, label, line_color in lines:
                # 绘制短线
                ax.plot([x_start, x_end], [price, price], 
                       color=line_color, linestyle='--', alpha=0.5)
                
                # 添加带英文首字母的价格标注
                ax.text(x_end + 0.1, price, f'{label}: {price:.2f}', 
                       color=line_color, va='center', ha='left', fontsize=8)
        
        # 在最右侧添加周线数据
        # 绘制周线K线
        i = 4  # 第四个位置
        width = 0.15
        if float(last_week['close']) > float(last_week['open']):
            color = 'red'
            bottom = float(last_week['open'])
            height = float(last_week['close']) - float(last_week['open'])
        else:
            color = 'green'
            bottom = float(last_week['close'])
            height = float(last_week['open']) - float(last_week['close'])

        # 绘制周线实体部分
        ax.bar(i, height, width, bottom=bottom, color=color)
        # 绘制周线上下影线
        ax.plot([i, i], [week_low, week_high], color='black', linewidth=1)

        # 标注周线OHLC价格和圆点
        week_ohlc_points = [
            (float(last_week['open']), 'WO'),
            (week_high, 'WH'),
            (week_low, 'WL'),
            (week_close, 'WC')
        ]

        for price, label in week_ohlc_points:
            # 绘制圆点
            ax.plot(i, price, 'o', color='purple', markersize=4)
            # 添加价格标注
            ax.text(i + 0.1, price, f'{label}: {price:.2f}', 
                   color='purple', va='center', ha='left', fontsize=8)

        # 绘制周线枢轴点
        week_lines = [
            (week_r3, 'WR3', 'darkred'),
            (week_r2, 'WR2', 'darkred'),
            (week_r1, 'WR1', 'darkred'),
            (week_pivot, 'WP', 'purple'),
            (week_s1, 'WS1', 'darkgreen'),
            (week_s2, 'WS2', 'darkgreen'),
            (week_s3, 'WS3', 'darkgreen')
        ]

        # 为周线绘制支撑位和压力位
        x_start = i - 0.2
        x_end = i + 0.2

        for price, label, line_color in week_lines:
            # 绘制短线
            ax.plot([x_start, x_end], [price, price], 
                   color=line_color, linestyle='--', alpha=0.5)
            # 添加标签
            ax.text(x_end + 0.1, price, f'{label}: {price:.2f}', 
                   color=line_color, va='center', ha='left', fontsize=8)

        # 更新x轴刻度和标签
        ax.set_xticks([1, 2, 3, 4])
        dates = list(last_three_days['date'])
        dates.append('周K线')  # 将'周线'改为'周K线'
        ax.set_xticklabels(dates, rotation=0)

        # 扩大显示范围以适应所有元素
        ax.set_xlim(0.2, 5.0)  # 扩大右侧空间以显示周线标签

        # 设置图表标题和标签
        ax.set_title(f'{stock_name}({code}) 最近三个交易日股票价格与枢轴点（周线）', fontproperties='SimHei')
        ax.set_ylabel('价格')
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(last_three_days['date'], rotation=0)
        ax.grid(True, linestyle='--', alpha=0.3)
        
        # 更新画布
        canvas.draw()
        
        # 填充最后一天的数据到输入框
        last_day = last_three_days.iloc[-1]
        open_entry.delete(0, tk.END)
        open_entry.insert(0, last_day['open'])

        high_entry.delete(0, tk.END)
        high_entry.insert(0, last_day['high'])

        low_entry.delete(0, tk.END)
        low_entry.insert(0, last_day['low'])

        close_entry.delete(0, tk.END)
        close_entry.insert(0, last_day['close'])
        
        # 在成功获取数据后，更新历史记录
        update_stock_history(code, stock_name)
        
    except Exception as e:
        messagebox.showerror("错误", str(e))
    finally:
        bs.logout()

# 创建主窗口
root = tk.Tk()
root.title("股票枢轴点计算器")

# 使用固定的窗口大小
window_width = 1400  # 从1200改为1400
window_height = 800  # 固定高度

# 设置窗口大小和位置
root.geometry(f"{window_width}x{window_height}+100+100")  # 位置固定在 (100,100)

# 允许窗口调整大小
root.resizable(True, True)

# 创建Figure，使用固定的尺寸
fig = Figure(figsize=(8, 6), dpi=100)  # 使用固定的图表尺寸
ax = fig.add_subplot(111)
ax.set_title('股票价格与枢轴点', fontproperties='SimHei')
ax.set_ylabel('价格', fontproperties='SimHei')

# 设置统一的边距
fig.subplots_adjust(left=0.08, right=0.92, top=0.9, bottom=0.15)  # 调整左右边距

# 创建左侧框架
left_frame = ttk.Frame(root)
left_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

# 创建输入框框架
input_frame = ttk.LabelFrame(left_frame, text="价格输入", padding="5 5 5 5")
input_frame.pack(fill=tk.X, padx=5, pady=5)

# 创建输入框标签
ttk.Label(input_frame, text="开盘价:").grid(row=0, column=0, padx=5, pady=5)
open_entry = ttk.Entry(input_frame)
open_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="最高价:").grid(row=1, column=0, padx=5, pady=5)
high_entry = ttk.Entry(input_frame)
high_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="最低价:").grid(row=2, column=0, padx=5, pady=5)
low_entry = ttk.Entry(input_frame)
low_entry.grid(row=2, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="收盘价:").grid(row=3, column=0, padx=5, pady=5)
close_entry = ttk.Entry(input_frame)
close_entry.grid(row=3, column=1, padx=5, pady=5)

# 添加计算按钮
calc_button = ttk.Button(input_frame, text="计算枢轴点", command=calculate_pivot_points)
calc_button.grid(row=4, column=0, columnspan=2, pady=10)

# 创建结果显示框架
result_frame = ttk.LabelFrame(left_frame, text="计算结信息", padding="5 5 5 5")
result_frame.pack(fill=tk.X, padx=5, pady=5)

# 结果标签使用grid布局
pivot_label = ttk.Label(result_frame, text="枢轴点(P): ")
pivot_label.grid(row=0, column=0, padx=5, pady=2, sticky='w')

r1_label = ttk.Label(result_frame, text="压力位1(R1): ")
r1_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')

r2_label = ttk.Label(result_frame, text="压力位2(R2): ")
r2_label.grid(row=1, column=0, padx=5, pady=2, sticky='w')

r3_label = ttk.Label(result_frame, text="压力位3(R3): ")
r3_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')

s1_label = ttk.Label(result_frame, text="支撑位1(S1): ")
s1_label.grid(row=2, column=0, padx=5, pady=2, sticky='w')

s2_label = ttk.Label(result_frame, text="支撑位2(S2): ")
s2_label.grid(row=2, column=1, padx=5, pady=2, sticky='w')

s3_label = ttk.Label(result_frame, text="支撑位3(S3): ")
s3_label.grid(row=3, column=0, padx=5, pady=2, sticky='w')

# 修改股票信息输入框架的布局
stock_frame = ttk.LabelFrame(left_frame, text="股票信息", padding="5 5 5 5")
stock_frame.pack(fill=tk.X, padx=5, pady=5)

# 使用上下两行布局，但控制入框宽度
ttk.Label(stock_frame, text="股票代码:").grid(row=0, column=0, padx=5, pady=5)
stock_code_entry = ttk.Entry(stock_frame, width=12)  # 设置较窄的宽度
stock_code_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(stock_frame, text="日期:").grid(row=1, column=0, padx=5, pady=5)
date_entry = ttk.Entry(stock_frame, width=12)  # 设置较窄的宽度
date_entry.grid(row=1, column=1, padx=5, pady=5)

# 设置默认日期为今天
today = datetime.datetime.now().strftime('%Y-%m-%d')
date_entry.insert(0, today)

# 获取数据按钮
get_data_button = ttk.Button(stock_frame, text="获取数据", command=get_stock_data)
get_data_button.grid(row=2, column=0, columnspan=2, pady=10)

# 在创建左侧框架的最后添加历史记录列表框
history_frame = ttk.LabelFrame(left_frame, text="历史记录", padding="5 5 5 5")
history_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

history_listbox = tk.Listbox(history_frame, height=5)
history_listbox.pack(fill=tk.BOTH, expand=True)
history_listbox.bind('<<ListboxSelect>>', on_select_stock)

# 初始化列表显示
update_listbox()

# 在窗口关闭时保存历史记录
root.protocol("WM_DELETE_WINDOW", lambda: [save_stock_list(), root.destroy()])

# 创建右侧框架用于图表
right_frame = ttk.Frame(root)
right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

# 首先定义 on_resize 函数
_first_resize = True

def on_resize(event=None):
    global _first_resize
    
    def _resize():
        try:
            width = right_frame.winfo_width()
            height = right_frame.winfo_height()
            
            if width > 1 and height > 1:  # 确保有有效的尺寸
                fig.set_size_inches(width/100, height/100)
                fig.subplots_adjust(left=0.08, right=0.92, top=0.9, bottom=0.15)
                canvas.draw_idle()
                
                global _first_resize
                if _first_resize:
                    _first_resize = False
                    # 首次resize后再次触发更新
                    root.after(100, _resize)
        except:
            pass
    
    root.after_idle(_resize)

# 然后创建和配置画布
canvas = FigureCanvasTkAgg(fig, master=right_frame)
# canvas.draw()

toolbar = NavigationToolbar2Tk(canvas, right_frame)
# toolbar.update()

canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# # 添加强制更新布局的代码
# root.update_idletasks()  # 更新所有pending的图形任务
# on_resize()  # 即调用一次resize
# canvas.draw_idle()  # 使用draw_idle代替draw

# # 在mainloop之前的初始化代码
# root.update()
# root.minsize(root.winfo_width(), root.winfo_height())
# root.update_idletasks()
# on_resize()

# 添加最大化和复原操作
root.after(500, lambda: root.state('zoomed'))  # 500ms后最大化
root.after(1000, lambda: root.state('normal'))  # 1000ms后复原

root.mainloop()
