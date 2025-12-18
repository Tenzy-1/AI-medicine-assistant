import pandas as pd
import matplotlib.pyplot as plt
import os

# 配置英文显示字体（无需中文字体）
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 修复负号显示问题

# 颜色配置（医疗领域专业配色方案）
COLORS = {
    "success": "#2E8B57",  # 海绿色（成功）
    "fail": "#DC143C",     # 深红色（失败）
    "reason": "#4169E1",   # 皇家蓝（原因维度）
    "suggest": "#FF6347",  # 番茄红（建议维度）
    "note": "#32CD32",     # 石灰绿（注意事项维度）
    "defect1": "#FF8C00",  # 橙红色（缺失注意事项）
    "defect2": "#9370DB",  # 中紫色（原因说明不完整）
    "defect3": "#20B2AA",  # 浅海绿（中英文不一致）
}

# 基于当前脚本位置使用绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(script_dir, "medical_test_results", "medical_test_results_20251203_165417.xlsx")
# 图表输出目录
OUTPUT_DIR = os.path.join(script_dir, "medical_visualization_charts")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# 数据预处理 
def load_and_preprocess_data(excel_path):
    """加载Excel测试结果并进行数据预处理"""
    # 读取Excel文件
    df = pd.read_excel(excel_path, sheet_name="Complete Test Results")

    # 1. 统计测试状态（成功/失败）
    status_counts = df["Status"].value_counts()

    # 2. 分析关键信息完整性（原因、建议、注意事项）
    def count_keywords(text, keywords):
        """检查文本是否包含指定关键词中的任意一个"""
        return 1 if any(keyword in str(text).lower() for keyword in keywords) else 0

    # 定义各维度关键词
    keyword_map = {
        "reason": ["原因", "cause", "因素", "factor"],  # 原因维度（双语支持）
        "suggest": ["建议", "推荐", "措施", "suggest", "recommend", "step", "measure"],  # 建议维度
        "note": ["注意", "风险", "避免", "note", "precaution", "avoid", "risk"]  # 注意事项维度
    }

    # 统计每个回答的维度覆盖情况（合并中英文）
    for dim, keywords in keyword_map.items():
        df[f"has_{dim}"] = df.apply(
            lambda row: count_keywords(str(row["Answer (Chinese)"]) + str(row["Answer (English)"]), keywords),
            axis=1
        )

    # 3. 分析中英文一致性（各维度是否在两种语言中均存在）
    df["consistent_reason"] = df["has_reason"]  # 任意语言包含即视为一致
    df["consistent_suggest"] = df["has_suggest"]
    df["consistent_note"] = df["has_note"]

    # 4. 分类缺陷类型（基于缺失的维度）
    def classify_defect(row):
        """基于回答质量分类缺陷类型"""
        defects = []
        if row["has_note"] == 0:
            defects.append("缺失注意事项")
        if row["has_reason"] == 1 and len([k for k in keyword_map["reason"] if k in str(row["Answer (Chinese)"])]) < 2:
            defects.append("原因说明不完整")
        # 检查原因维度是否存在英文有但中文无的情况（简化一致性校验）
        en_has_reason = any(k in str(row["Answer (English)"]).lower() for k in keyword_map["reason"][1:])
        if row["has_reason"] != (1 if en_has_reason else 0):
            defects.append("中英文不一致")
        return defects if defects else ["无明显缺陷"]

    df["defects"] = df.apply(classify_defect, axis=1)

    # 展开缺陷列表用于统计
    all_defects = []
    defect_question_ids = []
    for idx, row in df.iterrows():
        for defect in row["defects"]:
            if defect != "无明显缺陷":
                all_defects.append(defect)
                defect_question_ids.append(row["Question ID"])

    return {
        "df": df,
        "status_counts": status_counts,
        "defect_counts": pd.Series(all_defects).value_counts(),
        "defect_question_counts": pd.Series(defect_question_ids).value_counts()
    }


