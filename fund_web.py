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

# CSS美化
st.markdown("""
    <style>
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
        @media only screen and (max-width: 600px) {
            .block-container { padding-top: 1rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important;}
            h1 { font-size: 1.5rem !important; }
            .big-rate-up, .big-rate-down { font-size: 22px !important; }
            .brand-footer { margin-top: 30px; }
            section[data-testid="stSidebar"] { width: 100% !important; }
        }
    </style>
""", unsafe_allow_html=True)


# --- 2. 多用户数据管理系统 ---
def get_data_file_path(username):
    safe_name = username if username else "unknown"
    return f"fund_data_{safe_name}.json"


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
    if not username: return
    file_path = get_data_file_path(username)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存失败: {e}")


# --- 3. 登录逻辑 (修复版) ---
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

            # 🔥 修复核心1：登录瞬间同时完成 ID 设置和数据加载
            if st.button("🚀 进入系统", use_container_width=True, type="primary"):
                if user_input:
                    st.session_state.user_id = user_input
                    st.session_state.data = load_data(user_input)
                    st.rerun()

            st.markdown("---")
            st.caption("Designed by 抖音：绿豆生北国 (ID:32053858729)")

    # 强制停止
    st.stop()

# --- 4. 数据加载与核心计算 ---
current_user = st.session_state.user_id

# 🔥 修复核心2：双重保险
if 'data' not in st.session_state or st.session_state.data is None:
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

# 🔥 修复核心3：安全读取 .get()
holdings = st.session_state.data.get('holdings', {})

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
                "名称": f"{info['name']} ({code})",
                "投入本金": cost,
                "当前市值": market_val,
                "今日涨幅(%)": f"{zhangfu:+.2f}%",
                "今日收益": day_profit,
                "持有收益": market_val - cost,
                "持有收益率": (market_val - cost) / cost * 100 if cost > 0 else 0,
                "更新时间": real_data['更新时间']
            })

total_profit_all = total_assets - total_cost
total_rate = (total_profit_all / total_cost * 100) if total_cost > 0 else 0.0

today_str = datetime.datetime.now().strftime("%Y-%m-%d")
if total_assets > 0:
    if st.session_state.data is not None:
        st.session_state.data['asset_history'][today_str] = total_assets
        save_data(current_user, st.session_state.data)


# --- 新增：删除持仓基金的函数 ---
def delete_holding_fund(fund_code_to_delete):
    if fund_code_to_delete in st.session_state.data['holdings']:
        fund_details = st.session_state.data['holdings'][fund_code_to_delete]

        # 获取实时数据以记录清仓时的市值和份额
        real_data = fund_core.get_fund_real_time_value(fund_code_to_delete)

        if real_data:
            current_price = float(real_data['实时估算值'])
            current_market_value = fund_details['shares'] * current_price

            # 记录“清仓”交易
            rec = {
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type": "清仓",  # 明确标记为清仓操作
                "code": fund_code_to_delete,
                "name": fund_details['name'],
                "amount": current_market_value,  # 记录清仓时的市值
                "shares": fund_details['shares']  # 记录清仓时的份额
            }
            st.session_state.data['transactions'].insert(0, rec)

            # 从持仓中移除基金
            del st.session_state.data['holdings'][fund_code_to_delete]

            save_data(current_user, st.session_state.data)
            st.success(f"基金 {fund_details['name']} ({fund_code_to_delete}) 已清仓并记录。")
            time.sleep(1)  # 暂停1秒让用户看到成功消息
            st.rerun()
        else:
            st.error(f"无法获取基金 {fund_code_to_delete} 的实时数据，清仓失败。")
    else:
        st.warning(f"基金 {fund_code_to_delete} 不在持仓中。")


