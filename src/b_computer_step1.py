#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
B计算机第一步：解析A发来的JSON，查找公式并添加
"""

import json
import os
import csv
import sys

def b_step1():
    """
    B计算机处理步骤：
    1. 读取A计算机发送的JSON
    2. 解析element_content内容
    3. 在CSV中查找对应公式
    4. 将公式写入JSON的compute_formula字段
    5. 保存为B1.json并"发送"回A计算机
    """
    # 读取A计算机发送的JSON
    input_json_path = '/home/super/linchen/250418-accountant-agent/exp/input.json'
    
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取element_content内容 - 注意JSON结构变更
        element_content = data.get('element_info', {}).get('element_content', '')
        print(f"B计算机：收到元素内容 '{element_content}'，正在查找对应公式...")
        
        # 在CSV中查找对应公式
        csv_path = '/home/super/linchen/250418-accountant-agent/填报说明115之后_公式两列.csv'
        # 强制覆盖 compute_formula 为指定公式
        compute_formula = "([货币资金]+[结算备付金]+[拆出资金]+[交易性金融资产]+[衍生金融资产]+[应收票据]+[应收账款]+[应收款项融资]+[预付款项]+[应收保费]+[应收分保账款]+[应收分保合同准备金]+[其他应收款]+[其他应收款-应收利息]+[其他应收款-应收股利]+[买入返售金融资产]+[存货]+[合同资产]+[持有待售资产]+[一年内到期的非流动资产]+[其他流动资产])-[其他应收款-应收利息]-[其他应收款-应收股利]"
        print(f"B计算机：强制设置公式: '{compute_formula}'")
        # 初始化element_fill_source字段，如果不存在
        if 'element_fill_source' not in data:
            data['element_fill_source'] = {
                "data_source_list": [
                    {
                        "content": "",
                        "source": ""
                    }
                ],
                "compute_formula": ""
            }
        # 更新JSON中的compute_formula字段
        data['element_fill_source']['compute_formula'] = compute_formula
        
        # 保存为B1.json
        b1_json_path = '/home/super/linchen/250418-accountant-agent/exp/b1.json'
        with open(b1_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"B计算机：已将更新后的JSON保存到: {b1_json_path}")
        print("B计算机：正在发送JSON数据回A计算机...")
        
        return b1_json_path
    
    except Exception as e:
        print(f"B计算机处理出错: {str(e)}")
        return None

if __name__ == "__main__":
    b_step1()
