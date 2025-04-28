#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用多轮工具调用实现具有连续函数调用能力的财务计算代理
"""

import json
import os
import re
import time
import asyncio
import glob
from typing import List, Dict, Any, Optional

# 引入必要的第三方库
import httpx
from openai import AsyncOpenAI  # 使用OpenAI兼容接口

# 加载API密钥
def load_api_keys():
    """加载API密钥配置"""
    api_keys_path = "/home/super/linchen/000000-api-keys/api_keys.json"
    with open(api_keys_path, 'r', encoding='utf-8') as f:
        return json.load(f)

class DeepSeekLLM:
    """DeepSeek LLM客户端封装类"""
    
    def __init__(self, api_key, base_url, model_name="deepseek-v3-250324"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = 0.1  # 降低温度，使模型更倾向于使用工具
        self.max_tokens = 2048
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
    
    async def call_with_tools(self, messages, tools, tool_choice="auto"):
        """
        调用LLM进行函数调用，支持多轮函数调用
        参数:
            messages: 消息历史
            tools: 可用工具列表
            tool_choice: 工具选择方式
        返回:
            模型响应
        """
        try:
            print(f"发送API请求...")
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=tools,
                tool_choice=tool_choice
            )
            
            # 将OpenAI客户端响应转换为字典格式
            response_dict = {
                "choices": [{
                    "message": {
                        "content": response.choices[0].message.content,
                        "role": response.choices[0].message.role,
                        "tool_calls": []
                    },
                    "finish_reason": response.choices[0].finish_reason,
                    "index": response.choices[0].index
                }],
                "created": response.created,
                "id": response.id,
                "model": response.model,
                "object": response.object,
                "usage": {
                    "completion_tokens": response.usage.completion_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            # 处理工具调用
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                tool_calls = []
                for tool_call in response.choices[0].message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
                response_dict["choices"][0]["message"]["tool_calls"] = tool_calls
            
            return response_dict
        except Exception as e:
            print(f"API调用失败: {str(e)}")
            raise

# 定义计算工具函数
def add(a: float, b: float) -> float:
    """加法运算"""
    return float(a) + float(b)

def subtract(a: float, b: float) -> float:
    """减法运算"""
    return float(a) - float(b)

def multiply(a: float, b: float) -> float:
    """乘法运算"""
    return float(a) * float(b)

def divide(a: float, b: float) -> float:
    """除法运算"""
    if float(b) == 0:
        raise ValueError("除数不能为零")
    return float(a) / float(b)

# 定义要提供给LLM的工具
CALCULATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "执行加法运算。在财务计算中，可用于计算资产总和、收入合计等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个操作数"},
                    "b": {"type": "number", "description": "第二个操作数"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "subtract",
            "description": "执行减法运算。在财务计算中，可用于计算资产净值、收入减支出、同比变动额等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "被减数"},
                    "b": {"type": "number", "description": "减数"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "执行乘法运算。在财务计算中，可用于计算利息、增长率应用、数量乘单价等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个因数"},
                    "b": {"type": "number", "description": "第二个因数"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "divide",
            "description": "执行除法运算。在财务计算中，可用于计算比率、平均值、百分比等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "被除数"},
                    "b": {"type": "number", "description": "除数，不能为零"}
                },
                "required": ["a", "b"]
            }
        }
    }
]

# 定义系统消息，强调多步骤计算和函数调用链
SYSTEM_PROMPT = """你是一个专业的财务计算助手，擅长处理会计和财务领域的计算任务。
你会严格按照以下原则工作：

1. 你必须使用提供的函数进行所有计算，不允许自己计算。
2. 对于多步骤计算，你会分解问题并按顺序调用多个函数。
3. 当涉及诸如"(a+b)/2"这样的复合公式时，你会先调用add(a,b)，然后用结果调用divide(结果,2)。
4. 面对财务变动额计算时，通常使用subtract(当期值, 上期值)公式。
5. 计算平均值时，先使用add计算总和，再使用divide计算平均值。
6. 最重要的是，你必须返回计算的完整结果，不要省略整数部分或负号。

示例思路：
- 对于"(381236.73+257026.09)/2"计算：
  * 步骤1: 调用add(381236.73, 257026.09)得到638262.82
  * 步骤2: 调用divide(638262.82, 2)得到319131.41
  * 最终结果: 319131.41

- 对于"年平均应付账款=([应付账款]+[应付账款_T-1])/2"计算：
  * 步骤1: 调用add(应付账款, 应付账款_T-1)计算总和
  * 步骤2: 调用divide(总和结果, 2)计算平均值
  * 最终答案: 完整的数值，例如7500.0

