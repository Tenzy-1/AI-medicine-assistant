{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 2,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "123\n"
     ]
    }
   ],
   "source": [
    "print(123)"
   ]
  },
  {
   "attachments": {},
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 原始测试数据集下载地址\n",
    "\n",
    "https://github.com/FreedomIntelligence/CMB/tree/main\n",
    "\n",
    "https://huggingface.co/datasets/FreedomIntelligence/CMB/tree/main/CMB-Clin\n",
    "\n",
    "https://huggingface.co/datasets/FreedomIntelligence/CMB/resolve/main/CMB-Clin/CMB-Clin-qa.json"
   ]
  },
  {
   "attachments": {},
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### EvalScope 自定义测试数据集文档地址\n",
    "\n",
    "https://evalscope.readthedocs.io/zh-cn/latest/advanced_guides/custom_dataset/llm.html#qa"
   ]
  },
  {
   "attachments": {},
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 测试数据集数据处理脚本\n",
    "\n",
    "1. 转换格式\n",
    "2. 去除控制字符"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 19,
   "metadata": {},
   "outputs": [],
   "source": [
    "import json\n",
    "import re\n",
    "import string\n",
    "\n",
    "def remove_control_chars(text):\n",
    "    \"\"\"\n",
    "    使用 translate 去除字符串中的控制字符。\n",
    "    \n",
    "    参数:\n",
    "    text (str): 输入的字符串，可能包含控制字符。\n",
    "    \n",
    "    返回:\n",
    "    str: 去除了控制字符的字符串。\n",
    "    \"\"\"\n",
    "    # 生成控制字符的集合（包括 \\x00 到 \\x1F 和 \\x7F）\n",
    "    control_chars = ''.join(map(chr, range(0, 32))) + chr(127)\n",
    "    \n",
    "    # 创建用于删除这些控制字符的转换表\n",
    "    translation_table = str.maketrans('', '', control_chars)\n",
    "    \n",
    "    # 移除控制字符\n",
    "    return text.translate(translation_table)\n",
    "\n",
    "file_path = '/workspace/CMB-Clin-qa.json'\n",
    "output_file = '/workspace/CMB-Clin-qa.jsonl'\n",
    "\n",
    "# 读取 JSON 文件\n",
    "with open(file_path, 'r', encoding='utf-8') as file:\n",
    "    data = json.load(file)\n",
    "\n",
    "lines = []\n",
    "\n",
    "# 遍历 JSON 数组并打印每个元素\n",
    "for index, item in enumerate(data, start=1):\n",
    "    desc = item['description']\n",
    "    question = item['QA_pairs'][0]['question']\n",
    "    answer = item['QA_pairs'][0]['answer']\n",
    "\n",
    "    line = '{{ \"query\" : \"{} {}\", \"response\" : \"{}\" }}'.format(desc, question, answer)\n",
    "    lines.append(remove_control_chars(line))\n",
    "\n",
    "with open(output_file, 'w', encoding='utf-8') as f:\n",
    "    for line in lines:\n",
    "        #print(line)\n",
    "        line_escaped = line.replace(\"\\n\", \"\")\n",
    "        f.write(line_escaped)\n",
    "        f.write(\"\\n\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python (base)",
   "language": "python",
   "name": "base"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.11"
  },
  "orig_nbformat": 4
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
