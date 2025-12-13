import pandas as pd
import matplotlib.pyplot as plt
import os

# -------------------------- Basic Configuration --------------------------
# Configure font for English display (no Chinese font required)
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issue
# Increase default font sizes
plt.rcParams['font.size'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['axes.labelsize'] = 16
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['figure.titlesize'] = 20

# Color Configuration (Professional color scheme for medical domain)
COLORS = {
    "success": "#2E8B57",  # SeaGreen (Success)
    "fail": "#DC143C",  # Crimson (Failure)
    "reason": "#4169E1",  # RoyalBlue (Cause dimension)
    "suggest": "#FF6347",  # Tomato (Suggestion dimension)
    "note": "#32CD32",  # LimeGreen (Precautions dimension)
    "defect1": "#FF8C00",  # Orange (Missing precautions)
    "defect2": "#9370DB",  # MediumPurple (Incomplete cause explanation)
    "defect3": "#20B2AA",  # LightSeaGreen (CN-EN inconsistency)
}

# Result file path (Please replace with your Excel file path)
# Use absolute path based on current script location
script_dir = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(script_dir, "medical_test_results_20251130_173723(1).xlsx")
# Chart output directory
OUTPUT_DIR = os.path.join(script_dir, "medical_visualization_charts")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# -------------------------- Data Preprocessing --------------------------
def load_and_preprocess_data(excel_path):
    """Load Excel test results and preprocess data"""
    # Read Excel file
    df = pd.read_excel(excel_path, sheet_name="Complete Test Results")

    # 1. Count test status (success/fail)
    status_counts = df["Status"].value_counts()

    # 2. Analyze key information completeness (cause, suggestion, precautions)
    def count_keywords(text, keywords):
        """Check if text contains any of the specified keywords"""
        return 1 if any(keyword in str(text).lower() for keyword in keywords) else 0

    # Define keywords for each dimension
    keyword_map = {
        "reason": ["原因", "cause", "因素", "factor"],  # Cause dimension (bilingual support)
        "suggest": ["建议", "推荐", "措施", "suggest", "recommend", "step", "measure"],  # Suggestion dimension
        "note": ["注意", "风险", "避免", "note", "precaution", "avoid", "risk"]  # Precautions dimension
    }

    # Count dimension coverage for each answer (combine Chinese and English)
    for dim, keywords in keyword_map.items():
        df[f"has_{dim}"] = df.apply(
            lambda row: count_keywords(str(row["Answer (Chinese)"]) + str(row["Answer (English)"]), keywords),
            axis=1
        )

    # 3. Analyze CN-EN consistency (whether dimensions exist in both languages)
    df["consistent_reason"] = df["has_reason"]  # Considered consistent if present in either language
    df["consistent_suggest"] = df["has_suggest"]
    df["consistent_note"] = df["has_note"]

    # 4. Classify defect types (based on missing dimensions)
    def classify_defect(row):
        """Classify defect types based on answer quality"""
        defects = []
        if row["has_note"] == 0:
            defects.append("Missing Precautions")
        if row["has_reason"] == 1 and len([k for k in keyword_map["reason"] if k in str(row["Answer (Chinese)"])]) < 2:
            defects.append("Incomplete Cause Explanation")
        # Check if cause dimension exists in English but not in Chinese (simplified consistency check)
        en_has_reason = any(k in str(row["Answer (English)"]).lower() for k in keyword_map["reason"][1:])
        if row["has_reason"] != (1 if en_has_reason else 0):
            defects.append("CN-EN Inconsistency")
        return defects if defects else ["No Significant Defects"]

    df["defects"] = df.apply(classify_defect, axis=1)

    # Expand defects list for statistics
    all_defects = []
    defect_question_ids = []
    for idx, row in df.iterrows():
        for defect in row["defects"]:
            if defect != "No Significant Defects":
                all_defects.append(defect)
                defect_question_ids.append(row["Question ID"])

    return {
        "df": df,
        "status_counts": status_counts,
        "defect_counts": pd.Series(all_defects).value_counts(),
        "defect_question_counts": pd.Series(defect_question_ids).value_counts()
    }


# -------------------------- Chart Generation Functions --------------------------
def plot_status_distribution(status_counts, output_path):
    """Chart 1: Test Success Rate & Status Distribution (Pie + Bar Chart)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart: Status proportion
    labels = status_counts.index.tolist()
    sizes = status_counts.values.tolist()
    colors = [COLORS["success"] if label == "success" else COLORS["fail"] for label in labels]
    wedges, texts, autotexts = ax1.pie(sizes, labels=[f"{label}\n{size} items" for label, size in zip(labels, sizes)],
                                       colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
    ax1.set_title("Model Test Status Distribution", fontsize=18, fontweight='bold', pad=20)

    # Bar chart: Success rate statistics
    success_rate = (status_counts.get("success", 0) / status_counts.sum()) * 100
    fail_rate = 100 - success_rate
    ax2.bar(["Success", "Failure"], [success_rate, fail_rate], color=[COLORS["success"], COLORS["fail"]], alpha=0.8)
    ax2.set_ylabel("Percentage (%)", fontsize=16)
    ax2.set_title("Model Test Success Rate", fontsize=18, fontweight='bold', pad=20)
    # Add value labels on top of bars
    for i, v in enumerate([success_rate, fail_rate]):
        ax2.text(i, v + 1, f"{v:.1f}%", ha='center', va='bottom', fontsize=15, fontweight='bold')
    ax2.set_ylim(0, 110)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 1 saved: {output_path}")


def plot_answer_completeness(df, output_path):
    """Chart 2: Key Information Completeness of Answers (Stacked Bar Chart)"""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Extract dimension coverage data for each question
    question_ids = df["Question ID"].tolist()
    reason_data = df["has_reason"].tolist()
    suggest_data = df["has_suggest"].tolist()
    note_data = df["has_note"].tolist()

    # Stacked bar chart
    width = 0.6
    ax.bar(question_ids, reason_data, width, label="Contains Cause Analysis", color=COLORS["reason"], alpha=0.8)
    ax.bar(question_ids, suggest_data, width, bottom=reason_data, label="Contains Intervention Suggestions",
           color=COLORS["suggest"], alpha=0.8)
    ax.bar(question_ids, note_data, width, bottom=[r + s for r, s in zip(reason_data, suggest_data)],
           label="Contains Precautions", color=COLORS["note"], alpha=0.8)

    # Chart configuration
    ax.set_xlabel("Question ID", fontsize=16)
    ax.set_ylabel("Number of Covered Dimensions (0-3)", fontsize=16)
    ax.set_title("Key Information Completeness by Question", fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(question_ids)
    ax.set_ylim(0, 3.5)
    ax.tick_params(axis='x', labelsize=14)
    ax.tick_params(axis='y', labelsize=14)
    ax.legend(loc='upper right', fontsize=14)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 2 saved: {output_path}")


def plot_cn_en_consistency(df, output_path):
    """Chart 3: CN-EN Answer Consistency (Heatmap)"""
    fig, ax = plt.subplots(figsize=(10, 8))

    # Build consistency matrix (Question ID × Dimension)
    question_ids = df["Question ID"].tolist()
    dimensions = ["Cause Analysis", "Intervention Suggestions", "Precautions"]
    consistency_matrix = [
        [df[df["Question ID"] == qid]["consistent_reason"].iloc[0],
         df[df["Question ID"] == qid]["consistent_suggest"].iloc[0],
         df[df["Question ID"] == qid]["consistent_note"].iloc[0]]
        for qid in question_ids
    ]

    # Plot heatmap
    im = ax.imshow(consistency_matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    # Set axis labels
    ax.set_xticks(range(len(dimensions)))
    ax.set_xticklabels(dimensions, fontsize=14)
    ax.set_yticks(range(len(question_ids)))
    ax.set_yticklabels([f"Q{qid}" for qid in question_ids], fontsize=14)

    # Add value labels (0/1) in each cell
    for i in range(len(question_ids)):
        for j in range(len(dimensions)):
            text = ax.text(j, i, consistency_matrix[i][j], ha="center", va="center",
                           color="white" if consistency_matrix[i][j] == 1 else "black", fontweight='bold', fontsize=14)

    # Add color bar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Consistency (1=Matched, 0=Missing)", fontsize=14)
    cbar.ax.tick_params(labelsize=14)

    ax.set_title("CN-EN Answer Dimension Consistency Heatmap", fontsize=18, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 3 saved: {output_path}")


def plot_defect_analysis(defect_counts, defect_question_counts, output_path):
    """Chart 4: Defect Type Statistics & Priority Optimization Questions (Pie + Bar Chart)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart: Defect type proportion
    if not defect_counts.empty:
        labels = defect_counts.index.tolist()
        sizes = defect_counts.values.tolist()
        colors = [COLORS["defect1"], COLORS["defect2"], COLORS["defect3"]][:len(labels)]
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
        ax1.set_title("Answer Defect Type Distribution", fontsize=18, fontweight='bold', pad=20)
    else:
        ax1.text(0.5, 0.5, "No Significant Defects", ha='center', va='center', transform=ax1.transAxes, fontsize=16)
        ax1.set_title("Answer Defect Type Distribution", fontsize=18, fontweight='bold', pad=20)

    # Bar chart: Top 3 defect-prone questions
    if not defect_question_counts.empty:
        top3_defect_questions = defect_question_counts.nlargest(3)
        ax2.barh([f"Q{qid}" for qid in top3_defect_questions.index],
                 top3_defect_questions.values, color=COLORS["defect1"], alpha=0.8)
        ax2.set_xlabel("Number of Defects", fontsize=16)
        ax2.set_title("Top 3 Defect-Prone Questions", fontsize=18, fontweight='bold', pad=20)
        ax2.tick_params(axis='x', labelsize=14)
        ax2.tick_params(axis='y', labelsize=14)
        # Add value labels
        for i, v in enumerate(top3_defect_questions.values):
            ax2.text(v + 0.05, i, str(v), ha='left', va='center', fontweight='bold', fontsize=15)
    else:
        ax2.text(0.5, 0.5, "No Defective Questions", ha='center', va='center', transform=ax2.transAxes, fontsize=16)
        ax2.set_title("Top 3 Defect-Prone Questions", fontsize=18, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 4 saved: {output_path}")


# -------------------------- Main Execution Function --------------------------
def generate_all_charts():
    """Generate all 4 core visualization charts"""
    # 1. Data preprocessing
    data = load_and_preprocess_data(EXCEL_PATH)

    # 2. Generate all charts
    plot_status_distribution(
        data["status_counts"],
        os.path.join(OUTPUT_DIR, "1_Model_Test_Status_and_Success_Rate.png")
    )

    plot_answer_completeness(
        data["df"],
        os.path.join(OUTPUT_DIR, "2_Answer_Key_Information_Completeness.png")
    )

    plot_cn_en_consistency(
        data["df"],
        os.path.join(OUTPUT_DIR, "3_CN-EN_Answer_Consistency_Heatmap.png")
    )

    plot_defect_analysis(
        data["defect_counts"],
        data["defect_question_counts"],
        os.path.join(OUTPUT_DIR, "4_Defect_Type_and_Priority_Optimization.png")
    )

    print(f"\nAll charts generated successfully! Saved to: {OUTPUT_DIR}")


# -------------------------- Execution Entry --------------------------
if __name__ == "__main__":
    generate_all_charts()