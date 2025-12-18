import pandas as pd
import matplotlib.pyplot as plt
import os
import re

# 配置英文显示字体
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 修复负号显示问题

# 专业配色方案（医疗场景适配）
COLORS = {
    "success": "#2E8B57",  # 海绿色（处理成功）
    "fail": "#DC143C",     # 深红色（处理失败）
    "valid": "#4169E1",    # 皇家蓝（有效数据）
    "incomplete": "#FF8C00",  # 橙红色（数据不完整）
    "coagulation": "#9370DB", # 中紫色（凝血功能检测）
    "blood_type": "#20B2AA",  # 浅海绿（血型检测）
    "hbv": "#32CD32",         # 石灰绿（乙肝五项检测）
    "infectious": "#FF6347",  # 番茄红（传染病筛查）
    "missing_data": "#DAA520", # 金菊色（缺失数值/参考范围）
    "no_data": "#808080",     # 灰色（未提取到有效数据）
    "network_error": "#6A5ACD", # 石楠蓝（网络错误）
}

# 测试结果文件路径（请确保该路径正确）
RESULTS_FILE = "Medical_Report_Interpretation_Full_Report.txt"
# 图表输出目录
OUTPUT_DIR = "./medical_vlm_visualization"
os.makedirs(OUTPUT_DIR, exist_ok=True)
# Excel报告路径
EXCEL_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "Medical_Report_Analysis_Statistics.xlsx")

