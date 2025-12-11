import sys
import os
import platform
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "一键查看当前 Django 项目运行环境、标准库与第三方库"

    def handle(self, *args, **options):
        py_ver = platform.python_version()
        venv = os.environ.get("VIRTUAL_ENV", "未使用虚拟环境")
        py_exec = sys.executable
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 已安装第三方库（pip list）
        pkgs = subprocess.check_output(
            [py_exec, "-m", "pip", "list"],
            universal_newlines=True
        )

        # 标准库（按文件夹名粗略过滤）
        stdlib_path = os.path.join(os.path.dirname(py_exec), "lib")
        std_modules = []
        if os.path.isdir(stdlib_path):
            for nm in os.listdir(stdlib_path):
                if nm.endswith(".py") or os.path.isdir(os.path.join(stdlib_path, nm)):
                    std_modules.append(nm.split(".")[0])
            std_modules = sorted(set(std_modules))[:80]   # 取前 80 个示意
        else:
            std_modules = ["（标准库路径未找到）"]

        report_lines = [
            f"生成时间：{now}",
            f"Python 版本：{py_ver}",
            f"解释器路径：{py_exec}",
            f"虚拟环境：{venv}",
            "-" * 60,
            ">>> 第三方库（pip list）",
            pkgs,
            "-" * 60,
            ">>> 标准库示例（部分）",
            "  " + ", ".join(std_modules),
            "-" * 60,
        ]

        report_txt = "\n".join(report_lines)
        # 输出到控制台
        self.stdout.write(report_txt)

        # 同时写文件
        with open("env_report.txt", "w", encoding="utf-8") as f:
            f.write(report_txt)

        self.stdout.write(self.style.SUCCESS("\n✅ 报告已保存到 env_report.txt"))