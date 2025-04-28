#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A计算机第二步：解析B发来的JSON，提取公式变量并注入测试数据
增加对变量值为空的检测功能
"""

import json
import os
import re
import sys

def extract_variables(formula):
    """
    从公式中提取变量名
    参数:
        formula: 计算公式字符串
    返回:
        变量名列表
    """
    # 简单的变量提取逻辑，可以根据实际公式格式调整
    # 这里假设变量没有嵌套在中括号内的复杂结构
    variables = re.findall(r'([^-+*/(),\s]+)', formula)
    # 过滤掉可能的数字和操作符
    variables = [var for var in variables if not var.replace('.', '', 1).isdigit() 
                and var not in ['', '-', '+', '*', '/', '(', ')', ',']]
    return variables

def check_empty_variables(variables_dict):
    """
    检查变量字典中是否有空值
    参数:
        variables_dict: 变量字典
    返回:
        (bool, list): 第一个元素表示是否有空值，第二个元素是空值变量列表
    """
    empty_variables = []
    for key, value in variables_dict.items():
        if value == "":
            empty_variables.append(key)
    
    return len(empty_variables) > 0, empty_variables

def a_step2():
    """
    A计算机第二步处理:
    1. 读取B1.json
    2. 解析compute_formula，提取变量
    3. 为变量生成测试数据
    4. 检查是否有变量值为空
    5. 更新JSON
    6. 保存为A2.json并"发送"回B计算机
    """
    # 读取B计算机发送的B1.json
    b1_json_path = '/home/super/linchen/250418-accountant-agent/exp/b1.json'
    
    try:
        with open(b1_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 获取计算公式
        compute_formula = data.get('element_fill_source', {}).get('compute_formula', '')
        print(f"A计算机：收到计算公式 '{compute_formula}'，正在解析变量...")
        
        if compute_formula:
            # 提取公式中的变量
            variables = extract_variables(compute_formula)
            print(f"A计算机：提取的变量: {variables}")
            
            # 生成测试数据（在实际系统中，这些数据可能来自数据库或用户输入）
            test_data = {}
            # 使 test_data 与公式变量一一对应，全部赋值为 1
            if compute_formula == "([货币资金]+[结算备付金]+[拆出资金]+[交易性金融资产]+[衍生金融资产]+[应收票据]+[应收账款]+[应收款项融资]+[预付款项]+[应收保费]+[应收分保账款]+[应收分保合同准备金]+[其他应收款]+[其他应收款-应收利息]+[其他应收款-应收股利]+[买入返售金融资产]+[存货]+[合同资产]+[持有待售资产]+[一年内到期的非流动资产]+[其他流动资产])-[其他应收款-应收利息]-[其他应收款-应收股利]":
                for var in variables:
                    test_data[var] = 1
            else:
                # 为其他公式生成随机测试数据
                for var in variables:
                    test_data[var] = "0.01"  # 示例值，实际应根据业务逻辑设置
            
            # 检查是否有变量值为空
            has_empty_vars, empty_vars = check_empty_variables(test_data)
            if has_empty_vars:
                empty_vars_str = ", ".join([f"{var}" for var in empty_vars])
                print(f"A计算机：检测到空值变量: {empty_vars_str}")
                print(f"缺少{{ {empty_vars_str} }}无法计算结果")
                # 仍然更新JSON以便于检查
                data['element_fill_source']['data_source_list'][0]['content'] = test_data
            else:
                # 更新JSON
                data['element_fill_source']['data_source_list'][0]['content'] = test_data
                print(f"A计算机：已注入测试数据: {test_data}")
        
        # 保存为A2.json
        a2_json_path = '/home/super/linchen/250418-accountant-agent/exp/a2.json'
        with open(a2_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"A计算机：已将更新后的JSON保存到: {a2_json_path}")
        
        # 如果有空值变量，则不发送给B计算机
        if 'has_empty_vars' in locals() and has_empty_vars:
            print("A计算机：由于存在空值变量，不发送JSON数据到B计算机")
            return None
        else:
            print("A计算机：正在发送JSON数据回B计算机...")
            return a2_json_path
    
    except Exception as e:
        print(f"A计算机处理出错: {str(e)}")
        return None

if __name__ == "__main__":
    a_step2()