# 图表生成函数
def plot_status_distribution(status_counts, output_path):
    """图表1：测试成功率 & 状态分布（饼图 + 柱状图）"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 饼图：状态占比
    labels = status_counts.index.tolist()
    sizes = status_counts.values.tolist()
    colors = [COLORS["success"] if label == "success" else COLORS["fail"] for label in labels]
    wedges, texts, autotexts = ax1.pie(sizes, labels=[f"{label}\n{size} 条数据" for label, size in zip(labels, sizes)],
                                       colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title("模型测试状态分布", fontsize=14, fontweight='bold', pad=20)

    # 柱状图：成功率统计
    success_rate = (status_counts.get("success", 0) / status_counts.sum()) * 100
    fail_rate = 100 - success_rate
    ax2.bar(["成功", "失败"], [success_rate, fail_rate], color=[COLORS["success"], COLORS["fail"]], alpha=0.8)
    ax2.set_ylabel("占比 (%)", fontsize=12)
    ax2.set_title("模型测试成功率", fontsize=14, fontweight='bold', pad=20)
    # 在柱状图顶部添加数值标签
    for i, v in enumerate([success_rate, fail_rate]):
        ax2.text(i, v + 1, f"{v:.1f}%", ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax2.set_ylim(0, 110)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表1已保存：{output_path}")


def plot_answer_completeness(df, output_path):
    """图表2：回答关键信息完整性（堆叠柱状图）"""
    fig, ax = plt.subplots(figsize=(12, 7))

    # 提取每个问题的维度覆盖数据
    question_ids = df["Question ID"].tolist()
    reason_data = df["has_reason"].tolist()
    suggest_data = df["has_suggest"].tolist()
    note_data = df["has_note"].tolist()

    # 堆叠柱状图
    width = 0.6
    ax.bar(question_ids, reason_data, width, label="包含原因分析", color=COLORS["reason"], alpha=0.8)
    ax.bar(question_ids, suggest_data, width, bottom=reason_data, label="包含干预建议",
           color=COLORS["suggest"], alpha=0.8)
    ax.bar(question_ids, note_data, width, bottom=[r + s for r, s in zip(reason_data, suggest_data)],
           label="包含注意事项", color=COLORS["note"], alpha=0.8)

    # 图表配置
    ax.set_xlabel("问题ID", fontsize=12)
    ax.set_ylabel("覆盖维度数量 (0-3)", fontsize=12)
    ax.set_title("各问题回答关键信息完整性", fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(question_ids)
    ax.set_ylim(0, 3.5)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表2已保存：{output_path}")


def plot_cn_en_consistency(df, output_path):
    """图表3：中英文回答一致性（热力图）"""
    fig, ax = plt.subplots(figsize=(10, 8))

    # 构建一致性矩阵（问题ID × 维度）
    question_ids = df["Question ID"].tolist()
    dimensions = ["原因分析", "干预建议", "注意事项"]
    consistency_matrix = [
        [df[df["Question ID"] == qid]["consistent_reason"].iloc[0],
         df[df["Question ID"] == qid]["consistent_suggest"].iloc[0],
         df[df["Question ID"] == qid]["consistent_note"].iloc[0]]
        for qid in question_ids
    ]

    # 绘制热力图
    im = ax.imshow(consistency_matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    # 设置坐标轴标签
    ax.set_xticks(range(len(dimensions)))
    ax.set_xticklabels(dimensions, fontsize=11)
    ax.set_yticks(range(len(question_ids)))
    ax.set_yticklabels([f"问题{qid}" for qid in question_ids], fontsize=10)

    # 在每个单元格添加数值标签（0/1）
    for i in range(len(question_ids)):
        for j in range(len(dimensions)):
            text = ax.text(j, i, consistency_matrix[i][j], ha="center", va="center",
                           color="白色" if consistency_matrix[i][j] == 1 else "黑色", fontweight='bold')

    # 添加颜色条
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("一致性（1=匹配，0=缺失）", fontsize=11)

    ax.set_title("中英文回答维度一致性热力图", fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表3已保存：{output_path}")


def plot_defect_analysis(defect_counts, defect_question_counts, output_path):
    """图表4：缺陷类型统计 & 优先优化问题（饼图 + 柱状图）"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 饼图：缺陷类型占比
    if not defect_counts.empty:
        labels = defect_counts.index.tolist()
        sizes = defect_counts.values.tolist()
        colors = [COLORS["defect1"], COLORS["defect2"], COLORS["defect3"]][:len(labels)]
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title("回答缺陷类型分布", fontsize=14, fontweight='bold', pad=20)
    else:
        ax1.text(0.5, 0.5, "无明显缺陷", ha='center', va='center', transform=ax1.transAxes, fontsize=14)
        ax1.set_title("回答缺陷类型分布", fontsize=14, fontweight='bold', pad=20)

    # 柱状图：缺陷最多的前3个问题
    if not defect_question_counts.empty:
        top3_defect_questions = defect_question_counts.nlargest(3)
        ax2.barh([f"问题{qid}" for qid in top3_defect_questions.index],
                 top3_defect_questions.values, color=COLORS["defect1"], alpha=0.8)
        ax2.set_xlabel("缺陷数量", fontsize=12)
        ax2.set_title("缺陷最多的前3个问题", fontsize=14, fontweight='bold', pad=20)
        # 添加数值标签
        for i, v in enumerate(top3_defect_questions.values):
            ax2.text(v + 0.05, i, str(v), ha='left', va='center', fontweight='bold')
    else:
        ax2.text(0.5, 0.5, "无缺陷问题", ha='center', va='center', transform=ax2.transAxes, fontsize=14)
        ax2.set_title("缺陷最多的前3个问题", fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表4已保存：{output_path}")


# -------------------------- 主执行函数 --------------------------
def generate_all_charts():
    """生成全部4个核心可视化图表"""
    # 1. 数据预处理
    data = load_and_preprocess_data(EXCEL_PATH)

    # 2. 生成所有图表
    plot_status_distribution(
        data["status_counts"],
        os.path.join(OUTPUT_DIR, "1_模型测试状态与成功率.png")
    )

    plot_answer_completeness(
        data["df"],
        os.path.join(OUTPUT_DIR, "2_回答关键信息完整性.png")
    )

    plot_cn_en_consistency(
        data["df"],
        os.path.join(OUTPUT_DIR, "3_中英文回答一致性热力图.png")
    )

    plot_defect_analysis(
        data["defect_counts"],
        data["defect_question_counts"],
        os.path.join(OUTPUT_DIR, "4_缺陷类型与优先优化项.png")
    )

    print(f"\n所有图表生成完成！保存至：{OUTPUT_DIR}")


if __name__ == "__main__":
    generate_all_charts()