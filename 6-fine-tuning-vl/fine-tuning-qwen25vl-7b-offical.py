# 导入Unsloth针对多模态（视觉+语言）模型的核心优化类FastVisionModel
# 区别于纯语言模型的FastLanguageModel，专为图文融合模型设计（如Qwen2.5-VL）
from unsloth import FastVisionModel
import torch  # 导入PyTorch，作为模型加载、张量计算的基础

# 加载Qwen2.5-VL-7B-Instruct多模态预训练模型和配套分词器/视觉处理器
# 返回值：model为多模态模型实例，tokenizer包含文本分词+图片预处理逻辑
model, tokenizer = FastVisionModel.from_pretrained(
    "Qwen/Qwen2.5-VL-7B-Instruct",  # 指定多模态模型名称（7B规模，指令微调版）
    load_in_4bit = False,  # 关闭4位量化（16位精度微调视觉层效果更好；若显存不足可设为True）
    use_gradient_checkpointing = False,  # 关闭梯度检查点（视觉层微调时开启可能降低精度；长文本场景可设为"unsloth"）
)

# 为多模态模型配置LoRA（低秩适配）微调策略，支持同时微调视觉/语言层
model = FastVisionModel.get_peft_model(
    model,
    finetune_vision_layers     = True,  # 微调视觉编码层（核心：医学图片特征提取需适配垂直领域）
    finetune_language_layers   = True,  # 微调语言生成层（核心：医学报告解读的文本生成逻辑）
    finetune_attention_modules = True,  # 微调图文融合注意力层（保证图片特征与文本指令的对齐）
    finetune_mlp_modules       = True,  # 微调MLP层（增强模型对医学指标的推理能力）

    r = 16,           # LoRA低秩矩阵秩：16平衡微调效果与显存（越大拟合能力越强，易过拟合）
    lora_alpha = 16,  # LoRA缩放系数：推荐与r取值一致，平衡参数更新幅度
    lora_dropout = 0, # 关闭Dropout（小样本医学数据集避免过拟合）
    bias = "none",    # 不训练偏置参数，减少训练量
    random_state = 3407,  # 固定随机种子，保证实验可复现
    use_rslora = False,  # 关闭秩稳定LoRA（7B模型无需启用）
    loftq_config = None, # 关闭LoftQ初始化（16位精度无需量化感知初始化）
    # target_modules = "all-linear", # 可选：指定仅微调线性层；多模态默认覆盖视觉+语言核心层
)

# 导入Hugging Face的datasets库，用于加载图片数据集
from datasets import load_dataset
# 加载本地图片数据集（imagefolder格式：文件夹下按分类/直接存图片，配套标签文件）
# data_dir：指定训练数据集的本地路径（包含医学报告图片+标签）
dataset = load_dataset(path="imagefolder",
                       data_dir="/workspace/6-fine-tuning-vl/dataset-img-train")

# 定义微调任务的固定指令：要求模型解读医学报告并一句话指出异常指标
instruction = "解读这个医学报告，一句话指出其中异常指标"

# 定义数据格式转换函数：将原始图片数据集转换为Qwen2.5-VL要求的多模态对话格式
def convert_to_conversation(sample):
    # 构建多模态对话结构（Qwen2.5-VL的标准格式）
    conversation = [
        # 用户角色：输入包含「文本指令」+「医学报告图片」
        { "role": "user",
          "content" : [
            {"type" : "text",  "text"  : instruction},  # 文本指令
            {"type" : "image", "image" : sample["image"]}  # 医学报告图片（从数据集样本中读取）
          ]
        },
        # 助手角色：输出标注好的异常指标文本（sample["additional_feature"]为数据集的标签字段）
        { "role" : "assistant",
          "content" : [
            {"type" : "text",  "text"  : sample["additional_feature"]}
          ]
        },
    ]
    # 返回转换后的格式（key为"messages"，适配后续训练器）
    return { "messages" : conversation }
pass  # 函数结束标记（Python语法，无实际作用）

# 遍历训练集，将所有样本转换为多模态对话格式
converted_dataset = [convert_to_conversation(sample) for sample in dataset["train"]]

