import streamlit as st
import matplotlib.pyplot as plt
import baostock as bs
import datetime
import os
import json
import matplotlib.font_manager as fm

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']  # 按优先级尝试字体
plt.rcParams['axes.unicode_minus'] = False

# 初始化session state
if 'stock_history' not in st.session_state:
    st.session_state.stock_history = []
if 'selected_code' not in st.session_state:
    st.session_state.selected_code = ''

# 文件路径处理
DATA_PATH = os.path.join(os.path.dirname(__file__), 'stock_history.json')

# 将回调函数移到文件的前面，在所有函数定义之前
def on_stock_select():
    print('zhxing')
    if st.session_state.history_selector:
        selected = st.session_state.history_selector
        st.session_state.selected_code = selected['code'].replace('sh.', '').replace('sz.', '')
        # 自动获取数据并显示
        data = get_stock_data(st.session_state.selected_code, str(st.session_state.date_input))
        print(data)
        if data:
            update_stock_history(data['code'], data['name'])
            save_stock_list()
            fig = draw_kline(data)
            st.pyplot(fig)

def load_stock_list():
    try:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                st.session_state.stock_history = json.load(f)
    except Exception as e:
        st.error(f"加载股票列表失败: {e}")

def save_stock_list():
    try:
        with open(DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.stock_history, f, ensure_ascii=False)
    except Exception as e:
        st.error(f"保存股票列表失败: {e}")

def update_stock_history(code, name):
    history = st.session_state.stock_history
    # 移除重复记录
    history = [s for s in history if s['code'] != code]
    # 添加新记录到开头
    history.insert(0, {'code': code, 'name': name})
    # 保留最近5条
    st.session_state.stock_history = history[:5]

def calculate_pivot_points(high, low, close, open_price):
    pivot = (high + low + close) / 3
    return {
        'pivot': pivot,
        'r1': (2 * pivot) - low,
        'r2': pivot + (high - low),
        'r3': high + 2 * (pivot - low),
        's1': (2 * pivot) - high,
        's2': pivot - (high - low),
        's3': low - 2 * (high - pivot)
    }

def get_stock_data(code, end_date):
    try:
        # 格式化股票代码
        code = f'sh.{code}' if code.startswith('6') else f'sz.{code}'
        
        bs.login()
        # 获取股票基本信息
        rs = bs.query_stock_basic(code=code)
        stock_info = rs.get_data()
        if stock_info.empty:
            st.error("没有找到股票信息")
            return None
        
        # 获取日线数据
        end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        start_date = (end_date_obj - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close",
            start_date=start_date, end_date=end_date, frequency="d")
        daily_data = rs.get_data()
        
        # 获取周线数据
        week_start_date = (end_date_obj - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close",
            start_date=week_start_date, end_date=end_date, frequency="w")
        weekly_data = rs.get_data()
        
        return {
            'daily': daily_data,
            'weekly': weekly_data,
            'name': stock_info['code_name'][0],
            'code': code
        }
    except Exception as e:
        st.error(str(e))
        return None
    finally:
        bs.logout()

