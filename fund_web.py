# fund_web.py
import streamlit as st
import pandas as pd
import json
import os
import datetime
import requests
import time
import fund_core  # 复用核心代码

# --- 1. 页面配置 (针对移动端优化) ---
st.set_page_config(
    page_title="基金资产管家 Pro",
    page_icon="💰",
    layout="wide",  # 虽然是wide，但我们会用代码控制手机端显示
    initial_sidebar_state="auto"
)

# CSS美化 (手机端适配 + 品牌展示)
st.markdown("""
    <style>
        /* 手机端字体优化 */
        .block-container { padding-top: 1rem; padding-bottom: 2rem; }
        h1 { font-size: 1.8rem !important; }

        /* 品牌水印 */
        .brand-watermark {
            color: #ccc; font-size: 0.8rem; text-align: center; margin-top: 20px;
        }

        /* 状态徽章 */
        .status-badge {
            background-color: #f0f2f6; color: #555; padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600; border: 1px solid #ddd;
        }

        /* 涨跌幅大数字 */
        .big-rate-up { color: #e63946; font-size: 24px; font-weight: bold; }
        .big-rate-down { color: #28a745; font-size: 24px; font-weight: bold; }

        /* 隐藏默认导航，防止误触 */
        [data-testid="stSidebarNav"] { display: none; }
    </style>
""", unsafe_allow_html=True)


# --- 2. 多用户数据管理系统 ---
# 这里的逻辑是：文件名 = fund_data_{用户名}.json
def get_data_file_path(username):
    return f"fund_data_{username}.json"


def load_data(username):
    file_path = get_data_file_path(username)
    default_data = {"holdings": {}, "transactions": [], "asset_history": {}}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "asset_history" not in data: data["asset_history"] = {}
                return data
        except:
            return default_data
    return default_data


def save_data(username, data):
    file_path = get_data_file_path(username)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存失败: {e}")


# --- 3. 登录逻辑 ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# 如果未登录，显示登录页
if not st.session_state.user_id:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 基金资产管家 Pro")
        st.info("👋 欢迎！请输入您的专属 ID 以访问资产。")
        user_input = st.text_input("请输入 ID / 手机号 / 昵称", placeholder="例如：zhu618")

        if st.button("🚀 进入系统", use_container_width=True, type="primary"):
            if user_input:
                st.session_state.user_id = user_input
                st.rerun()
            else:
                st.warning("ID 不能为空")

        st.markdown("---")
        st.caption("网页归抖音：**绿豆生北国**（id:32053858729）所有")
    st.stop()  # 停止执行后面的代码，直到登录

# --- 4. 已登录：加载用户数据 ---
current_user = st.session_state.user_id
if 'data' not in st.session_state:
    st.session_state.data = load_data(current_user)


# --- 5. 核心计算 (复用逻辑) ---
@st.cache_data(ttl=300)  # 缓存时间改为5分钟，节省资源
def get_fund_history_data(code, days=30):
    try:
        page_size = days + 20
        url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize={page_size}"
        headers = {"Referer": "http://fund.eastmoney.com/"}
        res = requests.get(url, headers=headers)
        data = res.json()
        if data['Data']['LSJZList']:
            df = pd.DataFrame(data['Data']['LSJZList'])
            df['FSRQ'] = pd.to_datetime(df['FSRQ'])
            df['DWJZ'] = df['DWJZ'].astype(float)
            df = df.sort_values('FSRQ')
            start_date = datetime.datetime.now() - datetime.timedelta(days=days)
            df = df[df['FSRQ'] >= start_date]
            return df[['FSRQ', 'DWJZ']]
    except:
        return None
    return None


total_assets = 0.0
total_cost = 0.0
today_profit = 0.0
holdings_list = []
latest_update_time = "等待刷新..."

holdings = st.session_state.data['holdings']
if holdings:
    for code, info in holdings.items():
        real_data = fund_core.get_fund_real_time_value(code)
        if real_data:
            curr_price = float(real_data['实时估算值'])
            zhangfu = float(real_data['估算涨幅'].replace('%', ''))
            latest_update_time = real_data['更新时间']
            market_val = info['shares'] * curr_price
            cost = info['cost']
            day_profit = market_val * (zhangfu / 100)
            total_assets += market_val
            total_cost += cost
            today_profit += day_profit
            holdings_list.append({
                "代码": code,
                "名称": info['name'],  # 手机端精简，不显示代码在名称里
                "成本": cost,
                "市值": market_val,
                "涨幅": f"{zhangfu:+.2f}%",
                "今日": day_profit,
                "总收益": market_val - cost,
                "收益率": (market_val - cost) / cost * 100 if cost > 0 else 0
            })

today_str = datetime.datetime.now().strftime("%Y-%m-%d")
if total_assets > 0:
    st.session_state.data['asset_history'][today_str] = total_assets
    save_data(current_user, st.session_state.data)

# --- 6. 侧边栏 (包含登出功能) ---
with st.sidebar:
    st.title("💰 资产管家 Pro")
    st.caption(f"当前用户: **{current_user}**")
    st.caption("抖音号: 32053858729")
    st.markdown("---")

    page = st.radio("功能导航", ["🏠 资产看板", "📝 交易明细", "🚀 交易与分析"])

    st.markdown("---")
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.data = None
        st.rerun()

# --- 7. 页面逻辑 ---

