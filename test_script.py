#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试a_computer_step2.py的空值变量检测功能
"""

import json
import os
import subprocess

def setup_test_files():
    """设置测试文件"""
    # 确保exp目录存在
    os.makedirs('/home/super/linchen/250418-accountant-agent/exp', exist_ok=True)
    
    # 创建测试用的b1.json文件
    b1_data = {
        "element_uuid": "table_0032",
        "element_final_value": "待填写",
        "is_endpoint": False,
        "element_info": {
            "element_content": "市场风险溢价",
            "element_type": "table"
        },
        "element_fill_source": {
            "data_source_list": [
                {
                    "content": "",
                    "source": ""
                }
            ],
            "compute_formula": "无风险利率-市场期望报酬率"
        }
    }
    
    b1_json_path = '/home/super/linchen/250418-accountant-agent/exp/b1.json'
    with open(b1_json_path, 'w', encoding='utf-8') as f:
        json.dump(b1_data, f, ensure_ascii=False, indent=2)
    
    print(f"测试文件 {b1_json_path} 已创建")
    return b1_json_path

def run_test_with_empty_value():
    """测试空值变量场景"""
    # 修改a_computer_step2.py，使其生成空值的变量
    script_path = '/home/super/linchen/250418-accountant-agent/src/a_computer_step2.py'
    
    # 读取原始文件
    with open(script_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # 修改文件，将"无风险利率"的值设为空字符串
    modified_content = original_content.replace(
        '"无风险利率": "0.03",', 
        '"无风险利率": "",', 
    )
    
    # 保存修改后的文件
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print('已修改脚本，将无风险利率变量的值设为空')
    
    # 运行测试
    print("\n开始测试空值变量检测功能...")
    result = subprocess.run(['python', script_path], 
                           capture_output=True, 
                           text=True, 
                           cwd='/home/super/linchen/250418-accountant-agent')
    
    print("测试结果:")
    print(result.stdout)
    
    # 恢复原始文件
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(original_content)
    
    print("已恢复脚本到原始状态")
    
    return "缺少{ 无风险利率 }无法计算结果" in result.stdout

def main():
    """主函数"""
    # 设置测试文件
    setup_test_files()
    
    # 测试空值变量场景
    test_result = run_test_with_empty_value()
    
    if test_result:
        print("\n✅ 测试通过: 脚本成功检测到空值变量并发出警告")
    else:
        print("\n❌ 测试失败: 脚本未能正确检测到空值变量")

if __name__ == "__main__":
    main()
