# fund_web.py
import streamlit as st
import pandas as pd
import json
import os
import datetime
import requests
import time
import fund_core  # 复用核心代码

# --- 1. 页面配置 (保持宽屏) ---
st.set_page_config(
    page_title="基金资产管家 Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS美化 (电脑端经典 + 手机端适配)
st.markdown("""
    <style>
        /* ================= 电脑端默认样式 (保持原样) ================= */
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }

        .brand-footer {
            text-align: center; color: #aaa; font-size: 13px;
            margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee;
        }

        .big-rate-up { color: #e63946; font-size: 28px; font-weight: bold; }
        .big-rate-down { color: #28a745; font-size: 28px; font-weight: bold; }

        .status-badge {
            background-color: #fff; color: #555; padding: 5px 15px; border-radius: 20px;
            font-size: 13px; font-weight: 600; border: 1px solid #eee;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .status-dot {
            height: 8px; width: 8px; background-color: #28a745;
            border-radius: 50%; display: inline-block; margin-right: 6px;
        }

        [data-testid="stSidebarNav"] { display: none; }

        /* ================= 📱 手机端专属适配 (Media Query) ================= */
        @media only screen and (max-width: 600px) {
            /* 1. 缩小顶部间距，手机寸土寸金 */
            .block-container { 
                padding-top: 1rem !important; 
                padding-left: 0.5rem !important; 
                padding-right: 0.5rem !important;
            }

            /* 2. 标题字号调小，防止换行 */
            h1 { font-size: 1.5rem !important; }

            /* 3. 涨跌幅大数字调小 */
            .big-rate-up, .big-rate-down { font-size: 22px !important; }

            /* 4. 调整底部水印间距 */
            .brand-footer { margin-top: 30px; }

            /* 5. 隐藏侧边栏的某些大留白 */
            section[data-testid="stSidebar"] { width: 100% !important; }
        }
    </style>
""", unsafe_allow_html=True)


# --- 2. 多用户数据管理系统 ---
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

if not st.session_state.user_id:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.title("🔐 基金资产管家 Pro")
            st.markdown("---")
            user_input = st.text_input("请输入 ID / 昵称", placeholder="例如：zhu618")
            if st.button("🚀 进入系统", use_container_width=True, type="primary"):
                if user_input:
                    st.session_state.user_id = user_input
                    st.rerun()
            st.markdown("---")
            st.caption("Designed by 抖音：绿豆生北国 (ID:32053858729)")
    st.stop()

# --- 4. 数据加载与核心计算 ---
current_user = st.session_state.user_id
if 'data' not in st.session_state:
    st.session_state.data = load_data(current_user)


@st.cache_data(ttl=300)
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
                "名称": f"{info['name']} ({code})",  # 电脑端保留完整信息
                "投入本金": cost,
                "当前市值": market_val,
                "今日涨幅(%)": f"{zhangfu:+.2f}%",
                "今日收益": day_profit,
                "持有收益": market_val - cost,
                "持有收益率": (market_val - cost) / cost * 100 if cost > 0 else 0
            })

total_profit_all = total_assets - total_cost
total_rate = (total_profit_all / total_cost * 100) if total_cost > 0 else 0.0

today_str = datetime.datetime.now().strftime("%Y-%m-%d")
if total_assets > 0:
    st.session_state.data['asset_history'][today_str] = total_assets
    save_data(current_user, st.session_state.data)

# --- 5. 侧边栏 ---
with st.sidebar:
    st.header("💰 基金资产管家 Pro")
    st.caption("Designed by 绿豆生北国")
    st.caption(f"当前用户: **{current_user}**")
    st.markdown("---")

    st.markdown("##### 功能导航")
    page = st.radio("功能导航", ["🏠 资产看板", "📝 交易明细", "🚀 深度分析 & 交易"], label_visibility="collapsed")

    st.markdown("---")

    auto_refresh = False
    if page == "🏠 资产看板":
        st.success("🟢 实时监控模式")
        auto_refresh = st.toggle("⚡ 开启5秒自动刷新", value=False)
        if st.button("🔄 立即刷新", use_container_width=True):
            st.rerun()
    else:
        st.info("⏸️ 自动刷新已暂停")

    st.markdown("---")
    st.warning("⚠️ 数据管理")
    if st.button("🗑️ 清空数据", use_container_width=True):
        if os.path.exists(get_data_file_path(current_user)):
            os.remove(get_data_file_path(current_user))
        st.session_state.data = {"holdings": {}, "transactions": [], "asset_history": {}}
        st.rerun()

    st.markdown("---")
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.data = None
        st.rerun()

