#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
B计算机第二步：使用LLM API计算公式结果并写入最终值
"""

import json
import os
import sys
import requests
import time
import ast

def call_llm_api(formula, variables):
    """
    通用计算器 function call 实现：只暴露一个 evaluate_expression 函数，支持任意表达式计算。
    参数:
        formula: 计算表达式（字符串）
        variables: 变量键值对（dict）
    返回:
        计算结果
    """
    import ast
    # 读取API密钥
    try:
        with open('/home/super/linchen/000000-api-keys/api_keys.json', 'r', encoding='utf-8') as f:
            api_keys = json.load(f)
            api_key = api_keys.get('volcano_engine', {}).get('api_key', '')
            base_url = api_keys.get('volcano_engine', {}).get('base_url', 'https://ark.cn-beijing.volces.com/api/v3')
    except Exception as e:
        print(f"读取API密钥出错: {str(e)}")
        api_key = "6bb3037a-57e8-4b46-9dc2-db53252849e8"
        base_url = "https://ark.cn-beijing.volces.com/api/v3"

    # 通用计算器 function call schema
    tools = [
        {
            "type": "function",
            "function": {
                "name": "evaluate_expression",
                "description": "计算任意数学表达式，支持变量。表达式示例：a+b, x*y-z, (本金+利息)*税率 等。变量需通过 variables 提供。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "要计算的数学表达式（如 a+b, x*y-z 等）"},
                        "variables": {"type": "object", "description": "表达式中变量的键值对，如 {\"a\":1,\"b\":2}"}
                    },
                    "required": ["expression", "variables"]
                }
            }
        }
    ]

    system_prompt = (
        "你是一个只调用 evaluate_expression 工具的智能计算器。"
        "遇到任何需要计算的表达式、公式或数值推导时，都应调用 evaluate_expression 工具，并传入表达式与变量。"
        "不要直接输出答案，也不要解释，只调用工具。"
    )
    user_prompt = f"表达式: {formula}\n变量: {json.dumps(variables, ensure_ascii=False)}\n请计算结果。"

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "deepseek-v3-250324",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "tools": tools,
            "tool_choice": {"type": "function", "function": {"name": "evaluate_expression"}},
            "temperature": 0.1
        }
        response = requests.post(
            f"{base_url}/chat/completions", headers=headers, data=json.dumps(payload), timeout=60
        )
        response.raise_for_status()
        result = response.json()
        print("[DEBUG] volcengine API 原始返回：", json.dumps(result, ensure_ascii=False, indent=2))
        # 检查 tool_calls
        tool_calls = None
        try:
            choices = result.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                tool_calls = message.get("tool_calls", None)
        except Exception as e:
            print(f"解析tool_calls出错: {e}")
        if tool_calls and isinstance(tool_calls, list):
            for call in tool_calls:
                if call.get("type") == "function" and call.get("function", {}).get("name") == "evaluate_expression":
                    arguments = call.get("function", {}).get("arguments", "")
                    try:
                        args = json.loads(arguments)
                        expr = args.get("expression", "")
                        vars_dict = args.get("variables", {})
                        # 用变量值安全替换表达式变量
                        expr_eval = expr
                        for k, v in vars_dict.items():
                            expr_eval = expr_eval.replace(str(k), str(v))
                        # 只允许安全表达式
                        result_value = eval(expr_eval, {"__builtins__": {}})
                        return result_value
                    except Exception as e:
                        print(f"本地计算表达式出错: {e}")
                        return None
            print("未检测到evaluate_expression类型的tool_call")
            return None
        else:
            print("未检测到tool_calls，或tool_calls结构不符")
            return None
    except Exception as e:
        print(f"调用LLM API出错: {e}")
        return None

def b_step2():
    """
    B计算机第二步处理：
    1. 读取A2.json
    2. 提取计算公式和变量值
    3. 调用LLM API计算结果
    4. 将结果写入element_final_value
    5. 保存为B2.json并"发送"回A计算机
    """
    # 读取A计算机发送的A2.json
    a2_json_path = '/home/super/linchen/250418-accountant-agent/exp/a2.json'
    
    try:
        with open(a2_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 获取计算公式和变量
        compute_formula = data.get('element_fill_source', {}).get('compute_formula', '')
        variables = data.get('element_fill_source', {}).get('data_source_list', [{}])[0].get('content', {})
        
        print(f"B计算机：收到计算公式 '{compute_formula}' 和变量 {variables}")
        
        if compute_formula and variables:
            # 调用LLM API计算结果
            result = call_llm_api(compute_formula, variables)
            
            # 更新JSON的element_final_value字段
            data['element_final_value'] = result
            print(f"B计算机：已将计算结果 '{result}' 写入JSON")
        else:
            print("B计算机：未找到计算公式或变量，无法计算")
        
        # 保存为B2.json
        b2_json_path = '/home/super/linchen/250418-accountant-agent/exp/b2.json'
        with open(b2_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"B计算机：已将更新后的JSON保存到: {b2_json_path}")
        print("B计算机：正在发送最终JSON数据回A计算机...")
        
        return b2_json_path
    
    except Exception as e:
        print(f"B计算机处理出错: {str(e)}")
        return None

if __name__ == "__main__":
    b_step2()
