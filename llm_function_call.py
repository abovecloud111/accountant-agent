#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用火山引擎API实际调用LLM处理公式计算
支持异步并发处理多个测试数据
"""

import json
import os
import glob
import re
import asyncio
import time
from typing import List, Dict, Any, Tuple, Optional
import httpx

# 加载API密钥
def load_api_keys():
    """加载API密钥配置"""
    api_keys_path = "/home/super/linchen/000000-api-keys/api_keys.json"
    with open(api_keys_path, 'r', encoding='utf-8') as f:
        return json.load(f)

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

# 执行函数调用的处理器
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
    return question, original_formula, all_variables

# LLM调用相关函数
class DeepSeekLLM:
    """DeepSeek LLM客户端封装类"""
    
    def __init__(self, api_key, base_url, model_name="deepseek-v3-250324"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = 0.1  # 降低温度，使模型更倾向于使用工具
        self.max_tokens = 2048
        self.client = httpx.AsyncClient(timeout=60.0)  # 使用异步HTTP客户端
    
    async def call_function(self, question: str, calculator_functions: List[Dict]) -> Dict:
        """
        调用LLM进行函数调用
        参数:
            question: 用户问题
            calculator_functions: 计算器函数描述
        返回:
            模型响应，包含函数调用信息
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建工具列表（按照火山引擎文档格式）
        tools = []
        for func in calculator_functions:
            tools.append({
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": func["parameters"]
                }
            })
        
        # 设置系统提示，明确引导模型使用函数
        system_message = """你是一个数学计算助手，请使用提供的函数进行计算。不要自己计算结果，必须通过函数调用获取结果。以下是你可以使用的函数：
- add(a, b): 计算a + b
- subtract(a, b): 计算a - b
- multiply(a, b): 计算a * b
- divide(a, b): 计算a / b，b不能为0

用户将提供计算问题，请分析公式并选择合适的函数进行计算。"""
        
        # 构建请求体
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": question}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": tools,
            "tool_choice": "auto"  # 强制模型使用工具
        }
        
        try:
            print(f"发送函数调用请求: {question}")
            print(f"API调用: {url}")
            print(f"请求头: {headers}")
            print(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            print(f"API响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            return response_data
        except Exception as e:
            print(f"API调用失败: {str(e)}")
            if isinstance(e, httpx.HTTPStatusError):
                print(f"HTTP状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            raise
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

# 定义我们要提供给LLM的函数
CALCULATOR_FUNCTIONS = [
    {
        "name": "add",
        "description": "加法运算",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个操作数"},
                "b": {"type": "number", "description": "第二个操作数"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "subtract",
        "description": "减法运算",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "被减数"},
                "b": {"type": "number", "description": "减数"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "multiply",
        "description": "乘法运算",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个因数"},
                "b": {"type": "number", "description": "第二个因数"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "divide",
        "description": "除法运算",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "被除数"},
                "b": {"type": "number", "description": "除数，不能为零"}
            },
            "required": ["a", "b"]
        }
    }
]

async def process_formula_with_llm(llm: DeepSeekLLM, formula_file: str) -> Dict:
    """
    使用LLM处理单个公式文件
    参数:
        llm: DeepSeekLLM实例
        formula_file: 公式文件路径
    返回:
        处理结果
    """
    start_time = time.time()
    
    try:
        with open(formula_file, 'r', encoding='utf-8') as f:
            formula_data = json.load(f)
        
        # 生成自然语言问题和提取公式信息
        question, original_formula, all_variables = generate_natural_language_question(formula_file, formula_data)
        formula_name = os.path.splitext(os.path.basename(formula_file))[0]
        
        print(f"\n开始处理 [{formula_name}]")
        print(f"问题: {question}")
        
        # 解析公式并获取预期的function call信息（用于比较）
        expected_function_name, expected_args, expression, calculation_steps = parse_formula(original_formula, all_variables)
        
        # 调用LLM进行函数调用
        try:
            llm_response = await llm.call_function(question, CALCULATOR_FUNCTIONS)
            
            # 提取函数调用信息
            if "choices" in llm_response and len(llm_response["choices"]) > 0:
                choice = llm_response["choices"][0]
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls", [])
                
                if tool_calls and len(tool_calls) > 0:
                    # 使用了工具调用
                    tool_call = tool_calls[0]  # 获取第一个工具调用
                    function_name = tool_call["function"]["name"]
                    
                    # 解析参数(为JSON字符串)
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {"error": "无法解析参数JSON"}
                    
                    # 计算结果
                    if function_name in ["add", "subtract", "multiply", "divide"]:
                        # 处理常规函数调用
                        result = function_call_handler(function_name, [float(args["a"]), float(args["b"])])
                        
                        # 计算预期结果（以供比较）
                        if expected_function_name == "complex":
                            expected_result = evaluate_expression(expression)
                        else:
                            expected_result = function_call_handler(expected_function_name, expected_args)
                        
                        # 比较结果
                        is_correct = abs(result - expected_result) < 1e-6
                        
                        elapsed_time = time.time() - start_time
                        
                        return {
                            "formula_name": formula_name,
                            "question": question,
                            "formula": original_formula,
                            "variables": all_variables,
                            "llm_function": {
                                "name": function_name,
                                "args": args
                            },
                            "expected_function": {
                                "name": expected_function_name,
                                "args": expected_args if expected_function_name != "complex" else {},
                                "expression": expression
                            },
                            "result": result,
                            "expected_result": expected_result,
                            "is_correct": is_correct,
                            "elapsed_time": elapsed_time,
                            "status": "success"
                        }
                    else:
                        return {
                            "formula_name": formula_name,
                            "error": f"未知的函数调用: {function_name}",
                            "elapsed_time": time.time() - start_time,
                            "status": "error_unknown_function"
                        }
                else:
                    # 尝试从普通内容中提取数字结果
                    content = message.get("content", "")
                    print(f"模型未使用工具调用，直接返回: {content}")
                    
                    # 尝试从内容中提取数字（作为备选方案）
                    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", content)
                    extracted_result = None
                    if numbers:
                        extracted_result = float(numbers[-1])  # 使用最后一个数字作为结果
                    
                    # 计算预期结果（以供比较）
                    if expected_function_name == "complex":
                        expected_result = evaluate_expression(expression)
                    else:
                        expected_result = function_call_handler(expected_function_name, expected_args)
                    
                    # 判断提取的结果是否与预期接近
                    is_correct = False
                    if extracted_result is not None:
                        is_correct = abs(extracted_result - expected_result) < 1e-6
                    
                    return {
                        "formula_name": formula_name,
                        "question": question,
                        "formula": original_formula,
                        "variables": all_variables,
                        "error": "模型未使用工具调用",
                        "content": content,
                        "extracted_result": extracted_result,
                        "expected_result": expected_result,
                        "is_correct": is_correct,
                        "elapsed_time": time.time() - start_time,
                        "status": "no_tool_call"
                    }
            else:
                return {
                    "formula_name": formula_name,
                    "error": "无效的API响应格式",
                    "raw_response": llm_response,
                    "elapsed_time": time.time() - start_time,
                    "status": "error_invalid_response"
                }
                
        except Exception as e:
            return {
                "formula_name": formula_name,
                "error": f"调用LLM出错: {str(e)}",
                "elapsed_time": time.time() - start_time,
                "status": "error_llm_call"
            }
            
    except Exception as e:
        formula_name = os.path.splitext(os.path.basename(formula_file))[0]
        return {
            "formula_name": formula_name,
            "error": f"处理公式文件出错: {str(e)}",
            "elapsed_time": time.time() - start_time,
            "status": "error_file_processing"
        }

async def process_all_formulas(formulas_dir: str) -> List[Dict]:
    """
    异步并发处理所有公式文件
    参数:
        formulas_dir: 公式文件目录
    返回:
        所有处理结果的列表
    """
    # 加载API配置
    api_keys = load_api_keys()
    volcano_config = api_keys.get("volcano_engine", {})
    
    api_key = volcano_config.get("api_key")
    base_url = volcano_config.get("base_url")
    
    if not api_key or not base_url:
        raise ValueError("无法从API密钥文件获取火山引擎配置")
    
    # 创建LLM客户端
    llm = DeepSeekLLM(api_key, base_url)
    
    try:
        # 获取所有公式文件
        formula_files = glob.glob(os.path.join(formulas_dir, "*.json"))
        
        if not formula_files:
            raise ValueError(f"在目录 {formulas_dir} 中未找到公式文件")
        
        print(f"找到 {len(formula_files)} 个公式文件，开始并发处理...")
        
        # 创建所有公式处理任务
        tasks = [process_formula_with_llm(llm, formula_file) for formula_file in formula_files]
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks)
        
        return results
    finally:
        # 确保客户端关闭
        await llm.close()

def format_results(results: List[Dict]) -> str:
    """
    格式化处理结果为可读的输出
    参数:
        results: 处理结果列表
    返回:
        格式化后的字符串
    """
    output = ["# 公式计算结果汇总\n"]
    
    # 统计
    total = len(results)
    successful = sum(1 for r in results if "is_correct" in r and r["is_correct"])
    errors = sum(1 for r in results if "status" in r and r["status"].startswith("error"))
    no_tool_calls = sum(1 for r in results if "status" in r and r["status"] == "no_tool_call")
    
    output.append(f"总计处理: {total} 个公式")
    output.append(f"正确计算: {successful} 个")
    output.append(f"未使用工具调用: {no_tool_calls} 个")
    output.append(f"处理失败: {errors} 个")
    output.append(f"正确率: {(successful/total)*100:.2f}%\n")
    
    # 详细结果
    for i, result in enumerate(results, 1):
        output.append(f"## {i}. {result.get('formula_name', '未命名')}")
        status = result.get("status", "unknown")
        
        if status.startswith("error"):
            output.append(f"**错误**: {result.get('error', '未知错误')}")
            output.append(f"**状态**: {status}")
            output.append(f"处理时间: {result.get('elapsed_time', 0):.2f} 秒\n")
            continue
        
        output.append(f"**问题**: {result.get('question', '未提供')}")
        output.append(f"**公式**: {result.get('formula', '未提供')}")
        
        # 变量
        output.append("**变量**:")
        for var_name, var_value in result.get('variables', {}).items():
            output.append(f"- {var_name}: {var_value}")
        
        if status == "success":
            # LLM函数调用
            llm_func = result.get('llm_function', {})
            output.append(f"**LLM选择的函数**: {llm_func.get('name', '未提供')}")
            output.append(f"**LLM函数参数**: {llm_func.get('args', {})}")
            
            # 预期函数调用
            expected_func = result.get('expected_function', {})
            output.append(f"**预期函数**: {expected_func.get('name', '未提供')}")
            
            if expected_func.get('name') == "complex":
                output.append(f"**预期表达式**: {expected_func.get('expression', '未提供')}")
            else:
                output.append(f"**预期参数**: {expected_func.get('args', {})}")
            
            # 结果比较
            output.append(f"**LLM计算结果**: {result.get('result', '未提供')}")
            output.append(f"**预期结果**: {result.get('expected_result', '未提供')}")
            output.append(f"**计算正确**: {'是' if result.get('is_correct', False) else '否'}")
        elif status == "no_tool_call":
            output.append(f"**状态**: 模型未使用工具调用")
            output.append(f"**模型回复**: {result.get('content', '无内容')}")
            
            if "extracted_result" in result and result["extracted_result"] is not None:
                output.append(f"**从文本提取的结果**: {result['extracted_result']}")
            
            output.append(f"**预期结果**: {result.get('expected_result', '未提供')}")
            output.append(f"**计算正确**: {'是' if result.get('is_correct', False) else '否'}")
        
        output.append(f"**处理时间**: {result.get('elapsed_time', 0):.2f} 秒\n")
    
    return "\n".join(output)

async def main():
    """主函数"""
    try:
        start_time = time.time()
        print("开始处理所有公式文件...")
        
        # 处理公式目录
        formulas_dir = "/home/super/linchen/250418-accountant-agent/separated_formulas"
        results = await process_all_formulas(formulas_dir)
        
        # 格式化输出
        output = format_results(results)
        
        # 保存结果到文件
        output_file = "/home/super/linchen/250418-accountant-agent/llm_results.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        
        # 输出总结
        total_time = time.time() - start_time
        print(f"\n处理完成! 总耗时: {total_time:.2f} 秒")
        print(f"详细结果已保存到: {output_file}")
        
        # 计算成功率
        total = len(results)
        successful = sum(1 for r in results if "is_correct" in r and r["is_correct"])
        print(f"总计: {total}, 正确: {successful}, 正确率: {(successful/total)*100:.2f}%")
        
    except Exception as e:
        print(f"执行出错: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
