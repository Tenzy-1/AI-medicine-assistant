import pandas as pd
import matplotlib.pyplot as plt
import os
import re

# -------------------------- Basic Configuration --------------------------
# Configure font for English display
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issue

# Professional Color Scheme (Medical Scenario Adaptation)
COLORS = {
    "success": "#2E8B57",  # SeaGreen (Processing Success)
    "fail": "#DC143C",  # Crimson (Processing Failure)
    "valid": "#4169E1",  # RoyalBlue (Valid Data)
    "incomplete": "#FF8C00",  # Orange (Incomplete Data)
    "coagulation": "#9370DB",  # MediumPurple (Coagulation Test)
    "blood_type": "#20B2AA",  # LightSeaGreen (Blood Type Test)
    "hbv": "#32CD32",  # LimeGreen (HBV Panel Test)
    "infectious": "#FF6347",  # Tomato (Infectious Disease Screen)
    "missing_data": "#DAA520",  # Goldenrod (Missing Values/Reference Ranges)
    "no_data": "#808080",  # Gray (No Valid Data Extracted)
    "network_error": "#6A5ACD",  # SlateBlue (Network Error)
}

# Test results file path (Ensure this path is correct)
RESULTS_FILE = "Medical_Report_Interpretation_Full_Report.txt"
# Chart output directory
OUTPUT_DIR = "./medical_vlm_visualization"
os.makedirs(OUTPUT_DIR, exist_ok=True)
# Excel report path
EXCEL_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "Medical_Report_Analysis_Statistics.xlsx")