# --- 6. 页面逻辑 ---

# ================= 页面 1: 资产看板 =================
if page == "🏠 资产看板":
    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.title("资产看板")
    with col_status:
        if latest_update_time != "等待刷新...":
            st.markdown(
                f'<div style="text-align:right; padding-top:15px;"><span class="status-badge"><span class="status-dot"></span>更新: {latest_update_time}</span></div>',
                unsafe_allow_html=True)

    # 电脑端：一行4个；手机端：自动堆叠为4行
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总资产", f"{total_assets:,.2f}")
    with col2:
        st.metric("今日收益", f"{today_profit:+,.2f}", delta_color="inverse", delta="今日变动")
    with col3:
        st.metric("持有收益", f"{total_profit_all:+,.2f}", delta_color="inverse")
    with col4:
        st.metric("总收益率", f"{total_rate:+.2f}%", delta_color="inverse")

    st.divider()

    st.markdown("**📈 财富净值走势**")
    history_data = st.session_state.data['asset_history']
    if len(history_data) > 1:
        chart_df = pd.DataFrame(list(history_data.items()), columns=['日期', '总资产'])
        chart_df['日期'] = pd.to_datetime(chart_df['日期'])
        st.line_chart(chart_df.set_index('日期'), color="#e63946")
    else:
        st.info("📊 暂无历史数据")

    st.markdown("**📋 持仓明细**")
    if holdings_list:
        # 保持完整列，手机端 Streamlit 会自动提供横向滚动条
        df = pd.DataFrame(holdings_list)
        df.insert(0, '序号', range(1, 1 + len(df)))
        view_df = df[["序号", "名称", "投入本金", "当前市值", "今日涨幅(%)", "今日收益", "持有收益", "持有收益率"]]


        def highlight(val):
            color = 'red' if val > 0 else 'green'
            if val == 0: color = 'black'
            return f'color: {color}; font-weight: bold'


        styled_df = view_df.style \
            .map(highlight, subset=["今日收益", "持有收益", "持有收益率"]) \
            .map(lambda x: highlight(float(x.replace('%', ''))), subset=["今日涨幅(%)"]) \
            .format("{:,.2f}", subset=["投入本金", "当前市值", "今日收益", "持有收益"]) \
            .format("{:+.2f}%", subset=["持有收益率"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.caption("暂无持仓")

    if auto_refresh:
        time.sleep(5)
        st.rerun()

# ================= 页面 2: 交易明细 =================
elif page == "📝 交易明细":
    st.title("交易流水账本")
    if st.session_state.data['transactions']:
        trans_df = pd.DataFrame(st.session_state.data['transactions'])
        filter_code = st.text_input("🔍 搜索交易记录", key="history_search")
        if filter_code: trans_df = trans_df[trans_df['code'].str.contains(filter_code)]
        st.dataframe(trans_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无交易记录")

# ================= 页面 3: 深度分析 & 交易 =================
elif page == "🚀 深度分析 & 交易":
    st.title("深度分析 & 交易柜台")

    # 电脑端：左右布局；手机端：自动上下堆叠
    col_left, col_right = st.columns([1, 2])

    with col_left:
        with st.container(border=True):
            st.markdown("#### 🕹 交易柜台")
            search_code = st.text_input("输入代码", placeholder="如 110011")

            fund_info = None
            if len(search_code) == 6:
                with st.spinner("查询中..."):
                    fund_info = fund_core.get_fund_real_time_value(search_code)

                if fund_info:
                    st.success(f"已锁定: {fund_info['名称']}")
                    st.metric("实时估值", fund_info['实时估算值'], fund_info['估算涨幅'], delta_color="inverse")
                else:
                    st.error("❌ 查无此基")

            st.divider()

            op_tab1, op_tab2 = st.tabs(["🔴 买入", "🟢 卖出"])

            with op_tab1:
                buy_money = st.number_input("买入金额", step=100.0, key="buy_input")
                if st.button("确认买入", use_container_width=True, type="primary"):
                    if fund_info and buy_money > 0:
                        price = float(fund_info['实时估算值'])
                        shares = buy_money / price
                        name = fund_info['名称']
                        if search_code in st.session_state.data['holdings']:
                            st.session_state.data['holdings'][search_code]['shares'] += shares
                            st.session_state.data['holdings'][search_code]['cost'] += buy_money
                        else:
                            st.session_state.data['holdings'][search_code] = {'name': name, 'shares': shares,
                                                                              'cost': buy_money}

                        rec = {"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "买入",
                               "code": search_code, "name": name, "amount": buy_money}
                        st.session_state.data['transactions'].insert(0, rec)
                        save_data(current_user, st.session_state.data)
                        st.success(f"买入成功！")
                        time.sleep(1)
                        st.rerun()

            with op_tab2:
                my_codes = list(st.session_state.data['holdings'].keys())
                if my_codes:
                    sell_code_select = st.selectbox("选择持仓", my_codes, key="sell_select")
                    curr = st.session_state.data['holdings'][sell_code_select]
                    curr_info = fund_core.get_fund_real_time_value(sell_code_select)
                    curr_price = float(curr_info['实时估算值']) if curr_info else 0
                    curr_val = curr['shares'] * curr_price
                    st.caption(f"持仓: {curr['shares']:.2f} 份 | 市值: {curr_val:.2f} 元")

                    sell_mode = st.radio("卖出方式", ["按金额", "按份额", "全部卖出"], horizontal=True)
                    sell_shares = 0.0
                    if sell_mode == "全部卖出":
                        sell_shares = curr['shares']
                    elif sell_mode == "按金额":
                        sell_amount = st.number_input("卖出金额 (元)", min_value=0.0, max_value=curr_val)
                        if curr_price > 0: sell_shares = sell_amount / curr_price
                    elif sell_mode == "按份额":
                        sell_shares = st.number_input("卖出份额", min_value=0.0, max_value=curr['shares'])

                    if st.button("确认卖出", use_container_width=True):
                        if sell_shares > 0:
                            cost_reduce = curr['cost'] * (sell_shares / curr['shares'])
                            curr['shares'] -= sell_shares
                            curr['cost'] -= cost_reduce
                            if curr['shares'] < 0.01: del st.session_state.data['holdings'][sell_code_select]

                            rec = {"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "卖出",
                                   "code": sell_code_select, "name": curr['name'], "amount": sell_shares * curr_price}
                            st.session_state.data['transactions'].insert(0, rec)
                            save_data(current_user, st.session_state.data)
                            st.success("卖出成功！")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.warning("暂无持仓可卖")

    with col_right:
        if len(search_code) == 6 and fund_info:
            st.markdown(f"#### 📊 {fund_info['名称']} 深度分析")

            with st.spinner("加载业绩走势..."):
                chart_df = get_fund_history_data(search_code, days=30)
                if chart_df is not None and not chart_df.empty:
                    display_df = chart_df.copy()
                    start_val = display_df['DWJZ'].iloc[0]
                    display_df['本基金'] = (display_df['DWJZ'] - start_val) / start_val * 100
                    total_change = display_df['本基金'].iloc[-1]

                    col_rate, col_text = st.columns([1, 3])
                    with col_rate:
                        if total_change > 0:
                            st.markdown(f'<div class="big-rate-up">+{total_change:.2f}%</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="big-rate-down">{total_change:.2f}%</div>', unsafe_allow_html=True)
                        st.caption("近1月涨跌幅")

                    st.line_chart(display_df.set_index('FSRQ')['本基金'], color="#2979ff")

                    st.divider()
                    st.subheader("📜 历史净值列表")
                    display_df['涨跌幅'] = display_df['DWJZ'].pct_change() * 100
                    display_df['FSRQ_STR'] = display_df['FSRQ'].dt.strftime('%Y-%m-%d')
                    show_df = display_df.sort_values('FSRQ', ascending=False)[['FSRQ_STR', '涨跌幅', 'DWJZ']]


                    def color_v(val):
                        c = 'red' if val > 0 else 'green'
                        if val == 0: c = 'black'
                        return f'color: {c}; font-weight: bold'


                    st.dataframe(
                        show_df.style.map(color_v, subset=['涨跌幅']).format("{:+.2f}%", subset=['涨跌幅']).format(
                            "{:.4f}", subset=['DWJZ']),
                        use_container_width=True, hide_index=True,
                        column_config={"FSRQ_STR": "日期", "涨跌幅": "日涨跌幅", "DWJZ": "单位净值"}
                    )
                else:
                    st.warning("暂无历史数据")
        else:
            st.info("👈 请在左侧输入基金代码")

# --- 7. 底部版权 ---
st.markdown("""
    <div class="brand-footer">
        Designed by 抖音：<b>绿豆生北国</b> (ID: 32053858729)
    </div>
""", unsafe_allow_html=True)
