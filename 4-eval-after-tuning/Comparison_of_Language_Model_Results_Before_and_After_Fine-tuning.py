"""
模型微调前后对比分析脚本
优化版本：新增配置管理、错误处理和日志记录功能
"""
import matplotlib.pyplot as plt
import numpy as np
import re
import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('comparison_analysis.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# -------------------------- 配置参数 --------------------------
# 配置参数（可通过环境变量覆盖）
script_dir = Path(__file__).parent

# 处理路径：环境变量返回字符串，需正确转换为Path对象
def get_path_from_env(env_var, default_path):
    """从环境变量获取路径，若不存在则使用默认路径"""
    env_value = os.getenv(env_var)
    if env_value:
        return Path(env_value)
    return default_path

CONFIG = {
    'before_md_path': get_path_from_env('BEFORE_EVAL_RESULT', 
        script_dir / "eval_results" / "before-eval-result.md"),  # 微调前评估结果路径
    'after_md_path': get_path_from_env('AFTER_EVAL_RESULT',
        script_dir / "eval_results" / "after-eval-result.md"),   # 微调后评估结果路径
    'output_dir': get_path_from_env('OUTPUT_DIR', script_dir),   # 图表输出目录
    'output_format': os.getenv('OUTPUT_FORMAT', 'both'),         # 输出格式：'png'/'pdf'/'both'
    'dpi': int(os.getenv('DPI', '300')),                         # 图片分辨率
}

# 定义指标顺序（与MD文件中的Metric列对应，确保提取顺序正确）
target_metrics = [
    'mean_bleu-1', 'mean_bleu-2', 'mean_bleu-3', 'mean_bleu-4',
    'mean_Rouge-1-R', 'mean_Rouge-1-P', 'mean_Rouge-1-F',
    'mean_Rouge-2-R', 'mean_Rouge-2-P', 'mean_Rouge-2-F',
    'mean_Rouge-L-R', 'mean_Rouge-L-P', 'mean_Rouge-L-F'
]

# 图表展示用的指标标签（统一格式提升美观度）
display_metrics = [
    'BLEU-1', 'BLEU-2', 'BLEU-3', 'BLEU-4',
    'ROUGE-1-R', 'ROUGE-1-P', 'ROUGE-1-F',
    'ROUGE-2-R', 'ROUGE-2-P', 'ROUGE-2-F',
    'ROUGE-L-R', 'ROUGE-L-P', 'ROUGE-L-F'
]

# 图例名称
before_label = '微调前 (llama-3-8b-bnb-4bit)'
after_label = '微调后 (qwen25-14b-offical-finetuned-bnb-4bit)'


# -------------------------- 核心函数：从MD文件提取分数 --------------------------
def extract_scores_from_md(md_file_path: Path, target_metrics: list) -> np.ndarray:
    """
    从Markdown表格中提取指定指标的分数
    
    参数:
        md_file_path: MD文件路径
        target_metrics: 待提取的指标列表（顺序与最终图表对应）
    
    返回:
        按target_metrics顺序排列的分数数组
    
    异常:
        FileNotFoundError: MD文件不存在时抛出
        ValueError: 必要指标未找到时抛出
    """
    # 存储提取的分数（键：指标名称，值：分数）
    score_dict = {}

    try:
        if not md_file_path.exists():
            raise FileNotFoundError(f"评估结果文件不存在: {md_file_path}")
        
        logger.info(f"读取评估结果文件: {md_file_path}")
        with open(md_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 遍历MD文件行，查找表格数据行（跳过表头和分隔线）
        for line in lines:
            # 表格行以|开头和结尾，跳过分隔线（包含+或=）
            line_stripped = line.strip()
            if line_stripped.startswith('|') and line_stripped.endswith('|') and '+' not in line_stripped and '=' not in line_stripped:
                # 拆分表格列（去除首尾|并清理空格）
                columns = [col.strip() for col in line_stripped.strip('|').split('|')]

                # 确保列数正确（至少包含Metric和Score列）
                if len(columns) < 6:  # 适配表格格式：Model, Dataset, Metric, Subset, Num, Score, Cat.0
                    continue

                # 提取指标名称和分数（按MD表格结构：Metric是第3列，Score是第6列，0索引）
                metric_name = columns[2]
                score_str = columns[5]

                # 验证分数是否为有效数字（包含小数）
                try:
                    score_value = float(score_str)
                    score_dict[metric_name] = score_value
                except ValueError:
                    continue

        # 按目标指标顺序整理分数（确保与图表X轴顺序一致）
        scores = []
        missing_metrics = []
        for metric in target_metrics:
            if metric in score_dict:
                scores.append(score_dict[metric])
            else:
                missing_metrics.append(metric)
                logger.warning(f"指标未在MD文件中找到: {metric}，将使用0作为默认值")
                scores.append(0.0)  # 使用0作为默认值，避免程序崩溃
        
        if missing_metrics:
            logger.warning(f"以下指标未找到，已使用默认值0: {', '.join(missing_metrics)}")

        logger.info(f"成功提取 {len(scores)} 个指标")
        return np.array(scores)

    except FileNotFoundError as e:
        logger.error(f"文件未找到: {md_file_path}")
        raise
    except Exception as e:
        logger.error(f"读取文件时出错 {md_file_path}: {str(e)}", exc_info=True)
        raise


# -------------------------- 读取两个MD文件的数据 --------------------------
logger.info("=" * 80)
logger.info("开始读取评估结果文件")
logger.info("=" * 80)

try:
    before_scores = extract_scores_from_md(CONFIG['before_md_path'], target_metrics)  # 微调前分数
    after_scores = extract_scores_from_md(CONFIG['after_md_path'], target_metrics)    # 微调后分数
    
    logger.info("数据提取成功!")
    logger.info(f"微调前模型得分: {before_scores}")
    logger.info(f"微调后模型得分: {after_scores}")
except Exception as e:
    logger.error(f"读取数据失败: {str(e)}")
    sys.exit(1)

# -------------------------- 图表配置 --------------------------
# 全局绘图参数配置
plt.rcParams['font.family'] = 'Times New Roman'        # 全局字体
plt.rcParams['mathtext.fontset'] = 'stix'              # 数学公式字体
plt.rcParams['xtick.direction'] = 'in'                # X轴刻度向内
plt.rcParams['ytick.direction'] = 'in'                # Y轴刻度向内
plt.rcParams['axes.unicode_minus'] = False             # 修复负号显示问题

fig, ax = plt.subplots(figsize=(14, 7))  # 增大图表高度以容纳更高数值
x_pos = np.arange(len(display_metrics))

# 找到最大分数，设置合适的Y轴上限
max_score = max(np.max(before_scores), np.max(after_scores))
y_max = max(0.60, max_score * 1.15)  # Y轴上限设为最大值+标签空间

# 绘制折线图（添加颜色区分提升清晰度）
ax.plot(x_pos, before_scores, marker='o', linewidth=2.2, color='#2E86AB',
        markersize=7, label=before_label)  # 微调前折线
ax.plot(x_pos, after_scores, marker='s', linewidth=2.2, color='#A23B72',
        markersize=7, label=after_label)   # 微调后折线

# 添加数值标签（调整位置避免重叠）
for i, (b_score, a_score) in enumerate(zip(before_scores, after_scores)):
    # 根据分数值计算动态偏移量，避免标签重叠
    offset_b = max(0.02, y_max * 0.03)  # 微调前标签动态偏移
    offset_a = max(0.04, y_max * 0.06)  # 微调后标签动态偏移
    
    # 微调前分数标签
    ax.text(i, b_score + offset_b, f'{b_score:.4f}', ha='center', va='bottom',
            fontsize=13, color='#2E86AB', weight='bold')
    # 微调后分数标签（更大偏移避免与微调前重叠）
    ax.text(i, a_score + offset_a, f'{a_score:.4f}', ha='center', va='bottom',
            fontsize=13, color='#A23B72', weight='bold')

# 坐标轴设置
ax.set_ylim(0, y_max)  # 动态Y轴上限，容纳所有数值和标签
y_tick_interval = 0.1 if y_max > 0.5 else 0.05  # 动态Y轴刻度间隔
ax.set_yticks(np.arange(0, y_max + y_tick_interval, y_tick_interval))
ax.set_xticks(x_pos)

# 轴标签字体设置
ax.set_xticklabels(display_metrics, rotation=45, ha='right', fontsize=16)  # X轴标签
ax.tick_params(axis='y', labelsize=16)  # Y轴刻度标签字体大小
ax.set_ylabel('分数', fontsize=18, fontweight='bold')  # Y轴标题
ax.set_xlabel('评估指标', fontsize=18, fontweight='bold')  # X轴标题

# 图例设置
ax.legend(loc='upper left', fontsize=16, frameon=True, shadow=True, framealpha=0.9)

# 标题设置
ax.set_title('BLEU & ROUGE 分数对比（直接读取MD文件）',
             fontsize=20, pad=20, fontweight='bold')

# 调整布局防止标签截断
plt.tight_layout()

# 保存图片（添加bbox_inches确保标签完整显示）
output_format = CONFIG['output_format']
output_dir = CONFIG['output_dir']
output_dir.mkdir(parents=True, exist_ok=True)  # 确保输出目录存在

if output_format in ['png', 'both']:
    png_path = output_dir / 'finetune_comparison_from_md.png'
    plt.savefig(str(png_path), dpi=CONFIG['dpi'], bbox_inches='tight')
    logger.info(f"PNG图表已保存: {png_path}")

if output_format in ['pdf', 'both']:
    pdf_path = output_dir / 'finetune_comparison_from_md.pdf'
    plt.savefig(str(pdf_path), bbox_inches='tight')
    logger.info(f"PDF图表已保存: {pdf_path}")

logger.info("=" * 80)
logger.info("对比分析完成")
logger.info("=" * 80)

# 显示图表（仅非无头模式下生效）
try:
    plt.show()
except Exception:
    logger.info("无法显示图表（可能处于无头模式）")