# -------------------------- Data Preprocessing Functions --------------------------
def parse_test_results(result_file):
    """Parse test result file and extract core data (Unified field names)"""
    # 1. Check if file exists
    if not os.path.exists(result_file):
        print(f"Error: File not found - {result_file}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Files in current directory: {os.listdir('.')}")
        return {
            "stats": {"total": 0, "success": 0, "fail": 0, "valid": 0},
            "report_details": [],
            "type_counts": {},
            "defect_counts": pd.Series()
        }

    # 2. Read file content
    with open(result_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 3. Handle empty file
    if not content.strip():
        print("Error: The result file is empty")
        return {
            "stats": {"total": 0, "success": 0, "fail": 0, "valid": 0},
            "report_details": [],
            "type_counts": {},
            "defect_counts": pd.Series()
        }

    # 4. Extract statistical information
    stats_match = re.search(
        r'Statistics:\s*Total Reports\s*(\d+)\s*\|\s*Successfully Processed\s*(\d+)\s*\|\s*Failed\s*(\d+)\s*\|\s*Valid Data\s*(\d+)',
        content, re.IGNORECASE
    )
    stats = {"total": 0, "success": 0, "fail": 0, "valid": 0}
    if stats_match:
        try:
            stats = {
                "total": int(stats_match.group(1)),
                "success": int(stats_match.group(2)),
                "fail": int(stats_match.group(3)),
                "valid": int(stats_match.group(4))
            }
        except (IndexError, ValueError) as e:
            print(f"Warning: Failed to parse statistics - {e}")
    else:
        print("Warning: Statistics information not found, will recalculate from report details")

    # 5. Extract detailed report information
    # Keep Chinese separator in regex since source file contains Chinese sections
    report_pattern = r'\[Report (\d+)\]\s+Image Filename:\s*(.*?)\s*\|\s*Processing Status:\s*(success|failed)\s*([\s\S]*?)=== 医疗报告完整分析（中文）===\n([\s\S]*?)(?=\n={100}|\Z)'
    reports = re.findall(report_pattern, content, re.MULTILINE)

    if not reports:
        print("Warning: No report details matched! Debug info:")
        print(f"First 500 characters of file content:\n{content[:500]}")
        print(f"Regex pattern used:\n{report_pattern}")
        return {
            "stats": stats,
            "report_details": [],
            "type_counts": {},
            "defect_counts": pd.Series()
        }

    # 6. Process each report (KEY FIX: Unified field names with "Extracted" suffix)
    report_details = []
    for report in reports:
        no = int(report[0])
        img_filename = report[1].strip()
        status = report[2].lower()
        chinese_content = report[4].strip()  # Keep Chinese content processing

        # Classify report type using Chinese keywords (critical for accurate classification)
        if any(keyword in img_filename or keyword in chinese_content for keyword in
               ["血凝", "凝血", "PT", "APTT", "INR"]):
            report_type = "Coagulation Test"
        elif any(keyword in img_filename or keyword in chinese_content for keyword in ["血型", "ABO", "RH"]):
            report_type = "Blood Type Test"
        elif any(keyword in img_filename or keyword in chinese_content for keyword in ["乙肝", "HBV", "前S1"]):
            report_type = "HBV Panel Test"
        elif any(keyword in img_filename or keyword in chinese_content for keyword in
                 ["丙肝", "HIV", "梅毒", "Anti-TP", "RPR"]):
            report_type = "Infectious Disease Screen"
        else:
            report_type = "Other"

        # Evaluate data extraction completeness using Chinese content markers
        completeness = {
            "Indicator Names": 1 if (re.search(r'1\.|2\.|3\.|4\.|5\.|6\.', chinese_content) or
                                    any(kw in chinese_content for kw in ["丙肝抗体", "乙肝表面抗原", "ABO血型", "PT", "APTT"])) else 0,
            "Specific Values": 1 if re.search(r'\d+(\.\d+)?\s*[a-zA-Z]+/[a-zA-Z]+|\d+(\.\d+)?\s*（|[\d\.]+', chinese_content) else 0,
            "Reference Ranges": 1 if re.search(r'参考范围|参考区间', chinese_content) else 0,
            "Abnormal Indicators": 1 if re.search(r'异常指标|无异常', chinese_content) else 0,
            "Clinical Conclusions": 1 if re.search(r'临床意义|结论', chinese_content) else 0
        }

        # Identify defects using Chinese error messages
        defects = []
        if status == "failed":
            defects.append("Network Error" if "Read timed out" in chinese_content else "Processing Failed")
        else:
            if "未提取到有效的医疗报告数据" in chinese_content:
                defects.append("No Valid Data Extracted")
            if "缺少具体指标数据" in chinese_content:
                defects.append("Missing Values/Reference Ranges")

        # KEY FIX: Unified field names (all use "XXX Extracted" suffix)
        report_details.append({
            "Report No.": no,
            "Image Filename": img_filename,
            "Processing Status": status,
            "Report Type": report_type,
            "Completeness Score": sum(completeness.values()),
            "Indicator Names Extracted": "Yes" if completeness["Indicator Names"] == 1 else "No",
            "Specific Values Extracted": "Yes" if completeness["Specific Values"] == 1 else "No",
            "Reference Ranges Extracted": "Yes" if completeness["Reference Ranges"] == 1 else "No",
            "Abnormal Indicators Extracted": "Yes" if completeness["Abnormal Indicators"] == 1 else "No",
            "Clinical Conclusions Extracted": "Yes" if completeness["Clinical Conclusions"] == 1 else "No",
            "Defect Types": ", ".join(defects) if defects else "None",
            "Defect Count": len(defects)
        })

    # 7. Recalculate statistics
    total_reports = len(report_details)
    success_reports = len([r for r in report_details if r["Processing Status"] == "success"])
    fail_reports = total_reports - success_reports
    valid_reports = len([r for r in report_details if
                         r["Processing Status"] == "success" and "No Valid Data Extracted" not in r["Defect Types"]])
    stats = {
        "total": total_reports,
        "success": success_reports,
        "fail": fail_reports,
        "valid": valid_reports
    }
    print(f"Statistics confirmed: Total={total_reports}, Success={success_reports}, "
          f"Fail={fail_reports}, Valid={valid_reports}")

    # 8. Count report type and defect distribution
    type_counts = {}
    for r in report_details:
        type_counts[r["Report Type"]] = type_counts.get(r["Report Type"], 0) + 1

    all_defects = []
    for r in report_details:
        if r["Defect Types"] != "None":
            all_defects.extend(r["Defect Types"].split(", "))
    defect_counts = pd.Series(all_defects).value_counts()

    return {
        "stats": stats,
        "report_details": report_details,
        "type_counts": type_counts,
        "defect_counts": defect_counts
    }


# -------------------------- Excel Report Generation Function --------------------------
def generate_excel_report(data):
    """Generate Excel report with unified field names"""
    with pd.ExcelWriter(EXCEL_OUTPUT_PATH, engine='openpyxl') as writer:
        # Sheet 1: Summary Statistics
        summary_df = pd.DataFrame({
            "Metric": ["Total Reports", "Successfully Processed", "Processing Failed", "Valid Data Reports",
                       "Success Rate", "Valid Data Rate"],
            "Value": [
                data["stats"]["total"],
                data["stats"]["success"],
                data["stats"]["fail"],
                data["stats"]["valid"],
                f"{(data['stats']['success']/data['stats']['total']*100):.1f}%" if data['stats']['total']>0 else "0.0%",
                f"{(data['stats']['valid']/data['stats']['success']*100):.1f}%" if data['stats']['success']>0 else "0.0%"
            ]
        })
        summary_df.to_excel(writer, sheet_name="Summary Statistics", index=False)

        # Sheet 2: Detailed Report Info
        if data["report_details"]:
            report_df = pd.DataFrame(data["report_details"])
            column_order = [
                "Report No.", "Image Filename", "Processing Status", "Report Type", "Completeness Score",
                "Indicator Names Extracted", "Specific Values Extracted", "Reference Ranges Extracted",
                "Abnormal Indicators Extracted", "Clinical Conclusions Extracted",
                "Defect Types", "Defect Count"
            ]
            existing_cols = [col for col in column_order if col in report_df.columns]
            report_df[existing_cols].to_excel(writer, sheet_name="Detailed Report Info", index=False)
        else:
            empty_df = pd.DataFrame({
                "Report No.": [], "Image Filename": [], "Processing Status": [], "Report Type": [],
                "Completeness Score": [], "Defect Types": [], "Defect Count": []
            })
            empty_df.to_excel(writer, sheet_name="Detailed Report Info", index=False)

        # Sheet 3: Report Type Distribution
        type_data = pd.DataFrame({
            "Report Type": list(data["type_counts"].keys()),
            "Count": list(data["type_counts"].values()),
            "Percentage": [f"{(v/data['stats']['total']*100):.1f}%" for v in data["type_counts"].values()]
        }) if data["type_counts"] else pd.DataFrame({"Report Type": [], "Count": [], "Percentage": []})
        type_data.to_excel(writer, sheet_name="Report Type Distribution", index=False)

        # Sheet 4: Defect Type Distribution
        if not data["defect_counts"].empty:
            defect_data = pd.DataFrame({
                "Defect Type": data["defect_counts"].index.tolist(),
                "Count": data["defect_counts"].values.tolist(),
                "Percentage": [f"{(v/data['defect_counts'].sum()*100):.1f}%" for v in data["defect_counts"].values]
            })
        else:
            defect_data = pd.DataFrame({"Defect Type": ["None"], "Count": [0], "Percentage": ["100.0%"]})
        defect_data.to_excel(writer, sheet_name="Defect Type Distribution", index=False)

        # Sheet 5: Completeness Score Analysis
        if data["report_details"]:
            comp_df = pd.DataFrame(data["report_details"])
            comp_analysis = comp_df.groupby("Completeness Score").agg({
                "Report No.": "count",
                "Processing Status": lambda x: (x == "success").sum()
            }).rename(columns={"Report No.": "Total Reports", "Processing Status": "Successfully Processed"}).reset_index()
            comp_analysis["Percentage"] = (comp_analysis["Total Reports"]/data["stats"]["total"]*100).round(1).astype(str)+"%"
        else:
            comp_analysis = pd.DataFrame({
                "Completeness Score": [], "Total Reports": [], "Successfully Processed": [], "Percentage": []
            })
        comp_analysis.to_excel(writer, sheet_name="Completeness Score Analysis", index=False)

    print(f"Excel report generated successfully! Saved to: {EXCEL_OUTPUT_PATH}")


# -------------------------- Chart Generation Functions --------------------------
def plot_process_status(stats, output_path):
    """Chart 1: Processing Status (Pie + Bar)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart
    sizes = [stats["success"], stats["fail"]]
    colors = [COLORS["success"], COLORS["fail"]]
    if sum(sizes) == 0:
        ax1.text(0.5, 0.5, "No Data Available", ha='center', va='center', fontsize=18)
    else:
        ax1.pie(sizes, labels=[f"Success\n{sizes[0]}", f"Failure\n{sizes[1]}"],
                colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 16})
    ax1.set_title("Model Processing Status Distribution", fontsize=18, fontweight='bold', pad=20)

    # Bar chart
    categories = ["Total", "Success", "Valid Data"]
    values = [stats["total"], stats["success"], stats["valid"]]
    bars = ax2.bar(categories, values, color=[COLORS["incomplete"], COLORS["success"], COLORS["valid"]], alpha=0.8)
    ax2.set_ylabel("Number of Reports", fontsize=16)
    ax2.set_title("Report Count & Valid Data", fontsize=18, fontweight='bold', pad=20)
    for bar, val in zip(bars, values):
        ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1, str(val), ha='center', va='bottom', fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 1 saved: {output_path}")


def plot_report_type_performance(report_details, type_counts, output_path):
    """Chart 2: Report Type Performance"""
    fig, ax = plt.subplots(figsize=(12, 7))

    if not type_counts:
        ax.text(0.5, 0.5, "No Data Available", ha='center', va='center', fontsize=18)
        ax.set_xlabel("Report Type", fontsize=16)
        ax.set_ylabel("Number of Reports", fontsize=16)
        ax.set_title("Processing Performance by Report Type", fontsize=18, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Chart 2 saved: {output_path}")
        return

    # Calculate success/failure for each type
    type_success = {t: len([r for r in report_details if r["Report Type"]==t and r["Processing Status"]=="success"])
                    for t in type_counts.keys()}
    type_fail = {t: type_counts[t]-type_success[t] for t in type_counts.keys()}

    # Grouped bar chart
    x = range(len(type_counts))
    width = 0.35
    bars1 = ax.bar([i-width/2 for i in x], type_success.values(), width, label="Success", color=COLORS["success"], alpha=0.8)
    bars2 = ax.bar([i+width/2 for i in x], type_fail.values(), width, label="Failure", color=COLORS["fail"], alpha=0.8)

    # Chart config
    ax.set_xlabel("Report Type", fontsize=16)
    ax.set_ylabel("Number of Reports", fontsize=16)
    ax.set_title("Processing Performance by Medical Report Type", fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(type_counts.keys(), rotation=15, fontsize=14)
    ax.legend(fontsize=14)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            if bar.get_height() > 0:
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                        str(int(bar.get_height())), ha='center', va='bottom', fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 2 saved: {output_path}")


def plot_data_extraction_completeness(report_details, output_path):
    """Chart 3: Data Extraction Completeness (Uses unified field names)"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Filter valid reports
    valid_reports = [r for r in report_details if
                     r["Processing Status"]=="success" and "No Valid Data Extracted" not in r["Defect Types"]]

    if not valid_reports:
        ax.text(0.5, 0.5, "No Valid Processed Reports", ha='center', va='center', fontsize=18)
        ax.set_xlabel("Report No.", fontsize=16)
        ax.set_ylabel("Extracted Dimensions (0-5)", fontsize=16)
        ax.set_title("Data Extraction Completeness (Successfully Processed)", fontsize=18, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Chart 3 saved: {output_path}")
        return

    # Prepare data (KEY FIX: Use unified field names with "Extracted" suffix)
    report_nos = [r["Report No."] for r in valid_reports]
    dims = ["Indicator Names", "Specific Values", "Reference Ranges", "Abnormal Indicators", "Clinical Conclusions"]
    dim_data = {
        dim: [1 if r[f"{dim} Extracted"] == "Yes" else 0 for r in valid_reports]
        for dim in dims
    }

    # Stacked bar chart
    bottom = [0]*len(valid_reports)
    dim_colors = [COLORS["coagulation"], COLORS["blood_type"], COLORS["hbv"], COLORS["infectious"], COLORS["valid"]]
    for i, dim in enumerate(dims):
        ax.bar(report_nos, dim_data[dim], bottom=bottom, label=dim, color=dim_colors[i], alpha=0.8)
        bottom = [bottom[j]+dim_data[dim][j] for j in range(len(valid_reports))]

    # Chart config
    ax.set_xlabel("Report No.", fontsize=16)
    ax.set_ylabel("Number of Fully Extracted Dimensions (0-5)", fontsize=16)
    ax.set_title("Medical Report Data Extraction Completeness", fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(report_nos)
    ax.tick_params(axis='x', labelsize=14)
    ax.tick_params(axis='y', labelsize=14)
    ax.set_ylim(0, 5.5)
    ax.legend(loc='upper right', fontsize=14)
    ax.grid(axis='y', alpha=0.3)

    # Add completeness scores
    scores = [sum([dim_data[dim][j] for dim in dims]) for j in range(len(valid_reports))]
    for no, score in zip(report_nos, scores):
        ax.text(no, score+0.1, f"Score: {score}", ha='center', va='bottom', fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 3 saved: {output_path}")


def plot_defect_distribution(defect_counts, report_details, output_path):
    """Chart 4: Defect Distribution"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart for defect types
    if not defect_counts.empty:
        labels = defect_counts.index.tolist()
        sizes = defect_counts.values.tolist()
        defect_color_map = {
            "Missing Values/Reference Ranges": COLORS["missing_data"],
            "No Valid Data Extracted": COLORS["no_data"],
            "Network Error": COLORS["network_error"],
            "Processing Failed": COLORS["fail"]
        }
        colors = [defect_color_map.get(label, COLORS["incomplete"]) for label in labels]
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 16})
    else:
        ax1.text(0.5, 0.5, "No Defects", ha='center', va='center', fontsize=18)
    ax1.set_title("Defect Type Distribution", fontsize=18, fontweight='bold', pad=20)

    # Bar chart for defect count per report
    defect_reports = {f"Report {r['Report No.']}": r["Defect Count"]
                     for r in report_details if r["Defect Count"] > 0}
    if defect_reports:
        sorted_reports = sorted(defect_reports.items(), key=lambda x: x[1], reverse=True)
        labels, counts = zip(*sorted_reports)
        ax2.barh(labels, counts, color=COLORS["missing_data"], alpha=0.8)
        ax2.tick_params(axis='y', labelsize=14)
        for i, v in enumerate(counts):
            ax2.text(v+0.05, i, str(v), ha='left', va='center', fontweight='bold', fontsize=14)
    else:
        ax2.text(0.5, 0.5, "No Defective Reports", ha='center', va='center', fontsize=18)
    ax2.set_xlabel("Number of Defects", fontsize=16)
    ax2.set_title("Defect Count per Report", fontsize=18, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 4 saved: {output_path}")


def plot_cross_modal_alignment(report_details, output_path):
    """Chart 5: Cross-Modal Alignment (Match target structure + Fix tight_layout warning)"""
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except OSError:
        # Fallback for newer matplotlib versions
        plt.style.use('seaborn-v0_8')
    # 2x2 layout matching target structure
    fig, axes = plt.subplots(2, 2, figsize=(9, 7), gridspec_kw={'wspace': 0.2, 'hspace': 0.2})
    axes = axes.flatten()  # Convert to 1D array for easy iteration

    # Status color palette (matches target chart)
    status_colors = {
        "perfect": "#d9e6a7",  # Light green (Score 5)
        "good": "#c9e3f8",  # Light blue (Score 3-4)
        "poor": "#f8d0d8"  # Pink (Score <3)
    }

    # Sample type order (corresponds to 2x2 layout)
    sample_types = [
        "Coagulation Test",
        "Blood Type Test",
        "HBV Panel Test",
        "Infectious Disease Screen"
    ]
    success_reports = [r for r in report_details if r["Processing Status"] == "success"]

    # Handle case with no successful reports
    if not success_reports:
        for ax in axes:
            ax.text(0.5, 0.5, "No Successful Reports", ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.axis('off')
    else:
        # Select sample reports matching target chart (prioritize matching Report No.)
        sample_reports = []
        for target_type in sample_types:
            # Target Report No. matching target chart
            target_report_nos = {
                "Coagulation Test": 3,
                "Blood Type Test": 2,
                "HBV Panel Test": 10,
                "Infectious Disease Screen": 5
            }
            target_no = target_report_nos[target_type]
            # First try to find report with matching No. and Type, else fallback
            target_report = next(
                (r for r in success_reports if r["Report No."] == target_no and r["Report Type"] == target_type),
                next((r for r in success_reports if r["Report Type"] == target_type), success_reports[0])
            )
            sample_reports.append(target_report)

        # Plot each sub-module (matches target chart structure)
        for idx, (ax, report) in enumerate(zip(axes, sample_reports)):
            report_type = sample_types[idx]
            score = report["Completeness Score"]

            # Determine status and evaluation text based on score
            if score == 5:
                status = "perfect"
                eval_text = "□ Image→Text fully aligned\nAll information accurately extracted"
            elif 3 <= score <= 4:
                status = "good"
                eval_text = "□ Core information aligned\nPartial secondary information missing"
            else:
                status = "poor"
                eval_text = "□ Critical information alignment insufficient\nNeeds priority optimization"

            # Info box content (matches target chart exactly)
            info_text = (
                f"Report No.: {report['Report No.']}\n"
                f"Type: {report_type}\n"
                f"Status: SUCCESS\n"
                f"Score: {score}/5\n"
                f"Defects: {report['Defect Types']}\n\n"
                "Alignment Evaluation:\n"
                f"{eval_text}"
            )

            # 1. Sub-module title (above info box)
            ax.text(
                0.5, 0.96,
                f"Cross-Modal Alignment – {report_type}",
                ha='center', va='top', transform=ax.transAxes,
                fontweight='bold', fontsize=12
            )

            # 2. Info box (centered display)
            ax.text(
                0.5, 0.42,
                info_text,
                ha='center', va='center', transform=ax.transAxes,
                fontsize=11, linespacing=1.3,
                bbox=dict(
                    boxstyle="round,pad=0.5",
                    facecolor=status_colors[status],
                    edgecolor="#888888",
                    linewidth=1.0
                )
            )

            # Hide axes
            ax.axis('off')

    # Main title (matches target chart)
    plt.suptitle(
        "Medical Report Cross-Modal (Image→Text) Alignment Quality Comparison",
        fontsize=16, fontweight='bold', y=0.98
    )

    # 关键修复：用subplots_adjust替代tight_layout，解决兼容性警告
    fig.subplots_adjust(
        top=0.90,    # 主标题与子图的间距
        bottom=0.08, # 底部边距
        left=0.08,   # 左侧边距
        right=0.92,  # 右侧边距
        wspace=0.35,  # 子图水平间距
        hspace=0.45   # 子图垂直间距
    )

    # Save chart
    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches='tight',
        facecolor='white'
    )
    plt.close()
    print(f"Chart 5 saved: {output_path}")


# -------------------------- Main Execution Function --------------------------
def generate_all_vlm_charts():
    """Main function to generate all outputs"""
    try:
        # Data preprocessing
        data = parse_test_results(RESULTS_FILE)

        # Generate Excel report
        generate_excel_report(data)

        # Generate charts
        plot_process_status(data["stats"], os.path.join(OUTPUT_DIR, "1_Processing_Status.png"))
        plot_report_type_performance(data["report_details"], data["type_counts"], os.path.join(OUTPUT_DIR, "2_Report_Type_Performance.png"))
        plot_data_extraction_completeness(data["report_details"], os.path.join(OUTPUT_DIR, "3_Extraction_Completeness.png"))
        plot_defect_distribution(data["defect_counts"], data["report_details"], os.path.join(OUTPUT_DIR, "4_Defect_Distribution.png"))
        plot_cross_modal_alignment(data["report_details"], os.path.join(OUTPUT_DIR, "5_Cross_Modal_Alignment.png"))

        print(f"\nAll outputs generated successfully! Saved to: {OUTPUT_DIR}")

    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()


# -------------------------- Execution Entry --------------------------
if __name__ == "__main__":
    generate_all_vlm_charts()