# --- 5. 侧边栏 ---
with st.sidebar:
    st.header("💰 基金资产管家 Pro")
    st.caption("Designed by 绿豆生北国")
    st.caption(f"当前用户: **{current_user}**")
    st.markdown("---")

    st.markdown("##### 功能导航")
    # 侧边栏导航名称修改，更符合“添加持仓”的语境
    page = st.radio("功能导航", ["🏠 资产看板", "📝 交易明细", "🚀 添加持仓 & 交易"], label_visibility="collapsed")

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
    if st.button("🗑️ 清空所有数据", use_container_width=True):  # 按钮文本修改，避免与单只基金删除混淆
        if os.path.exists(get_data_file_path(current_user)):
            os.remove(get_data_file_path(current_user))
        st.session_state.data = {"holdings": {}, "transactions": [], "asset_history": {}}
        st.rerun()

    st.markdown("---")
    # 🔥 修复核心4：核弹级退出
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.clear()
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
    if st.session_state.data and 'asset_history' in st.session_state.data:
        history_data = st.session_state.data['asset_history']
        if len(history_data) > 1:
            chart_df = pd.DataFrame(list(history_data.items()), columns=['日期', '总资产'])
            chart_df['日期'] = pd.to_datetime(chart_df['日期'])
            st.line_chart(chart_df.set_index('日期'), color="#e63946")
        else:
            st.info("📊 暂无历史数据")
    else:
        st.info("📊 暂无历史数据")

    st.markdown("**📋 持仓明细**")
    if holdings_list:
        # 定义列宽，以适应新的“操作”列
        # 序号, 名称, 投入本金, 当前市值, 今日涨幅(%), 今日收益, 持有收益, 更新时间, 操作
        col_widths = [0.5, 2, 1.2, 1.2, 1, 1.2, 1.2, 1.5, 0.8]
        cols_header = st.columns(col_widths)
        headers = ["序号", "名称", "投入本金", "当前市值", "今日涨幅", "今日收益", "持有收益", "更新时间", "操作"]
        for i, header in enumerate(headers):
            with cols_header[i]:
                st.markdown(f"**{header}**")
        st.markdown("---")  # 分隔线

        for idx, fund_item in enumerate(holdings_list):
            cols_data = st.columns(col_widths)

            # 颜色逻辑：涨红跌绿
            today_change_pct_val = float(fund_item['今日涨幅(%)'].replace('%', ''))
            today_profit_val = fund_item['今日收益']
            holding_profit_val = fund_item['持有收益']

            color_today_change = 'red' if today_change_pct_val > 0 else 'green' if today_change_pct_val < 0 else 'black'
            color_today_profit = 'red' if today_profit_val > 0 else 'green' if today_profit_val < 0 else 'black'
            color_holding_profit = 'red' if holding_profit_val > 0 else 'green' if holding_profit_val < 0 else 'black'

            with cols_data[0]:
                st.write(idx + 1)
            with cols_data[1]:
                st.write(fund_item['名称'])
            with cols_data[2]:
                st.write(f"{fund_item['投入本金']:,.2f}")
            with cols_data[3]:
                st.write(f"{fund_item['当前市值']:,.2f}")
            with cols_data[4]:
                st.markdown(
                    f"<span style='color:{color_today_change}; font-weight:bold;'>{fund_item['今日涨幅(%)']}</span>",
                    unsafe_allow_html=True)
            with cols_data[5]:
                st.markdown(
                    f"<span style='color:{color_today_profit}; font-weight:bold;'>{fund_item['今日收益']:+,.2f}</span>",
                    unsafe_allow_html=True)
            with cols_data[6]:
                st.markdown(
                    f"<span style='color:{color_holding_profit}; font-weight:bold;'>{fund_item['持有收益']:+,.2f}</span>",
                    unsafe_allow_html=True)
            with cols_data[7]:
                st.write(fund_item['更新时间'])
            with cols_data[8]:
                # 添加删除按钮，使用 on_click 和 args 传递参数，确保每次点击都能触发
                st.button("删除", key=f"delete_btn_{fund_item['代码']}", on_click=delete_holding_fund,
                          args=(fund_item['代码'],))

    else:
        st.caption("暂无持仓")

    if auto_refresh:
        time.sleep(5)
        st.rerun()

