# fund_core.py
import requests
import json
import time
import pandas as pd
from datetime import datetime

# ==========================================
# 核心功能: 获取实时估值 (极简高效版)
# ==========================================
def get_fund_real_time_value(fund_code):
    """
    获取单只基金的实时估值
    """
    # 加上时间戳防止缓存
    timestamp = int(time.time() * 1000)
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={timestamp}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "http://fund.eastmoney.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code != 200:
            return None

        content = response.text
        # 解析 jsonpgz(...)
        start_index = content.find('(') + 1
        end_index = content.rfind(')')
        json_str = content[start_index:end_index]
        data = json.loads(json_str)

        result = {
            "代码": data['fundcode'],
            "名称": data['name'],
            "净值日期": data['jzrq'],
            "昨日单位净值": data['dwjz'],
            "实时估算值": data['gsz'],
            "估算涨幅": data['gszzl'] + "%",
            "更新时间": data['gztime']
        }
        return result

    except Exception as e:
        return None

# 占位函数，防止报错
def get_fund_portfolio(fund_code): pass
def get_manager_start_date(fund_code): pass
