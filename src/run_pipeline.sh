#!/bin/bash

# 运行整个数据计算管线的脚本

echo "开始运行数据计算管线..."
echo "======================================================"

# 设置虚拟环境
VENV_DIR="/home/super/linchen/250418-accountant-agent/venv"

# 检查虚拟环境是否存在，不存在则创建
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv $VENV_DIR
    
    # 激活虚拟环境并安装依赖
    source $VENV_DIR/bin/activate
    pip install requests
    echo "虚拟环境创建完成，已安装依赖包"
else
    echo "使用已存在的虚拟环境"
fi

# 激活虚拟环境
source $VENV_DIR/bin/activate
echo "已激活虚拟环境: $VENV_DIR"

# 确保目录存在
mkdir -p /home/super/linchen/250418-accountant-agent/exp

# 步骤1：A计算机初始化并发送JSON
echo "步骤1：A计算机初始化JSON，从/home/super/linchen/250418-accountant-agent/input.json读取"
python /home/super/linchen/250418-accountant-agent/src/a_computer_step1.py
echo "----------------------------------------------------"
sleep 1

# 步骤2：B计算机处理JSON并发回A
echo "步骤2：B计算机查找公式"
python /home/super/linchen/250418-accountant-agent/src/b_computer_step1.py
echo "----------------------------------------------------"
sleep 1

# 步骤3：A计算机处理B的响应并发回B
echo "步骤3：A计算机解析公式并注入数据"
python /home/super/linchen/250418-accountant-agent/src/a_computer_step2.py
echo "----------------------------------------------------"
sleep 1

# 步骤4：B计算机使用LLM API计算结果并发回A
echo "步骤4：B计算机调用LLM API计算公式结果"
python /home/super/linchen/250418-accountant-agent/src/b_computer_step2.py
echo "----------------------------------------------------"
sleep 5  # 给LLM API调用多一点时间

# 总结处理结果
echo ""
echo "======================================================"
echo "数据计算管线运行完成，结果如下："
echo "----------------------------------------------------"
echo "初始JSON (input.json):"
cat /home/super/linchen/250418-accountant-agent/exp/input.json
echo ""
echo "----------------------------------------------------"
echo "B计算机添加公式后 (b1.json):"
cat /home/super/linchen/250418-accountant-agent/exp/b1.json
echo ""
echo "----------------------------------------------------"
echo "A计算机添加变量数据后 (a2.json):"
cat /home/super/linchen/250418-accountant-agent/exp/a2.json
echo ""
echo "----------------------------------------------------"
echo "B计算机计算结果后 (b2.json):"
cat /home/super/linchen/250418-accountant-agent/exp/b2.json
echo ""
echo "======================================================"
echo "管线执行完毕!"

# 退出虚拟环境
deactivate