# ================= 页面 1: 资产看板 =================
if page == "🏠 资产看板":
    # 顶部标题栏
    c1, c2 = st.columns([2, 1])
    with c1:
        st.title("资产看板")
    with c2:
        if latest_update_time != "等待刷新...":
            st.caption(f"更新: {latest_update_time}")
            if st.button("🔄", key="refresh_btn"): st.rerun()

    # 🔥 手机端优化：使用 2x2 布局显示指标，而不是一行4个
    total_profit_all = total_assets - total_cost
    total_rate = (total_profit_all / total_cost * 100) if total_cost > 0 else 0.0

    # 第一行指标
    m1, m2 = st.columns(2)
    with m1:
        st.metric("总资产", f"{total_assets:,.0f}")  # 去掉小数位，节省空间
    with m2:
        st.metric("今日收益", f"{today_profit:+,.0f}", delta_color="inverse")

    # 第二行指标
    m3, m4 = st.columns(2)
    with m3:
        st.metric("总收益", f"{total_profit_all:+,.0f}", delta_color="inverse")
    with m4:
        st.metric("总收益率", f"{total_rate:+.2f}%", delta_color="inverse")

    st.divider()

    st.subheader("📈 财富走势")
    history_data = st.session_state.data['asset_history']
    if len(history_data) > 1:
        chart_df = pd.DataFrame(list(history_data.items()), columns=['日期', '总资产'])
        chart_df['日期'] = pd.to_datetime(chart_df['日期'])
        st.line_chart(chart_df.set_index('日期'), color="#e63946")
    else:
        st.info("暂无历史数据")

    st.subheader("📋 持仓明细")
    if holdings_list:
        df = pd.DataFrame(holdings_list)
        # 🔥 手机端优化：只展示最关键的列
        view_df = df[["名称", "市值", "今日", "收益率"]]


        def highlight(val):
            color = 'red' if val > 0 else 'green'
            if val == 0: color = 'black'
            return f'color: {color}; font-weight: bold'


        st.dataframe(
            view_df.style.map(highlight, subset=["今日", "收益率"])
            .format("{:,.0f}", subset=["市值", "今日"])  # 手机端去掉小数
            .format("{:+.2f}%", subset=["收益率"]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("暂无持仓")

    st.markdown('<div class="brand-watermark">抖音：绿豆生北国 (ID:32053858729)</div>', unsafe_allow_html=True)

# ================= 页面 2: 交易明细 =================
elif page == "📝 交易明细":
    st.title("交易流水")
    if st.session_state.data['transactions']:
        trans_df = pd.DataFrame(st.session_state.data['transactions'])
        # 手机端精简列
        show_trans = trans_df[['time', 'name', 'type', 'amount']]
        st.dataframe(
            show_trans,
            use_container_width=True,
            hide_index=True,
            column_config={"time": "时间", "name": "名称", "type": "操作", "amount": "金额"}
        )
    else:
        st.info("暂无记录")

# ================= 页面 3: 交易与分析 =================
elif page == "🚀 交易与分析":
    st.title("交易柜台")

    search_code = st.text_input("输入基金代码", placeholder="如 110011")
    fund_info = None

    if len(search_code) == 6:
        with st.spinner("查找中..."):
            fund_info = fund_core.get_fund_real_time_value(search_code)

        if fund_info:
            st.success(f"{fund_info['名称']}")
            c_val, c_rate = st.columns(2)
            with c_val:
                st.metric("估值", fund_info['实时估算值'])
            with c_rate:
                st.metric("涨幅", fund_info['估算涨幅'], delta_color="inverse")
        else:
            st.error("❌ 未找到该代码")

    st.divider()

    tab1, tab2 = st.tabs(["买入", "卖出"])

    with tab1:
        buy_money = st.number_input("买入金额", step=100.0)
        if st.button("确认买入", type="primary", use_container_width=True):
            if fund_info and buy_money > 0:
                price = float(fund_info['实时估算值'])
                shares = buy_money / price
                name = fund_info['名称']
                if search_code in st.session_state.data['holdings']:
                    st.session_state.data['holdings'][search_code]['shares'] += shares
                    st.session_state.data['holdings'][search_code]['cost'] += buy_money
                else:
                    st.session_state.data['holdings'][search_code] = {'name': name, 'shares': shares, 'cost': buy_money}

                rec = {"time": datetime.datetime.now().strftime("%m-%d %H:%M"), "type": "买入", "code": search_code,
                       "name": name, "amount": buy_money}
                st.session_state.data['transactions'].insert(0, rec)
                save_data(current_user, st.session_state.data)
                st.success("买入成功！")
                time.sleep(1)
                st.rerun()

    with tab2:
        my_codes = list(st.session_state.data['holdings'].keys())
        if my_codes:
            sell_code = st.selectbox("选择持仓", my_codes)
            curr = st.session_state.data['holdings'][sell_code]
            st.caption(f"持有: {curr['shares']:.2f} 份")

            if st.button("全部卖出", type="primary", use_container_width=True):
                # 简单处理：全部卖出
                curr_info = fund_core.get_fund_real_time_value(sell_code)
                price = float(curr_info['实时估算值']) if curr_info else 1.0
                amount = curr['shares'] * price

                del st.session_state.data['holdings'][sell_code]
                rec = {"time": datetime.datetime.now().strftime("%m-%d %H:%M"), "type": "卖出", "code": sell_code,
                       "name": curr['name'], "amount": amount}
                st.session_state.data['transactions'].insert(0, rec)
                save_data(current_user, st.session_state.data)
                st.success("卖出成功！")
                time.sleep(1)
                st.rerun()
        else:
            st.info("无持仓")