def draw_kline(data):
    # 使用 session state 中的移动设备模式设置
    is_mobile = st.session_state.get('is_mobile', False)
    
    # 根据设备类型调整图表大小和字体大小
    if is_mobile:
        fig = plt.figure(figsize=(2.8, 1.52), dpi=400)
        font_size = 4  # 移动设备上的字体大小
        title_size = 6
        marker_size = 2
    else:
        fig = plt.figure(figsize=(7, 3.8), dpi=400)
        font_size = 8  # 桌面设备上的字体大小
        title_size = 10
        marker_size = 4
    
    ax = fig.add_subplot(111)
    
    # 获取最近的数据（最多3天）
    last_three_days = data['daily'].tail(3)
    num_days = len(last_three_days)
    
    if num_days == 0:
        st.error("没有找到交易数据")
        return None
    
    # 绘制日K线
    for i, (_, row) in enumerate(last_three_days.iterrows()):
        open_price = float(row['open'])
        close = float(row['close'])
        high = float(row['high'])
        low = float(row['low'])
        
        # 计算枢轴点
        pp = calculate_pivot_points(high, low, close, open_price)
        
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
            ax.plot(i+1, price, 'o', color='blue', markersize=marker_size)
            # 添加价格标注
            ax.text(i+1 + 0.1, price, f'{price:.2f}', 
                   color='blue', va='center', ha='left', fontsize=font_size)
        
        # 为每天绘制独立的支撑位和压力位线条
        lines = [
            (pp['r3'], 'R3', 'red'),
            (pp['r2'], 'R2', 'red'),
            (pp['r1'], 'R1', 'red'),
            (pp['pivot'], 'P', 'black'),
            (pp['s1'], 'S1', 'green'),
            (pp['s2'], 'S2', 'green'),
            (pp['s3'], 'S3', 'green')
        ]
        
        # 计算线条的开始和结束位置
        x_start = i + 1 - 0.2
        x_end = i + 1 + 0.2
        
        for price, label, line_color in lines:
            # 绘制短线
            ax.plot([x_start, x_end], [price, price], 
                   color=line_color, linestyle='--', alpha=0.5)
            # 添加标签
            ax.text(x_end + 0.1, price, f'{label}: {price:.2f}', 
                   color=line_color, va='center', ha='left', fontsize=font_size)

    # 设置标题
    ax.set_title(f"{data['name']}({data['code']}) 最近价格走势", 
                 fontfamily='Microsoft YaHei', fontsize=title_size)
    
    # 设置x轴标签字体大小
    ax.tick_params(axis='both', which='major', labelsize=font_size)
    
    # 调整图表边距
    if is_mobile:
        plt.tight_layout(pad=0.5)  # 移动设备使用更小的边距
    else:
        plt.tight_layout(pad=2)
    
    return fig

# 页面布局代码
st.set_page_config(layout="wide")
load_stock_list()

# 使用sidebar进行所有设置
with st.sidebar:
    st.header("股票信息")
    code = st.text_input("股票代码", key='stock_code_input', 
                       value=st.session_state.selected_code)
    st.session_state.selected_code = code
    
    date = st.date_input("日期", datetime.date.today(), key='date_input')
    
    # st.header("价格输入")
    # open_price = st.number_input("开盘价", key='open')
    # high = st.number_input("最高价", key='high')
    # low = st.number_input("最低价", key='low')
    # close = st.number_input("收盘价", key='close')
    
    # if st.button("计算枢轴点"):
    #     result = calculate_pivot_points(high, low, close, open_price)
    #     st.write(f"枢轴点(P): {result['pivot']:.2f}")
    #     st.write(f"压力位1(R1): {result['r1']:.2f}")
    #     st.write(f"压力位2(R2): {result['r2']:.2f}")
    #     st.write(f"压力位3(R3): {result['r3']:.2f}")
    #     st.write(f"支撑位1(S1): {result['s1']:.2f}")
    #     st.write(f"支撑位2(S2): {result['s2']:.2f}")
    #     st.write(f"支撑位3(S3): {result['s3']:.2f}")
    
    st.header("历史记录")
    selected = st.selectbox(
        "选择历史股票",
        options=st.session_state.stock_history,
        format_func=lambda x: f"{x['name']}({x['code']})",
        key='history_selector'
    )
    
    # 直接在选择后进行处理
    if selected:
        st.session_state.selected_code = selected['code'].replace('sh.', '').replace('sz.', '')
        data = get_stock_data(st.session_state.selected_code, str(st.session_state.date_input))
        if data and not data['daily'].empty:  # 确保有数据
            update_stock_history(data['code'], data['name'])
            save_stock_list()
            fig = draw_kline(data)
            if fig:  # 只有在成功创建图表时才显示
                st.pyplot(fig)
        else:
            st.error("选择的日期没有交易数据")

    st.header("显示设置")
    is_mobile = st.checkbox("移动设备模式", value=False, key='is_mobile')

# 主内容区显示图表
if 'fig' in locals():
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1rem !important;
            }
            @media (max-width: 768px) {
                /* 移动设备样式 */
                .element-container {
                    width: 40vw !important;
                    margin: auto;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # 根据移动设备模式选择显示方式
    if st.session_state.get('is_mobile', False):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.pyplot(fig, use_container_width=True)
    else:
        st.pyplot(fig, use_container_width=False)

