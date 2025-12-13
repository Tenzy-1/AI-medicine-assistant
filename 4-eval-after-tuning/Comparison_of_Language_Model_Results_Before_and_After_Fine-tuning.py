import matplotlib.pyplot as plt
import numpy as np
import re
import os

# -------------------------- Configuration Parameters --------------------------
# Paths to two MD files (use absolute paths based on script location)
script_dir = os.path.dirname(os.path.abspath(__file__))
before_md_path = os.path.join(script_dir, "eval_results", "before-eval-result.md")
after_md_path = os.path.join(script_dir, "eval_results", "after-eval-result.md")

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
def extract_scores_from_md(md_file_path, target_metrics):
    """
    Extract scores of specified metrics from Markdown table
    :param md_file_path: Path to the MD file
    :param target_metrics: List of metrics to extract (order corresponds to final plot)
    :return: Score array arranged in the order of target metrics
    """
    # Store extracted scores (key: metric name, value: score)
    score_dict = {}

    try:
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
        for metric in target_metrics:
            if metric in score_dict:
                scores.append(score_dict[metric])
            else:
                raise ValueError(f"Metric not found in MD file: {metric}")

        return np.array(scores)

    except FileNotFoundError:
        print(f"Error: File not found {md_file_path}")
        exit(1)
    except Exception as e:
        print(f"Error reading {md_file_path}: {str(e)}")
        exit(1)


# -------------------------- Read Data from Two MD Files --------------------------
print("Reading data from MD files...")
before_scores = extract_scores_from_md(before_md_path, target_metrics)
after_scores = extract_scores_from_md(after_md_path, target_metrics)

print("Data extraction successful!")
print(f"Before model scores: {before_scores}")
print(f"After model scores: {after_scores}")

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
plt.savefig('finetune_comparison_from_md.png', dpi=300, bbox_inches='tight')
plt.savefig('finetune_comparison_from_md.pdf', bbox_inches='tight')  # Vector format

# Display plot
plt.show()