# 导入多模态专属的数据整理器（必须使用，处理图片张量+文本token的对齐）
from unsloth.trainer import UnslothVisionDataCollator
# 导入TRL的SFT训练器和配置类（适配大模型监督微调）
from trl import SFTTrainer, SFTConfig

# 将模型切换为训练模式（Unsloth封装的优化：启用梯度计算、适配多模态训练逻辑）
FastVisionModel.for_training(model)

# 初始化多模态模型的SFT训练器（监督微调）
trainer = SFTTrainer(
    model = model,  # 传入配置好LoRA的多模态模型
    tokenizer = tokenizer,  # 传入多模态分词器/视觉处理器
    # 多模态必须使用UnslothVisionDataCollator：自动处理图片预处理、文本token化、批次张量对齐
    data_collator = UnslothVisionDataCollator(model, tokenizer),
    train_dataset = converted_dataset,  # 传入转换后的多模态训练集
    # 训练超参数配置（SFTConfig是SFTTrainer的专属配置类）
    args = SFTConfig(
        per_device_train_batch_size = 2,  # 单GPU批次大小（2适配10GB+显存，显存不足可设为1）
        gradient_accumulation_steps = 4,  # 梯度累积步数：等效总批次=2*4=8（平衡显存与训练稳定性）
        warmup_steps = 5,  # 学习率预热步数：前5步线性升温，避免初始学习率过大
        max_steps = 30,  # 最大训练步数（小样本医学数据集30步足够适配）
        # num_train_epochs = 1, # 可选：替代max_steps，训练完整轮数
        learning_rate = 2e-4,  # LoRA微调学习率（多模态模型推荐2e-4）
        logging_steps = 1,  # 每1步打印训练日志（损失、学习率等）
        optim = "adamw_8bit",  # 8位量化AdamW优化器：降低50%显存占用
        weight_decay = 0.01,  # 权重衰减：抑制过拟合
        lr_scheduler_type = "linear",  # 学习率线性衰减（预热后逐步降至0）
        seed = 3407,  # 固定随机种子
        output_dir = "outputs",  # 训练结果保存路径（模型权重、日志）
        report_to = "none",     # 禁用第三方日志工具（如WandB）

        # 多模态微调必须配置的参数（缺一不可）
        remove_unused_columns = False,  # 保留图片列，不自动删除（纯文本微调默认True，多模态需关闭）
        dataset_text_field = "",  # 文本字段置空（多模态数据不在单一文本字段，由collator处理）
        dataset_kwargs = {"skip_prepare_dataset": True},  # 跳过TRL默认的文本预处理（由Unsloth collator处理）
        max_length = 2048,  # 最大序列长度（适配图文融合的输入长度）
    ),
)

# 打印GPU初始内存状态（监控训练显存占用）
gpu_stats = torch.cuda.get_device_properties(0)  # 获取第0块GPU的硬件信息
start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)  # 已预留显存（GB）
max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)  # GPU总显存（GB）
print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
print(f"{start_gpu_memory} GB of memory reserved.")

# 启动训练，返回训练统计信息（如耗时、损失等）
trainer_stats = trainer.train()

# 打印训练完成后的内存和时间统计
used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)  # 峰值预留显存
used_memory_for_lora = round(used_memory - start_gpu_memory, 3)  # 训练新增显存占用
used_percentage = round(used_memory / max_memory * 100, 3)  # 峰值显存占比
lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)  # 训练新增显存占比
print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")  # 训练总耗时（秒）
print(f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training.")  # 训练总耗时（分钟）
print(f"Peak reserved memory = {used_memory} GB.")  # 峰值显存
print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")  # 训练新增显存
print(f"Peak reserved memory % of max memory = {used_percentage} %.")  # 峰值显存占比
print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")  # 训练新增显存占比

# 合并LoRA参数与主模型，并保存微调后的完整模型（含tokenizer）
# 保存路径：qwen25vl-7b-offical-finetuned，可直接用于推理
model.save_pretrained_merged("qwen25vl-7b-offical-finetuned", tokenizer,)