- 对于"[交易性金融资产]-[交易性金融资产_T-1]"：
  * 调用subtract(交易性金融资产, 交易性金融资产_T-1)
  * 最终答案必须是完整的结果，例如"173436.7"，而不是"436.7"

- 对于减法可能出现的负数结果，必须保留负号，例如:
  * "[货币资金]-[货币资金_T-1]" 如果结果为负，应返回例如"-249678.75"，而不是"678.75"

请确保每步计算都使用函数调用，即使是看似简单的计算也不例外。
最终返回的答案必须是完整的数值，包括整数部分和负号（如果有）。
"""

# 财务计算代理类
class FinancialCalculator:
    """财务计算代理，使用DeepSeek模型进行多步骤计算"""
    
    def __init__(self):
        """初始化计算代理"""
        # 加载API配置
        api_keys = load_api_keys()
        volcano_config = api_keys.get("volcano_engine", {})
        
        self.api_key = volcano_config.get("api_key")
        self.base_url = volcano_config.get("base_url")
        
        if not self.api_key or not self.base_url:
            raise ValueError("无法获取API密钥配置")
        
        # 初始化DeepSeek LLM
        self.llm = DeepSeekLLM(self.api_key, self.base_url)
        
        # 创建工具映射
        self.tools_map = {
            "add": add,
            "subtract": subtract,
            "multiply": multiply,
            "divide": divide
        }
    
    async def execute_tool(self, name, args):
        """执行工具函数"""
        if name not in self.tools_map:
            raise ValueError(f"未知工具: {name}")
        
        try:
            result = self.tools_map[name](**args)
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def run_calc_with_tools(self, question, max_steps=5):
        """
        运行计算代理，支持多步骤工具调用
        参数:
            question: 用户问题
            max_steps: 最大执行步骤数
        返回:
            计算结果
        """
        # 初始化消息历史
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
        
        # 跟踪计算步骤
        calculation_steps = []
        final_result = None
        
        # 开始多轮工具调用循环
        for step in range(max_steps):
            print(f"\n执行步骤 {step+1}/{max_steps}...")
            
            # 调用LLM获取下一步操作
            response = await self.llm.call_with_tools(messages, CALCULATOR_TOOLS)
            
            # 检查是否有工具调用
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls", [])
                content = message.get("content", "")
                
                # 如果没有工具调用但有内容，可能是最终答案
                if not tool_calls and content:
                    print(f"模型返回了内容而非工具调用: {content}")
                    # 提取最终数字结果（如果有）
                    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", content)
                    if numbers:
                        # 尝试转换所有匹配到的数字，取最后一个作为结果
                        try:
                            final_result = float(numbers[-1])
                            # 检查内容中是否包含负号关键词，但结果为正数
                            if final_result > 0 and ("负" in content or "减少" in content or "-" in content or "下降" in content):
                                final_result = -final_result
                        except ValueError:
                            print(f"无法将 {numbers[-1]} 转换为数字")
                    break
                
                # 处理工具调用
                if tool_calls:
                    tool_call = tool_calls[0]  # 获取第一个工具调用
                    function_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    
                    print(f"调用工具: {function_name}({arguments})")
                    
                    # 执行工具调用
                    tool_result = await self.execute_tool(function_name, arguments)
                    
                    # 记录计算步骤
                    step_info = {
                        "step": step + 1,
                        "tool": function_name,
                        "arguments": arguments,
                        "result": tool_result
                    }
                    calculation_steps.append(step_info)
                    
                    # 将工具调用结果添加到消息历史
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(tool_result)
                    })
                    
                    # 如果这是最后一步，保存最终结果
                    if step == max_steps - 1 or "finish_reason" in choice and choice["finish_reason"] != "tool_calls":
                        if tool_result["status"] == "success":
                            final_result = tool_result["result"]
                else:
                    # 没有工具调用，停止循环
                    break
            else:
                print("收到无效的API响应")
                break
        
        # 返回计算结果
        return {
            "question": question,
            "steps": calculation_steps,
            "final_result": final_result
        }

async def process_formula_file(calculator, formula_file):
    """处理单个公式文件"""
    start_time = time.time()
    
    try:
        with open(formula_file, 'r', encoding='utf-8') as f:
            formula_data = json.load(f)
        
        # 构建问题
        formula_name = os.path.splitext(os.path.basename(formula_file))[0]
        variables = {}
        original_formula = ""
        
        for key, data in formula_data.items():
            original_formula = data.get("formula", "")
            for k, v in data.items():
                if k not in ["name", "formula", "T"]:
                    variables[k] = v
        
        # 构建问题文本
        variables_text = ""
        for var_name, var_value in variables.items():
            variables_text += f"{var_name}是{var_value}，"
        
        question = f"{variables_text}为了计算出{formula_name}，应该遵守\"formula\": \"{original_formula}\"，请问{formula_name}是多少？"
        
        print(f"\n开始处理 [{formula_name}]")
        print(f"问题: {question}")
        
        # 获取计算结果
        calculation_result = await calculator.run_calc_with_tools(question)
        
        # 获取预期结果（用于比较）
        expected_result = None
        if "(" in original_formula and ")" in original_formula:
            # 处理复杂公式
            expr = original_formula
            for var_name, var_value in variables.items():
                placeholder = f"[{var_name}]"
                if placeholder in expr:
                    expr = expr.replace(placeholder, str(var_value))
            
            # 清理公式（移除注释等）
            expr = re.sub(r'(/\d+)\(.*?\)', r'\1', expr)
            
            # 安全计算表达式
            expected_result = eval(expr, {"__builtins__": {}})
        else:
            # 处理简单公式
            if "-" in original_formula:
                var_names = re.findall(r'\[(.*?)\]', original_formula)
                if len(var_names) >= 2 and var_names[0] in variables and var_names[1] in variables:
                    expected_result = variables[var_names[0]] - variables[var_names[1]]
        
        # 判断结果是否正确
        is_correct = False
        if expected_result is not None and calculation_result["final_result"] is not None:
            is_correct = abs(expected_result - calculation_result["final_result"]) < 1e-6
        
        elapsed_time = time.time() - start_time
        
        # 返回结果
        return {
            "formula_name": formula_name,
            "question": question,
            "formula": original_formula,
            "variables": variables,
            "calculation_steps": calculation_result["steps"],
            "final_result": calculation_result["final_result"],
            "expected_result": expected_result,
            "is_correct": is_correct,
            "elapsed_time": elapsed_time
        }
    except Exception as e:
        formula_name = os.path.splitext(os.path.basename(formula_file))[0]
        print(f"处理 {formula_name} 时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "formula_name": formula_name,
            "error": str(e),
            "elapsed_time": time.time() - start_time
        }

async def process_all_formulas(formulas_dir):
    """处理目录中的所有公式文件"""
    # 创建计算代理
    calculator = FinancialCalculator()
    
    # 获取所有公式文件
    formula_files = glob.glob(os.path.join(formulas_dir, "*.json"))
    
    if not formula_files:
        raise ValueError(f"在目录 {formulas_dir} 中未找到公式文件")
    
    print(f"找到 {len(formula_files)} 个公式文件，开始处理...")
    
    # 创建处理任务
    tasks = [process_formula_file(calculator, f) for f in formula_files]
    
    # 等待所有任务完成
    results = await asyncio.gather(*tasks)
    
    return results

def format_results(results):
    """格式化结果为可读的输出"""
    output = ["# 财务计算代理测试结果\n"]
    
    # 统计
    total = len(results)
    successful = sum(1 for r in results if "is_correct" in r and r["is_correct"])
    errors = sum(1 for r in results if "error" in r)
    
    output.append(f"总计处理: {total} 个公式")
    output.append(f"正确计算: {successful} 个")
    output.append(f"处理失败: {errors} 个")
    output.append(f"正确率: {(successful/total)*100:.2f}%\n")
    
    # 详细结果
    for i, result in enumerate(results, 1):
        output.append(f"## {i}. {result.get('formula_name', '未命名')}")
        
        if "error" in result:
            output.append(f"**错误**: {result['error']}")
            output.append(f"处理时间: {result.get('elapsed_time', 0):.2f} 秒\n")
            continue
        
        output.append(f"**问题**: {result.get('question', '未提供')}")
        output.append(f"**公式**: {result.get('formula', '未提供')}")
        
        # 变量
        output.append("**变量**:")
        for var_name, var_value in result.get('variables', {}).items():
            output.append(f"- {var_name}: {var_value}")
        
        # 计算步骤
        output.append("\n**计算步骤**:")
        for step in result.get('calculation_steps', []):
            tool = step.get('tool')
            args = step.get('arguments')
            step_result = step.get('result', {}).get('result')
            output.append(f"- 步骤 {step.get('step')}: {tool}({args}) = {step_result}")
        
        # 结果
        output.append(f"\n**计算结果**: {result.get('final_result')}")
        output.append(f"**预期结果**: {result.get('expected_result')}")
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
        output_file = "/home/super/linchen/250418-accountant-agent/adk_results.md"
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
