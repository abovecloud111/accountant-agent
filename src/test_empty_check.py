#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试A2.json中变量值为空的检测功能
"""

import json
import os
import sys

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

def main():
    """主函数"""
    a2_json_path = '/home/super/linchen/250418-accountant-agent/exp/a2.json'
    
    has_empty_vars, empty_vars = check_variable_values(a2_json_path)
    
    if has_empty_vars:
        empty_vars_str = ", ".join([f"'{var}'" for var in empty_vars])
        print(f"\n缺少{{ {empty_vars_str} }}无法计算结果")
        return False
    else:
        print("\n所有变量都有值，可以继续计算")
        return True

if __name__ == "__main__":
    main()
