#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试function call处理公式计算
"""

import json
import os
import glob
import re

# 定义四个基础运算函数
def add(a, b):
    """加法运算"""
    return float(a) + float(b)

def subtract(a, b):
    """减法运算"""
    return float(a) - float(b)

def multiply(a, b):
    """乘法运算"""
    return float(a) * float(b)

def divide(a, b):
    """除法运算"""
    if float(b) == 0:
        raise ValueError("除数不能为零")
    return float(a) / float(b)

# 模拟LLM function call的函数
def function_call_handler(function_name, args):
    """
    处理function call
    参数:
        function_name: 函数名称
        args: 函数参数
    返回:
        计算结果
    """
    functions = {
        "add": add,
        "subtract": subtract,
        "multiply": multiply,
        "divide": divide
    }
    
    if function_name not in functions:
        raise ValueError(f"未知的函数: {function_name}")
    
    return functions[function_name](*args)

def clean_formula(formula):
    """
    清理公式，去除非计算部分
    参数:
        formula: 原始公式
    返回:
        清理后的公式
    """
    # 移除括号后的注释文本，如 "(...)/2(若无T-1数据，T-1年取T年值)"
    formula = re.sub(r'(/\d+)\(.*?\)', r'\1', formula)
    
    # 如果还有其他注释形式，可以继续添加清理规则
    return formula

def evaluate_expression(expr):
    """
    安全地计算数学表达式
    参数:
        expr: 数学表达式字符串
    返回:
        计算结果
    """
    # 使用正则表达式确保表达式只包含数字、运算符和括号
    if not re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', expr):
        raise ValueError(f"不安全的表达式: {expr}")
    
    # 安全地计算表达式
    try:
        return eval(expr, {"__builtins__": {}})
    except Exception as e:
        raise ValueError(f"表达式计算错误: {expr}, 错误: {str(e)}")

def parse_formula(formula, variables):
    """
    解析公式
    参数:
        formula: 公式字符串 (如 "[交易性金融资产]-[交易性金融资产_T-1]")
        variables: 变量字典
    返回:
        function_name: 要调用的函数名
        args: 函数参数列表,
        expression: 完整表达式
        calculation_steps: 计算步骤描述
    """
    # 清理公式
    cleaned_formula = clean_formula(formula)
    
    # 替换所有变量
    expression = cleaned_formula
    for var_name, var_value in variables.items():
        placeholder = f"[{var_name}]"
        if placeholder in expression:
            expression = expression.replace(placeholder, str(var_value))
    
    # 保存计算步骤
    calculation_steps = f"原始公式: {formula}\n清理后的公式: {cleaned_formula}\n替换变量后: {expression}"
    
    # 从表达式中识别操作类型
    pure_expr = expression
    
    # 检查是否包含括号
    if "(" in pure_expr and ")" in pure_expr:
        # 处理带括号的复杂表达式
        return "complex", [], pure_expr, calculation_steps
    
    # 基于公式中的运算符确定要调用的函数
    if "+" in pure_expr:
        parts = pure_expr.split("+")
        return "add", [parts[0].strip(), parts[1].strip()], pure_expr, calculation_steps
    elif "-" in pure_expr:
        parts = pure_expr.split("-")
        return "subtract", [parts[0].strip(), parts[1].strip()], pure_expr, calculation_steps
    elif "*" in pure_expr:
        parts = pure_expr.split("*")
        return "multiply", [parts[0].strip(), parts[1].strip()], pure_expr, calculation_steps
    elif "/" in pure_expr:
        parts = pure_expr.split("/")
        return "divide", [parts[0].strip(), parts[1].strip()], pure_expr, calculation_steps
    else:
        raise ValueError(f"不支持的公式格式: {formula}")

def generate_natural_language_question(formula_file, formula_data):
    """
    生成自然语言问题
    参数:
        formula_file: 公式文件名
        formula_data: 公式数据
    返回:
        自然语言问题
    """
    # 从文件名获取公式名称
    formula_name = os.path.splitext(os.path.basename(formula_file))[0]
    
    # 合并所有示例的变量
    all_variables = {}
    original_formula = ""
    
    for key, data in formula_data.items():
        original_formula = data.get("formula", "")
        for k, v in data.items():
            if k not in ["name", "formula", "T"]:
                all_variables[k] = v
    
    # 生成自然语言问题
    variables_text = ""
    for var_name, var_value in all_variables.items():
        variables_text += f"{var_name}是{var_value}，"
    
    question = f"{variables_text}为了计算出{formula_name}，应该遵守\"formula\": \"{original_formula}\"，请问{formula_name}是多少？"
    return question

def process_formula_file(formula_file):
    """
    处理单个公式文件
    参数:
        formula_file: 公式文件路径
    返回:
        处理结果
    """
    try:
        with open(formula_file, 'r', encoding='utf-8') as f:
            formula_data = json.load(f)
        
        # 生成自然语言问题
        question = generate_natural_language_question(formula_file, formula_data)
        print(f"\n问题: {question}")
        
        # 合并所有示例的变量
        all_variables = {}
        original_formula = ""
        
        for key, data in formula_data.items():
            original_formula = data.get("formula", "")
            for k, v in data.items():
                if k not in ["name", "formula", "T"]:
                    all_variables[k] = v
        
        # 解析公式并获取function call信息
        function_name, args, expression, calculation_steps = parse_formula(original_formula, all_variables)
        
        print(f"计算步骤解析:\n{calculation_steps}")
        
        # 执行计算
        if function_name == "complex":
            # 对于复杂表达式，使用evaluate_expression
            result = evaluate_expression(expression)
            print(f"计算过程: 计算复杂表达式 {expression}")
        else:
            # 对于简单表达式，使用function_call_handler
            result = function_call_handler(function_name, args)
            print(f"计算过程: 执行 {function_name}({', '.join(map(str, args))})")
        
        print(f"计算结果: {result}")
        
        return {
            "question": question,
            "formula": original_formula,
            "variables": all_variables,
            "expression": expression,
            "calculation_steps": calculation_steps,
            "function_call": {
                "name": function_name,
                "args": args if function_name != "complex" else ["complex_expression"]
            },
            "result": result
        }
    
    except Exception as e:
        print(f"处理文件 {formula_file} 时出错: {str(e)}")
        return None

def main():
    """
    主函数
    """
    formulas_dir = "/home/super/linchen/250418-accountant-agent/separated_formulas"
    formula_files = glob.glob(os.path.join(formulas_dir, "*.json"))
    
    print(f"找到 {len(formula_files)} 个公式文件")
    
    results = []
    
    for formula_file in formula_files:
        print(f"\n处理文件: {formula_file}")
        result = process_formula_file(formula_file)
        if result:
            results.append(result)
    
    # 保存结果到JSON文件
    output_file = "/home/super/linchen/250418-accountant-agent/function_call_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n所有公式处理完成，结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
