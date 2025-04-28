#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A计算机第一步：初始化JSON并发送给B计算机
"""

import json
import os
import shutil
import sys

def a_step1():
    """
    A计算机初始化步骤：
    1. 读取根目录下的input.json
    2. 将JSON复制到exp目录
    """
    # 确保exp目录存在
    os.makedirs('/home/super/linchen/250418-accountant-agent/exp', exist_ok=True)
    
    # 从原始input.json读取内容
    original_json_path = '/home/super/linchen/250418-accountant-agent/input.json'
    
    try:
        with open(original_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("A计算机：从原始JSON读取内容完成")
        
        # 将数据写入exp目录下的input.json
        exp_input_json_path = '/home/super/linchen/250418-accountant-agent/exp/input.json'
        with open(exp_input_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"A计算机：已将原始JSON复制到: {exp_input_json_path}")
        print("A计算机：发送JSON数据到B计算机...")
        
        return exp_input_json_path
    
    except Exception as e:
        print(f"A计算机处理出错: {str(e)}")
        return None

if __name__ == "__main__":
    a_step1()
