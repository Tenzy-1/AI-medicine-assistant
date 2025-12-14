"""
模型微调前后对比分析脚本
优化版本：添加了配置管理、错误处理和日志记录
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

# -------------------------- Configuration Parameters --------------------------
# 配置参数（可通过环境变量覆盖）
script_dir = Path(__file__).parent

# 处理路径：环境变量返回字符串，需要正确转换为Path
def get_path_from_env(env_var, default_path):
    """从环境变量获取路径，如果不存在则使用默认路径"""
    env_value = os.getenv(env_var)
    if env_value:
        return Path(env_value)
    return default_path

CONFIG = {
    'before_md_path': get_path_from_env('BEFORE_EVAL_RESULT', 
        script_dir / "eval_results" / "before-eval-result.md"),
    'after_md_path': get_path_from_env('AFTER_EVAL_RESULT',
        script_dir / "eval_results" / "after-eval-result.md"),
    'output_dir': get_path_from_env('OUTPUT_DIR', script_dir),
    'output_format': os.getenv('OUTPUT_FORMAT', 'both'),  # 'png', 'pdf', 'both'
    'dpi': int(os.getenv('DPI', '300')),
}

# Define metric order (corresponds to the Metric column in MD files, ensure correct extraction order)
target_metrics = [
    'mean_bleu-1', 'mean_bleu-2', 'mean_bleu-3', 'mean_bleu-4',
    'mean_Rouge-1-R', 'mean_Rouge-1-P', 'mean_Rouge-1-F',
    'mean_Rouge-2-R', 'mean_Rouge-2-P', 'mean_Rouge-2-F',
    'mean_Rouge-L-R', 'mean_Rouge-L-P', 'mean_Rouge-L-F'
]

# Metric labels for plot display (unified format for better aesthetics)
display_metrics = [
    'BLEU-1', 'BLEU-2', 'BLEU-3', 'BLEU-4',
    'ROUGE-1-R', 'ROUGE-1-P', 'ROUGE-1-F',
    'ROUGE-2-R', 'ROUGE-2-P', 'ROUGE-2-F',
    'ROUGE-L-R', 'ROUGE-L-P', 'ROUGE-L-F'
]

# Legend names
before_label = 'Before (llama-3-8b-bnb-4bit)'
after_label = 'After (qwen25-14b-offical-finetuned-bnb-4bit)'


# -------------------------- Core Function: Extract Scores from MD File --------------------------
def extract_scores_from_md(md_file_path: Path, target_metrics: list) -> np.ndarray:
    """
    Extract scores of specified metrics from Markdown table
    
    Args:
        md_file_path: Path to the MD file
        target_metrics: List of metrics to extract (order corresponds to final plot)
    
    Returns:
        Score array arranged in the order of target metrics
    
    Raises:
        FileNotFoundError: If the MD file doesn't exist
        ValueError: If required metrics are not found
    """
    # Store extracted scores (key: metric name, value: score)
    score_dict = {}

    try:
        if not md_file_path.exists():
            raise FileNotFoundError(f"评估结果文件不存在: {md_file_path}")
        
        logger.info(f"读取评估结果文件: {md_file_path}")
        with open(md_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Iterate through lines of MD file to find table data rows (skip header and separator lines)
        for line in lines:
            # Table rows start and end with |, skip separator lines (containing + or =)
            line_stripped = line.strip()
            if line_stripped.startswith('|') and line_stripped.endswith('|') and '+' not in line_stripped and '=' not in line_stripped:
                # Split table columns (remove leading/trailing | and clean up spaces)
                columns = [col.strip() for col in line_stripped.strip('|').split('|')]

                # Ensure correct number of columns (at least contains Metric and Score columns)
                if len(columns) < 6:  # Adapt to table format: Model, Dataset, Metric, Subset, Num, Score, Cat.0
                    continue

                # Extract metric name and score (according to MD table structure: Metric is 3rd column, Score is 6th column, 0-indexed)
                metric_name = columns[2]
                score_str = columns[5]

                # Verify if score is a valid number (including decimals)
                try:
                    score_value = float(score_str)
                    score_dict[metric_name] = score_value
                except ValueError:
                    continue

        # Organize scores in the order of target metrics (ensure consistency with plot x-axis order)
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


# -------------------------- Read Data from Two MD Files --------------------------
logger.info("=" * 80)
logger.info("开始读取评估结果文件")
logger.info("=" * 80)

try:
    before_scores = extract_scores_from_md(CONFIG['before_md_path'], target_metrics)
    after_scores = extract_scores_from_md(CONFIG['after_md_path'], target_metrics)
    
    logger.info("数据提取成功!")
    logger.info(f"微调前模型得分: {before_scores}")
    logger.info(f"微调后模型得分: {after_scores}")
except Exception as e:
    logger.error(f"读取数据失败: {str(e)}")
    sys.exit(1)

# -------------------------- Plot Configuration --------------------------
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['axes.unicode_minus'] = False  # Fix negative sign display issue

fig, ax = plt.subplots(figsize=(14, 7))  # Increase figure height to accommodate higher values
x_pos = np.arange(len(display_metrics))

# Find maximum score to set appropriate Y-axis limit
max_score = max(np.max(before_scores), np.max(after_scores))
y_max = max(0.60, max_score * 1.15)  # Set Y-axis limit to accommodate highest value + labels

# Plot line charts (add color distinction for clarity)
ax.plot(x_pos, before_scores, marker='o', linewidth=2.2, color='#2E86AB',
        markersize=7, label=before_label)
ax.plot(x_pos, after_scores, marker='s', linewidth=2.2, color='#A23B72',
        markersize=7, label=after_label)

# Add value labels (adjust positions to avoid overlap)
for i, (b_score, a_score) in enumerate(zip(before_scores, after_scores)):
    # Calculate dynamic offset based on score values to avoid overlap
    offset_b = max(0.02, y_max * 0.03)  # Dynamic offset for Before labels
    offset_a = max(0.04, y_max * 0.06)  # Dynamic offset for After labels
    
    # Before score label
    ax.text(i, b_score + offset_b, f'{b_score:.4f}', ha='center', va='bottom',
            fontsize=13, color='#2E86AB', weight='bold')
    # After score label (offset more to avoid overlapping with Before labels)
    ax.text(i, a_score + offset_a, f'{a_score:.4f}', ha='center', va='bottom',
            fontsize=13, color='#A23B72', weight='bold')

# Axis settings
ax.set_ylim(0, y_max)  # Dynamic Y-axis upper limit to accommodate all values and labels
y_tick_interval = 0.1 if y_max > 0.5 else 0.05
ax.set_yticks(np.arange(0, y_max + y_tick_interval, y_tick_interval))
ax.set_xticks(x_pos)
# 轴标签字体
ax.set_xticklabels(display_metrics, rotation=45, ha='right', fontsize=16)
ax.tick_params(axis='y', labelsize=16)  # Y轴刻度标签字体大小
ax.set_ylabel('Score', fontsize=18, fontweight='bold')
ax.set_xlabel('Evaluation Metrics', fontsize=18, fontweight='bold')
# 图例字体
ax.legend(loc='upper left', fontsize=16, frameon=True, shadow=True, framealpha=0.9)
# 标题字体
ax.set_title('Comparison of BLEU & ROUGE Scores (Directly from MD Files)',
             fontsize=20, pad=20, fontweight='bold')

# Adjust layout to prevent label truncation
plt.tight_layout()

# Save images (add bbox_inches to ensure complete labels)
output_format = CONFIG['output_format']
output_dir = CONFIG['output_dir']
output_dir.mkdir(parents=True, exist_ok=True)

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

# Display plot (only if not in headless mode)
try:
    plt.show()
except Exception:
    logger.info("无法显示图表（可能处于无头模式）")