# ================= 页面 2: 交易明细 =================
elif page == "📝 交易明细":
    st.title("交易流水账本")
    if st.session_state.data and st.session_state.data.get('transactions'):
        trans_df = pd.DataFrame(st.session_state.data['transactions'])
        filter_code = st.text_input("🔍 搜索交易记录", key="history_search")
        if filter_code: trans_df = trans_df[trans_df['code'].str.contains(filter_code)]
        st.dataframe(trans_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无交易记录")

# ================= 页面 3: 深度分析 & 交易 =================
# 页面名称修改，更符合“添加持仓”的语境
elif page == "🚀 添加持仓 & 交易":
    st.title("深度分析 & 交易柜台")

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

            op_tab1, op_tab2 = st.tabs(["🔴 买入/调整持仓", "🟢 卖出"]) # 标签页名称修改

            with op_tab1:
                buy_money = st.number_input("本次买入金额", step=100.0, min_value=0.0, key="buy_input")
                # 新增提示信息
                st.caption("💡 如果您只是想录入已有的持仓，本次买入金额可输入 0。")

                # --- 新增：已持有本金和已持有收益输入框 ---
                initial_principal_default = 0.0
                initial_profit_default = 0.0

                # 如果基金已在持仓中，预填充其当前本金和收益
                if search_code in st.session_state.data['holdings'] and fund_info:
                    current_fund_holding = st.session_state.data['holdings'][search_code]
                    current_price = float(fund_info['实时估算值'])

                    initial_principal_default = current_fund_holding['cost']
                    # 只有当当前价格大于0时，才能计算当前市值和收益，避免除零错误
                    if current_price > 0:
                        current_market_value = current_fund_holding['shares'] * current_price
                        initial_profit_default = current_market_value - current_fund_holding['cost']
                    else:
                        initial_profit_default = 0.0  # 如果价格为0，则收益也视为0

                input_original_principal = st.number_input(
                    "本次买入前，该基金已持有本金 (买入的本金)",
                    value=initial_principal_default,
                    min_value=0.0,
                    key=f"input_original_principal_{search_code}"
                )
                input_existing_profit = st.number_input(
                    "本次买入前，该基金已持有收益 (亏损就是负数)",
                    value=initial_profit_default,
                    key=f"input_existing_profit_{search_code}"
                )
                # --- 新增输入框结束 ---

                if st.button("确认操作", use_container_width=True, type="primary"): # 按钮文本修改
                    if not fund_info:
                        st.error("请先输入正确的基金代码并查询。")
                    elif buy_money < 0: # 理论上 min_value=0 已经避免了，但作为安全检查
                        st.warning("买入金额不能小于0。")
                    else: # fund_info is valid and buy_money >= 0
                        price = float(fund_info['实时估算值'])
                        name = fund_info['名称']

                        # 计算本次买入的份额
                        new_shares_from_buy = buy_money / price if price > 0 else 0.0

                        # 根据用户输入或默认值确定本次买入前的基金状态
                        base_cost_for_fund = input_original_principal
                        # 从本金和收益反推本次买入前的总市值，再计算总份额
                        base_market_value_for_fund = input_original_principal + input_existing_profit
                        base_shares_for_fund = base_market_value_for_fund / price if price > 0 else 0.0

                        # 计算本次买入后的最终总份额和总成本
                        final_shares = base_shares_for_fund + new_shares_from_buy
                        final_cost = base_cost_for_fund + buy_money

                        # 更新持仓数据
                        st.session_state.data['holdings'][search_code] = {
                            'name': name,
                            'shares': final_shares,
                            'cost': final_cost
                        }

                        # 只有当实际有买入金额时才记录为“买入”交易
                        if buy_money > 0:
                            rec = {"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "买入",
                                   "code": search_code, "name": name, "amount": buy_money}
                            st.session_state.data['transactions'].insert(0, rec)
                            st.success(f"买入成功！基金 {name} ({search_code}) 已更新。")
                        else: # buy_money == 0, 视为持仓调整
                            st.success(f"基金 {name} ({search_code}) 持仓数据已调整。")

                        save_data(current_user, st.session_state.data)
                        time.sleep(1)
                        st.rerun()

            with op_tab2:
                if st.session_state.data and 'holdings' in st.session_state.data:
                    my_codes = list(st.session_state.data['holdings'].keys())
                else:
                    my_codes = []

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
                            cost_reduce = curr['cost'] * (sell_shares / curr['shares']) if curr['shares'] > 0 else 0
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
                            st.warning("卖出份额或金额必须大于0。")
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
