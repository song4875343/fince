import streamlit as st
import matplotlib.pyplot as plt
import baostock as bs
import datetime
import os
import json
import matplotlib.font_manager as fm
from matplotlib import font_manager
import platform

# 在文件最开始，其他代码之前设置页面配置
st.set_page_config(layout="wide")

# 根据操作系统设置默认字体
def setup_chinese_font():
    if platform.system() == "Windows":
        font_list = ['Microsoft YaHei', 'SimHei']
    else:
        # Linux/Mac/Cloud 环境使用更通用的字体
        font_list = ['WenQuanYi Micro Hei', 'Noto Sans CJK JP', 'Noto Sans CJK SC', 
                    'Noto Sans CJK TC', 'Heiti TC', 'SimHei', 'DejaVu Sans']
    
    # 遍历字体列表，使用第一个可用的字体
    chinese_font = None
    for font_name in font_list:
        try:
            if any(f.name == font_name for f in font_manager.fontManager.ttflist):
                chinese_font = font_name
                break
        except:
            continue
    
    if chinese_font is None:
        chinese_font = 'DejaVu Sans'  # 使用默认后备字体
    
    plt.rcParams['font.sans-serif'] = [chinese_font] + plt.rcParams['font.sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    return chinese_font

# 替换原来的字体设置代码
setup_chinese_font()

# 初始化session state
if 'stock_history' not in st.session_state:
    st.session_state.stock_history = []
if 'selected_code' not in st.session_state:
    st.session_state.selected_code = ''

# 文件路径处理
DATA_PATH = os.path.join(os.path.dirname(__file__), 'stock_history.json')

# 将回调函数移到文件的前面，在所有函数定义之前





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
        start_date = (end_date_obj - datetime.timedelta(days=7)
                      ).strftime('%Y-%m-%d')

        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close",
            start_date=start_date, end_date=end_date, frequency="d")
        daily_data = rs.get_data()

        # 获取周线数据
        week_start_date = (
            end_date_obj - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
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

    # 根据设备类型调整图表大小和字体大小
    is_mobile = st.session_state.get('is_mobile', True)
    if is_mobile:
        fig = plt.figure(figsize=(5, 3), dpi=400)
        font_size = 9  # 桌面设备上的字体大小
        title_size = 10
        marker_size = 3
    else:
        fig = plt.figure(figsize=(8, 4), dpi=400)
        font_size = 8  # 桌面设备上的字体大小
        title_size = 12
        marker_size = 6

    ax = fig.add_subplot(111)

    # 获取最近的数据（最多3天）
    last_three_days = data['daily'].tail(3)
    num_days = len(last_three_days)

    if num_days == 0:
        st.error("没有找到交易数据")
        return None

    # 获取当前使用的中文字体
    current_font = plt.rcParams['font.sans-serif'][0]
    
    # 设置字体属性时使用当前字体
    font_properties = fm.FontProperties(
        family=current_font,
        weight='light'
    )

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
        ax.bar(i + 1, height, width, bottom=bottom, color=color)
        # 绘制上下影线
        ax.plot([i + 1, i + 1], [low, high], color='black', linewidth=1)

        # 标注OHLC价格和圆点
        ohlc_points = [
            (open_price, 'O'),
            (high, 'H'),
            (low, 'L'),
            (close, 'C')
        ]

        # 在绘制OHLC价格标注时使用新的字体属性
        for price, label in ohlc_points:
            # 绘制圆点
            ax.plot(i + 1, price, 'o', color='blue', markersize=marker_size)
            # 添加价格标注，使用更细的字体
            ax.text(i + 1 + 0.1, price, f'{price:.2f}',
                    color='blue', va='center', ha='left',
                    fontsize=font_size, fontproperties=font_properties)

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

        # 在绘制支撑/压力线标签时也使用新的字体属性
        for price, label, line_color in lines:
            # 绘制短线
            ax.plot([x_start, x_end], [price, price],
                    color=line_color, linestyle='--', alpha=0.5)
            # 添加标签，使用更细的字体
            ax.text(x_end + 0.1, price, f'{label}: {price:.2f}',
                    color=line_color, va='center', ha='left',
                    fontsize=font_size, fontproperties=font_properties)

    # 设置x轴刻度和标签
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(last_three_days['date'].values, rotation=0)  # 使用日期作为标签

    # 设置标题时增加字重和大小
    font_properties_title = font_properties.copy()
    font_properties_title.set_weight('bold')  # 设置字体加粗
    font_properties_title.set_size(title_size)
    
    ax.set_title(f"{data['code']}", 
                 fontproperties=font_properties_title,
                 pad=20)  # 增加标题和图表的间距

    # 设置坐标轴刻度字体
    ax.tick_params(axis='both', which='major', labelsize=font_size)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font_properties)

    # 调整图表边距
    if is_mobile:
        print("is_mobile")
        ax.set_aspect(1.5)
        plt.tight_layout(pad=0.1)
    else:
        print("pc")
        ax.set_aspect(1)
        plt.tight_layout(pad=4)  # 减小 pad 值，让标题有更多空间

    return fig


if __name__ == '__main__':

    # 页面布局代码
    load_stock_list()

    # 使用sidebar进行所有设置
    with st.sidebar:
        st.header("股票信息")
        # 修改输入框的处理方式
        code = st.text_input("股票代码", key='stock_code_input')
        is_mobile = st.checkbox("移动设备模式", value=True, key='is_mobile')
        # st.session_state.is_mobile = is_mobile
        # 当输入框的值改变时，更新 selected_code
        if code != st.session_state.get('selected_code', ''):
            st.session_state.selected_code = code
            # 清除上一次的图表
            if 'current_fig' in st.session_state:
                del st.session_state.current_fig

        date = st.date_input("日期", datetime.date.today(), key='date_input')

        # 添加获取数据按钮
        if st.button("获取数据") or (code and 'current_fig' not in st.session_state):
            if code:
                data = get_stock_data(code, str(st.session_state.date_input))
                if data and not data['daily'].empty:
                    update_stock_history(data['code'], data['name'])
                    save_stock_list()
                    fig = draw_kline(data)
                    if fig:
                        st.session_state.current_fig = fig
            else:
                st.error("请输入股票代码")

        st.header("历史记录")
        selected = st.selectbox(
            "选择历史股票",
            options=st.session_state.stock_history,
            format_func=lambda x: f"{x['name']}({x['code']})",
            key='history_selector'
        )

        # 历史记录选择处理
        if selected and st.session_state.get('stock_code_input') == '':
            st.session_state.selected_code = selected['code'].replace(
                'sh.', '').replace('sz.', '')
            data = get_stock_data(st.session_state.selected_code, str(
                st.session_state.date_input))
            if data and not data['daily'].empty:
                update_stock_history(data['code'], data['name'])
                save_stock_list()
                fig = draw_kline(data)
                if fig:
                    st.session_state.current_fig = fig

        # st.header("显示设置")


    # 主内容区显示图表
    if 'current_fig' in st.session_state:
        # 根据移动设备模式设置不同的CSS样式
        if st.session_state.get('is_mobile', False):
            st.markdown(
                """
                <style>
                    .block-container {
                        padding-top: 1.5rem !important;
                        max-width: 40rem !important;
                        margin: auto !important;
                    }
                    .element-container {
                        width: 100% !important;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.pyplot(st.session_state.current_fig, use_container_width=True)
        else:
            st.markdown(
                """
                <style>
                    .block-container {
                        padding-top: 4rem !important;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.pyplot(st.session_state.current_fig, use_container_width=False)
