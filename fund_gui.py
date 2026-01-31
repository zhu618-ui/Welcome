# fund_gui.py
import sys
import json
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel,
                             QLineEdit, QPushButton, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QAbstractItemView)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

# 引入核心数据获取模块
import fund_core

# 数据存储文件名
DATA_FILE = "my_funds.json"


class FundWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.fund_list = []  # 存储基金代码的列表
        self.load_funds()  # 启动时读取本地保存的基金
        self.init_ui()

        # 启动自动刷新定时器 (每30秒)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_all_data)
        self.timer.start(30000)

        # 启动后立即刷新一次
        QTimer.singleShot(500, self.refresh_all_data)

    def init_ui(self):
        self.setWindowTitle('我的基金看板 V2.0')
        self.resize(600, 500)  # 窗口搞大一点

        # --- 顶部操作区 ---
        top_layout = QHBoxLayout()

        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("输入基金代码 (如 110011)")
        self.input_code.setFixedWidth(200)

        self.btn_add = QPushButton("➕ 添加")
        self.btn_add.clicked.connect(self.add_fund)

        self.btn_refresh = QPushButton("🔄 立即刷新")
        self.btn_refresh.clicked.connect(self.refresh_all_data)

        self.btn_delete = QPushButton("🗑 删除选中")
        self.btn_delete.clicked.connect(self.delete_fund)

        top_layout.addWidget(self.input_code)
        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_delete)
        top_layout.addStretch()  # 弹簧，把按钮顶到左边
        top_layout.addWidget(self.btn_refresh)

        # --- 中间表格区 ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['代码', '名称', '实时估值', '涨跌幅', '更新时间'])

        # 表格美化
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 名称列自动拉伸
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)  # 禁止编辑
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)  # 选中整行

        # --- 底部状态栏 ---
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")

        # --- 总布局 ---
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.table)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def load_funds(self):
        """从本地文件读取基金列表"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.fund_list = json.load(f)
            except:
                self.fund_list = []

    def save_funds(self):
        """保存基金列表到本地文件"""
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.fund_list, f)
        except Exception as e:
            print(f"保存失败: {e}")

    def add_fund(self):
        """添加基金"""
        code = self.input_code.text().strip()
        if not code:
            return
        if code in self.fund_list:
            QMessageBox.warning(self, "提示", "这个基金已经在列表里了！")
            return

        # 先尝试获取一次数据，确认代码有效
        self.status_label.setText(f"正在验证基金 {code}...")
        QApplication.processEvents()

        data = fund_core.get_fund_real_time_value(code)
        if data:
            self.fund_list.append(code)
            self.save_funds()  # 保存
            self.input_code.clear()
            self.refresh_all_data()  # 刷新显示
            self.status_label.setText(f"成功添加: {data['名称']}")
        else:
            QMessageBox.critical(self, "错误", "无法获取数据，请检查基金代码是否正确！")
            self.status_label.setText("添加失败")

    def delete_fund(self):
        """删除选中的基金"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先点击选择要删除的行")
            return

        # 获取当前行的基金代码（第0列）
        code = self.table.item(current_row, 0).text()

        confirm = QMessageBox.question(self, "确认", f"确定要删除 {code} 吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm == QMessageBox.StandardButton.Yes:
            if code in self.fund_list:
                self.fund_list.remove(code)
                self.save_funds()
                self.refresh_all_data()

    def refresh_all_data(self):
        """刷新所有基金数据"""
        if not self.fund_list:
            self.table.setRowCount(0)
            return

        self.status_label.setText("正在刷新所有数据...")
        self.table.setRowCount(len(self.fund_list))  # 设置行数

        for row, code in enumerate(self.fund_list):
            data = fund_core.get_fund_real_time_value(code)

            if data:
                # 准备数据
                items = [
                    data['代码'],
                    data['名称'],
                    data['实时估算值'],
                    data['估算涨幅'],
                    data['更新时间']
                ]

                # 颜色逻辑：涨红跌绿
                zhangfu = data['估算涨幅']
                text_color = QColor("black")
                if "-" in zhangfu:
                    text_color = QColor("green")
                elif zhangfu != "0.00%":
                    text_color = QColor("red")

                # 填入表格
                for col, text in enumerate(items):
                    item = QTableWidgetItem(str(text))
                    # 涨跌幅和估值列设置颜色
                    if col in [2, 3]:
                        item.setForeground(text_color)
                        item.setFont(QFont("Arial", 10, QFont.Weight.Bold))

                    # 内容居中
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, col, item)
            else:
                self.table.setItem(row, 0, QTableWidgetItem(code))
                self.table.setItem(row, 1, QTableWidgetItem("获取失败"))

        self.status_label.setText(f"刷新完成 - 共 {len(self.fund_list)} 只基金")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FundWindow()
    window.show()
    sys.exit(app.exec())
