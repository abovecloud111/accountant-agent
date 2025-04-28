#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
管理数据计算管线的运行脚本，替代原有的shell脚本
增加了检查A2.json中变量值是否为空的逻辑
"""

import os
import sys
import json
import time
import subprocess
import venv
import platform

# 项目根目录
PROJECT_ROOT = "/home/super/linchen/250418-accountant-agent"

def print_separator(message=None):
    """打印分隔线"""
    if message:
        print(f"\n{message}")
    print("----------------------------------------------------")

def setup_virtual_environment():
    """设置虚拟环境"""
    print("开始运行数据计算管线...")
    print("======================================================")
    
    venv_dir = os.path.join(PROJECT_ROOT, "venv")
    
    # 检查虚拟环境是否存在
    if not os.path.exists(venv_dir):
        print("创建虚拟环境...")
        venv.create(venv_dir, with_pip=True)
        
        # 安装依赖
        # 根据操作系统选择正确的pip路径
        if platform.system() == 'Windows':
            pip_path = os.path.join(venv_dir, 'Scripts', 'pip')
        else:
            pip_path = os.path.join(venv_dir, 'bin', 'pip')
        
        subprocess.run([pip_path, 'install', 'requests'])
        print("虚拟环境创建完成，已安装依赖包")
    else:
        print("使用已存在的虚拟环境")
    
    # 返回Python解释器路径
    if platform.system() == 'Windows':
        python_path = os.path.join(venv_dir, 'Scripts', 'python')
    else:
        python_path = os.path.join(venv_dir, 'bin', 'python')
    
    print(f"已配置虚拟环境: {venv_dir}")
    return python_path

def run_a_step1(python_path):
    """运行A计算机第一步"""
    print_separator(f"步骤1：A计算机初始化JSON，从{PROJECT_ROOT}/input.json读取")
    
    # 确保exp目录存在
    os.makedirs(os.path.join(PROJECT_ROOT, "exp"), exist_ok=True)
    
    # 运行A计算机第一步
    script_path = os.path.join(PROJECT_ROOT, "src", "a_computer_step1.py")
    subprocess.run([python_path, script_path])
    time.sleep(1)
    
    return os.path.join(PROJECT_ROOT, "exp", "input.json")

def run_b_step1(python_path):
    """运行B计算机第一步"""
    print_separator("步骤2：B计算机查找公式")
    
    # 运行B计算机第一步
    script_path = os.path.join(PROJECT_ROOT, "src", "b_computer_step1.py")
    subprocess.run([python_path, script_path])
    time.sleep(1)
    
    return os.path.join(PROJECT_ROOT, "exp", "b1.json")

def check_variable_values(a2_json_path):
    """
    检查A2.json中的变量值是否为空
    返回:
        (bool, list): 第一个元素表示是否有空值，第二个元素是空值变量列表
    """
    try:
        with open(a2_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 获取变量内容
        variables_content = data.get('element_fill_source', {}).get('data_source_list', [{}])[0].get('content', {})
        
        # 检查是否有空值
        empty_variables = []
        for key, value in variables_content.items():
            if value == "":
                empty_variables.append(key)
        
        return len(empty_variables) > 0, empty_variables
    
    except Exception as e:
        print(f"检查变量值出错: {str(e)}")
        return False, []

def run_a_step2(python_path):
    """运行A计算机第二步并检查变量值"""
    print_separator("步骤3：A计算机解析公式并注入数据")
    
    # 运行A计算机第二步
    script_path = os.path.join(PROJECT_ROOT, "src", "a_computer_step2.py")
    subprocess.run([python_path, script_path])
    time.sleep(1)
    
    # 检查A2.json中的变量值
    a2_json_path = os.path.join(PROJECT_ROOT, "exp", "a2.json")
    has_empty_vars, empty_vars = check_variable_values(a2_json_path)
    
    if has_empty_vars:
        empty_vars_str = ", ".join([f"'{var}'" for var in empty_vars])
        print(f"\n缺少{{ {empty_vars_str} }}无法计算结果")
        return None
    
    return a2_json_path

def run_b_step2(python_path):
    """运行B计算机第二步"""
    print_separator("步骤4：B计算机调用LLM API计算公式结果")
    
    # 运行B计算机第二步
    script_path = os.path.join(PROJECT_ROOT, "src", "b_computer_step2.py")
    subprocess.run([python_path, script_path])
    time.sleep(5)  # 给LLM API调用多一点时间
    
    return os.path.join(PROJECT_ROOT, "exp", "b2.json")

def print_results():
    """打印处理结果"""
    print("\n======================================================")
    print("数据计算管线运行完成，结果如下：")
    
    # 打印input.json
    print_separator("初始JSON (input.json):")
    input_json_path = os.path.join(PROJECT_ROOT, "exp", "input.json")
    if os.path.exists(input_json_path):
        with open(input_json_path, 'r', encoding='utf-8') as f:
            print(f.read())
    
    # 打印b1.json
    print_separator("B计算机添加公式后 (b1.json):")
    b1_json_path = os.path.join(PROJECT_ROOT, "exp", "b1.json")
    if os.path.exists(b1_json_path):
        with open(b1_json_path, 'r', encoding='utf-8') as f:
            print(f.read())
    
    # 打印a2.json
    print_separator("A计算机添加变量数据后 (a2.json):")
    a2_json_path = os.path.join(PROJECT_ROOT, "exp", "a2.json")
    if os.path.exists(a2_json_path):
        with open(a2_json_path, 'r', encoding='utf-8') as f:
            print(f.read())
    
    # 打印b2.json
    print_separator("B计算机计算结果后 (b2.json):")
    b2_json_path = os.path.join(PROJECT_ROOT, "exp", "b2.json")
    if os.path.exists(b2_json_path):
        with open(b2_json_path, 'r', encoding='utf-8') as f:
            print(f.read())
    
    print("======================================================")
    print("管线执行完毕!")

def main():
    """主函数"""
    # 设置虚拟环境
    python_path = setup_virtual_environment()
    
    # 运行A计算机第一步
    input_json_path = run_a_step1(python_path)
    
    # 运行B计算机第一步
    b1_json_path = run_b_step1(python_path)
    
    # 运行A计算机第二步并检查变量值
    a2_json_path = run_a_step2(python_path)
    
    # 如果A2.json中有空值，则终止程序
    if a2_json_path is None:
        print_separator()
        print("程序已终止运行")
        return
    
    # 运行B计算机第二步
    b2_json_path = run_b_step2(python_path)
    
    # 打印处理结果
    print_results()

if __name__ == "__main__":
    main()