def parse_test_results(result_file):
    """解析测试结果文件并提取核心数据（统一字段命名）"""
    # 1. 检查文件是否存在
    if not os.path.exists(result_file):
        print(f"错误：文件未找到 - {result_file}")
        print(f"当前工作目录：{os.getcwd()}")
        print(f"当前目录下的文件：{os.listdir('.')}")
        return {
            "stats": {"total": 0, "success": 0, "fail": 0, "valid": 0},
            "report_details": [],
            "type_counts": {},
            "defect_counts": pd.Series()
        }

    # 2. 读取文件内容
    with open(result_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 3. 处理空文件情况
    if not content.strip():
        print("错误：结果文件为空")
        return {
            "stats": {"total": 0, "success": 0, "fail": 0, "valid": 0},
            "report_details": [],
            "type_counts": {},
            "defect_counts": pd.Series()
        }

    # 4. 提取统计信息
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
            print(f"警告：解析统计信息失败 - {e}")
    else:
        print("警告：未找到统计信息，将从报告详情重新计算")

    # 5. 提取报告详细信息
    # 正则中保留中文分隔符，因源文件包含中文分段
    report_pattern = r'\[Report (\d+)\]\s+Image Filename:\s*(.*?)\s*\|\s*Processing Status:\s*(success|failed)\s*([\s\S]*?)=== 医疗报告完整分析（中文）===\n([\s\S]*?)(?=\n={100}|\Z)'
    reports = re.findall(report_pattern, content, re.MULTILINE)

    if not reports:
        print("警告：未匹配到任何报告详情！调试信息：")
        print(f"文件内容前500字符：\n{content[:500]}")
        print(f"使用的正则表达式：\n{report_pattern}")
        return {
            "stats": stats,
            "report_details": [],
            "type_counts": {},
            "defect_counts": pd.Series()
        }

    report_details = []
    for report in reports:
        no = int(report[0])
        img_filename = report[1].strip()
        status = report[2].lower()
        chinese_content = report[4].strip()  # 保留中文内容处理逻辑

        # 使用中文关键词分类报告类型（分类准确性关键）
        if any(keyword in img_filename or keyword in chinese_content for keyword in
               ["血凝", "凝血", "PT", "APTT", "INR"]):
            report_type = "凝血功能检测"
        elif any(keyword in img_filename or keyword in chinese_content for keyword in ["血型", "ABO", "RH"]):
            report_type = "血型检测"
        elif any(keyword in img_filename or keyword in chinese_content for keyword in ["乙肝", "HBV", "前S1"]):
            report_type = "乙肝五项检测"
        elif any(keyword in img_filename or keyword in chinese_content for keyword in
                 ["丙肝", "HIV", "梅毒", "Anti-TP", "RPR"]):
            report_type = "传染病筛查"
        else:
            report_type = "其他类型"

        # 使用中文内容标记评估数据提取完整性
        completeness = {
            "指标名称": 1 if (re.search(r'1\.|2\.|3\.|4\.|5\.|6\.', chinese_content) or
                            any(kw in chinese_content for kw in ["丙肝抗体", "乙肝表面抗原", "ABO血型", "PT", "APTT"])) else 0,
            "具体数值": 1 if re.search(r'\d+(\.\d+)?\s*[a-zA-Z]+/[a-zA-Z]+|\d+(\.\d+)?\s*（|[\d\.]+', chinese_content) else 0,
            "参考范围": 1 if re.search(r'参考范围|参考区间', chinese_content) else 0,
            "异常指标": 1 if re.search(r'异常指标|无异常', chinese_content) else 0,
            "临床结论": 1 if re.search(r'临床意义|结论', chinese_content) else 0
        }

        # 使用中文错误信息识别缺陷类型
        defects = []
        if status == "failed":
            defects.append("网络错误" if "Read timed out" in chinese_content else "处理失败")
        else:
            if "未提取到有效的医疗报告数据" in chinese_content:
                defects.append("未提取到有效数据")
            if "缺少具体指标数据" in chinese_content:
                defects.append("缺失数值/参考范围")

        # 核心修复：统一字段命名（均使用"XXX Extracted"后缀）
        report_details.append({
            "报告编号": no,
            "图片文件名": img_filename,
            "处理状态": status,
            "报告类型": report_type,
            "完整性得分": sum(completeness.values()),
            "指标名称提取状态": "是" if completeness["指标名称"] == 1 else "否",
            "具体数值提取状态": "是" if completeness["具体数值"] == 1 else "否",
            "参考范围提取状态": "是" if completeness["参考范围"] == 1 else "否",
            "异常指标提取状态": "是" if completeness["异常指标"] == 1 else "否",
            "临床结论提取状态": "是" if completeness["临床结论"] == 1 else "否",
            "缺陷类型": ", ".join(defects) if defects else "无",
            "缺陷数量": len(defects)
        })

    # 7. 重新计算统计信息
    total_reports = len(report_details)
    success_reports = len([r for r in report_details if r["处理状态"] == "success"])
    fail_reports = total_reports - success_reports
    valid_reports = len([r for r in report_details if
                         r["处理状态"] == "success" and "未提取到有效数据" not in r["缺陷类型"]])
    stats = {
        "total": total_reports,
        "success": success_reports,
        "fail": fail_reports,
        "valid": valid_reports
    }
    print(f"统计信息已确认：总计={total_reports}, 成功={success_reports}, "
          f"失败={fail_reports}, 有效={valid_reports}")

    # 8. 统计报告类型和缺陷分布
    type_counts = {}
    for r in report_details:
        type_counts[r["报告类型"]] = type_counts.get(r["报告类型"], 0) + 1

    all_defects = []
    for r in report_details:
        if r["缺陷类型"] != "无":
            all_defects.extend(r["缺陷类型"].split(", "))
    defect_counts = pd.Series(all_defects).value_counts()

    return {
        "stats": stats,
        "report_details": report_details,
        "type_counts": type_counts,
        "defect_counts": defect_counts
    }

def generate_excel_report(data):
    """生成包含统一字段命名的Excel报告"""
    with pd.ExcelWriter(EXCEL_OUTPUT_PATH, engine='openpyxl') as writer:
        # 工作表1：汇总统计
        summary_df = pd.DataFrame({
            "指标": ["报告总数", "处理成功数", "处理失败数", "有效数据报告数",
                       "处理成功率", "有效数据率"],
            "数值": [
                data["stats"]["total"],
                data["stats"]["success"],
                data["stats"]["fail"],
                data["stats"]["valid"],
                f"{(data['stats']['success']/data['stats']['total']*100):.1f}%" if data['stats']['total']>0 else "0.0%",
                f"{(data['stats']['valid']/data['stats']['success']*100):.1f}%" if data['stats']['success']>0 else "0.0%"
            ]
        })
        summary_df.to_excel(writer, sheet_name="汇总统计", index=False)

        # 工作表2：报告详细信息
        if data["report_details"]:
            report_df = pd.DataFrame(data["report_details"])
            column_order = [
                "报告编号", "图片文件名", "处理状态", "报告类型", "完整性得分",
                "指标名称提取状态", "具体数值提取状态", "参考范围提取状态",
                "异常指标提取状态", "临床结论提取状态",
                "缺陷类型", "缺陷数量"
            ]
            existing_cols = [col for col in column_order if col in report_df.columns]
            report_df[existing_cols].to_excel(writer, sheet_name="报告详细信息", index=False)
        else:
            empty_df = pd.DataFrame({
                "报告编号": [], "图片文件名": [], "处理状态": [], "报告类型": [],
                "完整性得分": [], "缺陷类型": [], "缺陷数量": []
            })
            empty_df.to_excel(writer, sheet_name="报告详细信息", index=False)

        # 工作表3：报告类型分布
        type_data = pd.DataFrame({
            "报告类型": list(data["type_counts"].keys()),
            "数量": list(data["type_counts"].values()),
            "占比": [f"{(v/data['stats']['total']*100):.1f}%" for v in data["type_counts"].values()]
        }) if data["type_counts"] else pd.DataFrame({"报告类型": [], "数量": [], "占比": []})
        type_data.to_excel(writer, sheet_name="报告类型分布", index=False)

        # 工作表4：缺陷类型分布
        if not data["defect_counts"].empty:
            defect_data = pd.DataFrame({
                "缺陷类型": data["defect_counts"].index.tolist(),
                "数量": data["defect_counts"].values.tolist(),
                "占比": [f"{(v/data['defect_counts'].sum()*100):.1f}%" for v in data["defect_counts"].values]
            })
        else:
            defect_data = pd.DataFrame({"缺陷类型": ["无"], "数量": [0], "占比": ["100.0%"]})
        defect_data.to_excel(writer, sheet_name="缺陷类型分布", index=False)

        # 工作表5：完整性得分分析
        if data["report_details"]:
            comp_df = pd.DataFrame(data["report_details"])
            comp_analysis = comp_df.groupby("完整性得分").agg({
                "报告编号": "count",
                "处理状态": lambda x: (x == "success").sum()
            }).rename(columns={"报告编号": "报告总数", "处理状态": "处理成功数"}).reset_index()
            comp_analysis["占比"] = (comp_analysis["报告总数"]/data["stats"]["total"]*100).round(1).astype(str)+"%"
        else:
            comp_analysis = pd.DataFrame({
                "完整性得分": [], "报告总数": [], "处理成功数": [], "占比": []
            })
        comp_analysis.to_excel(writer, sheet_name="完整性得分分析", index=False)

    print(f"Excel报告生成成功！保存至：{EXCEL_OUTPUT_PATH}")


def plot_process_status(stats, output_path):
    """图表1：处理状态分布（饼图 + 柱状图）"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 饼图
    sizes = [stats["success"], stats["fail"]]
    colors = [COLORS["success"], COLORS["fail"]]
    if sum(sizes) == 0:
        ax1.text(0.5, 0.5, "无可用数据", ha='center', va='center', fontsize=18)
    else:
        ax1.pie(sizes, labels=[f"成功\n{sizes[0]}", f"失败\n{sizes[1]}"],
                colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 16})
    ax1.set_title("模型处理状态分布", fontsize=18, fontweight='bold', pad=20)

    # 柱状图
    categories = ["总计", "成功", "有效数据"]
    values = [stats["total"], stats["success"], stats["valid"]]
    bars = ax2.bar(categories, values, color=[COLORS["incomplete"], COLORS["success"], COLORS["valid"]], alpha=0.8)
    ax2.set_ylabel("报告数量", fontsize=16)
    ax2.set_title("报告数量与有效数据统计", fontsize=18, fontweight='bold', pad=20)
    for bar, val in zip(bars, values):
        ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1, str(val), ha='center', va='bottom', fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表1已保存：{output_path}")


def plot_report_type_performance(report_details, type_counts, output_path):
    """图表2：报告类型处理表现"""
    fig, ax = plt.subplots(figsize=(12, 7))

    if not type_counts:
        ax.text(0.5, 0.5, "无可用数据", ha='center', va='center', fontsize=18)
        ax.set_xlabel("报告类型", fontsize=16)
        ax.set_ylabel("报告数量", fontsize=16)
        ax.set_title("不同报告类型的处理表现", fontsize=18, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"图表2已保存：{output_path}")
        return

    # 计算各类型的成功/失败数量
    type_success = {t: len([r for r in report_details if r["报告类型"]==t and r["处理状态"]=="success"])
                    for t in type_counts.keys()}
    type_fail = {t: type_counts[t]-type_success[t] for t in type_counts.keys()}

    # 分组柱状图
    x = range(len(type_counts))
    width = 0.35
    bars1 = ax.bar([i-width/2 for i in x], type_success.values(), width, label="成功", color=COLORS["success"], alpha=0.8)
    bars2 = ax.bar([i+width/2 for i in x], type_fail.values(), width, label="失败", color=COLORS["fail"], alpha=0.8)

    # 图表配置
    ax.set_xlabel("报告类型", fontsize=16)
    ax.set_ylabel("报告数量", fontsize=16)
    ax.set_title("不同医疗报告类型的处理表现", fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(type_counts.keys(), rotation=15, fontsize=14)
    ax.legend(fontsize=14)
    ax.grid(axis='y', alpha=0.3)

    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            if bar.get_height() > 0:
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                        str(int(bar.get_height())), ha='center', va='bottom', fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表2已保存：{output_path}")


def plot_data_extraction_completeness(report_details, output_path):
    """图表3：数据提取完整性（使用统一字段命名）"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # 筛选有效报告
    valid_reports = [r for r in report_details if
                     r["处理状态"]=="success" and "未提取到有效数据" not in r["缺陷类型"]]

    if not valid_reports:
        ax.text(0.5, 0.5, "无有效处理完成的报告", ha='center', va='center', fontsize=18)
        ax.set_xlabel("报告编号", fontsize=16)
        ax.set_ylabel("提取维度数量 (0-5)", fontsize=16)
        ax.set_title("数据提取完整性（处理成功的报告）", fontsize=18, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"图表3已保存：{output_path}")
        return

    # 准备数据（核心修复：使用统一的"Extracted"后缀字段名）
    report_nos = [r["报告编号"] for r in valid_reports]
    dims = ["指标名称", "具体数值", "参考范围", "异常指标", "临床结论"]
    dim_data = {
        dim: [1 if r[f"{dim}提取状态"] == "是" else 0 for r in valid_reports]
        for dim in dims
    }

    # 堆叠柱状图
    bottom = [0]*len(valid_reports)
    dim_colors = [COLORS["coagulation"], COLORS["blood_type"], COLORS["hbv"], COLORS["infectious"], COLORS["valid"]]
    for i, dim in enumerate(dims):
        ax.bar(report_nos, dim_data[dim], bottom=bottom, label=dim, color=dim_colors[i], alpha=0.8)
        bottom = [bottom[j]+dim_data[dim][j] for j in range(len(valid_reports))]

    # 图表配置
    ax.set_xlabel("报告编号", fontsize=16)
    ax.set_ylabel("完全提取的维度数量 (0-5)", fontsize=16)
    ax.set_title("医疗报告数据提取完整性", fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(report_nos)
    ax.tick_params(axis='x', labelsize=14)
    ax.tick_params(axis='y', labelsize=14)
    ax.set_ylim(0, 5.5)
    ax.legend(loc='upper right', fontsize=14)
    ax.grid(axis='y', alpha=0.3)

    # 添加完整性得分标签
    scores = [sum([dim_data[dim][j] for dim in dims]) for j in range(len(valid_reports))]
    for no, score in zip(report_nos, scores):
        ax.text(no, score+0.1, f"得分：{score}", ha='center', va='bottom', fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表3已保存：{output_path}")


def plot_defect_distribution(defect_counts, report_details, output_path):
    """图表4：缺陷分布情况"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 缺陷类型饼图
    if not defect_counts.empty:
        labels = defect_counts.index.tolist()
        sizes = defect_counts.values.tolist()
        defect_color_map = {
            "缺失数值/参考范围": COLORS["missing_data"],
            "未提取到有效数据": COLORS["no_data"],
            "网络错误": COLORS["network_error"],
            "处理失败": COLORS["fail"]
        }
        colors = [defect_color_map.get(label, COLORS["incomplete"]) for label in labels]
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 16})
    else:
        ax1.text(0.5, 0.5, "无缺陷", ha='center', va='center', fontsize=18)
    ax1.set_title("缺陷类型分布", fontsize=18, fontweight='bold', pad=20)

    # 单报告缺陷数量柱状图
    defect_reports = {f"报告 {r['报告编号']}": r["缺陷数量"]
                     for r in report_details if r["缺陷数量"] > 0}
    if defect_reports:
        sorted_reports = sorted(defect_reports.items(), key=lambda x: x[1], reverse=True)
        labels, counts = zip(*sorted_reports)
        ax2.barh(labels, counts, color=COLORS["missing_data"], alpha=0.8)
        ax2.tick_params(axis='y', labelsize=14)
        for i, v in enumerate(counts):
            ax2.text(v+0.05, i, str(v), ha='left', va='center', fontweight='bold', fontsize=14)
    else:
        ax2.text(0.5, 0.5, "无缺陷报告", ha='center', va='center', fontsize=18)
    ax2.set_xlabel("缺陷数量", fontsize=16)
    ax2.set_title("单报告缺陷数量统计", fontsize=18, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表4已保存：{output_path}")


def plot_cross_modal_alignment(report_details, output_path):
    """图表5：跨模态对齐分析（匹配目标结构 + 修复tight_layout警告）"""
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except OSError:
        # 适配新版matplotlib的降级方案
        plt.style.use('seaborn-v0_8')
    # 2x2布局匹配目标图表结构
    fig, axes = plt.subplots(2, 2, figsize=(9, 7), gridspec_kw={'wspace': 0.2, 'hspace': 0.2})
    axes = axes.flatten()  # 转换为一维数组便于遍历

    # 状态配色方案（匹配目标图表）
    status_colors = {
        "perfect": "#d9e6a7",  # 浅绿（得分5分）
        "good": "#c9e3f8",     # 浅蓝（得分3-4分）
        "poor": "#f8d0d8"      # 粉色（得分<3分）
    }

    # 样本类型顺序（对应2x2布局）
    sample_types = [
        "凝血功能检测",
        "血型检测",
        "乙肝五项检测",
        "传染病筛查"
    ]
    success_reports = [r for r in report_details if r["处理状态"] == "success"]

    # 处理无成功报告的情况
    if not success_reports:
        for ax in axes:
            ax.text(0.5, 0.5, "无成功处理的报告", ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.axis('off')
    else:
        # 选择匹配目标图表的样本报告（优先匹配报告编号）
        sample_reports = []
        for target_type in sample_types:
            # 目标报告编号（匹配目标图表）
            target_report_nos = {
                "凝血功能检测": 3,
                "血型检测": 2,
                "乙肝五项检测": 10,
                "传染病筛查": 5
            }
            target_no = target_report_nos[target_type]
            # 优先查找编号和类型匹配的报告，否则降级匹配类型
            target_report = next(
                (r for r in success_reports if r["报告编号"] == target_no and r["报告类型"] == target_type),
                next((r for r in success_reports if r["报告类型"] == target_type), success_reports[0])
            )
            sample_reports.append(target_report)

        # 绘制每个子模块（匹配目标图表结构）
        for idx, (ax, report) in enumerate(zip(axes, sample_reports)):
            report_type = sample_types[idx]
            score = report["完整性得分"]

            # 根据得分确定状态和评估文本
            if score == 5:
                status = "perfect"
                eval_text = "□ 图像→文本完全对齐\n所有信息准确提取"
            elif 3 <= score <= 4:
                status = "good"
                eval_text = "□ 核心信息对齐\n部分次要信息缺失"
            else:
                status = "poor"
                eval_text = "□ 关键信息对齐度不足\n需优先优化"

            # 信息框内容（完全匹配目标图表）
            info_text = (
                f"报告编号：{report['报告编号']}\n"
                f"类型：{report_type}\n"
                f"状态：处理成功\n"
                f"得分：{score}/5\n"
                f"缺陷：{report['缺陷类型']}\n\n"
                "对齐性评估：\n"
                f"{eval_text}"
            )

            # 1. 子模块标题（信息框上方）
            ax.text(
                0.5, 0.96,
                f"跨模态对齐分析 – {report_type}",
                ha='center', va='top', transform=ax.transAxes,
                fontweight='bold', fontsize=12
            )

            # 2. 信息框（居中显示）
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

            # 隐藏坐标轴
            ax.axis('off')

    # 主标题（匹配目标图表）
    plt.suptitle(
        "医疗报告跨模态（图像→文本）对齐质量对比",
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

    # 保存图表
    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches='tight',
        facecolor='white'
    )
    plt.close()
    print(f"图表5已保存：{output_path}")

def generate_all_vlm_charts():
    """生成所有输出结果的主函数"""
    try:
        # 数据预处理
        data = parse_test_results(RESULTS_FILE)

        # 生成Excel报告
        generate_excel_report(data)

        # 生成图表
        plot_process_status(data["stats"], os.path.join(OUTPUT_DIR, "1_处理状态分布.png"))
        plot_report_type_performance(data["report_details"], data["type_counts"], os.path.join(OUTPUT_DIR, "2_报告类型处理表现.png"))
        plot_data_extraction_completeness(data["report_details"], os.path.join(OUTPUT_DIR, "3_数据提取完整性.png"))
        plot_defect_distribution(data["defect_counts"], data["report_details"], os.path.join(OUTPUT_DIR, "4_缺陷分布情况.png"))
        plot_cross_modal_alignment(data["report_details"], os.path.join(OUTPUT_DIR, "5_跨模态对齐分析.png"))

        print(f"\n所有输出结果生成成功！保存至：{OUTPUT_DIR}")

    except Exception as e:
        print(f"执行过程中出错：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_all_vlm_charts()