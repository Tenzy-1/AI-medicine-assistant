"""
医疗模型评估脚本 - 微调后评估
优化版本：添加了配置管理、错误处理、日志记录和工作目录管理
"""
import os
import sys
import logging
from pathlib import Path
from evalscope import TaskConfig, run_task

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('eval_after_tuning.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 配置参数（可通过环境变量覆盖）
EVAL_CONFIG = {
    'workspace_dir': os.getenv('WORKSPACE_DIR', '/workspace'),
    'model_path': os.getenv('EVAL_MODEL_PATH', 'model/'),
    'dataset_type': os.getenv('EVAL_DATASET_TYPE', 'general_qa'),
    'local_path': os.getenv('EVAL_LOCAL_PATH', 'qa'),
    'subset_list': os.getenv('EVAL_SUBSET_LIST', 'med').split(','),
    'output_dir': os.getenv('EVAL_OUTPUT_DIR', 'eval_results'),
}

def setup_workspace(workspace_dir):
    """设置工作目录"""
    original_dir = os.getcwd()
    workspace_path = Path(workspace_dir)
    
    logger.info(f"原始工作路径: {original_dir}")
    
    if not workspace_path.exists():
        logger.warning(f"工作目录不存在，尝试创建: {workspace_path}")
        workspace_path.mkdir(parents=True, exist_ok=True)
    
    try:
        os.chdir(str(workspace_path))
        logger.info(f"新工作路径: {os.getcwd()}")
        return original_dir
    except Exception as e:
        logger.error(f"无法切换到工作目录 {workspace_path}: {str(e)}")
        raise

def validate_config(config):
    """验证配置参数"""
    errors = []
    
    if not config['model_path']:
        errors.append("模型路径不能为空")
    
    model_path = Path(config['model_path'])
    if not model_path.exists() and not model_path.is_absolute():
        # 相对路径，检查工作目录下是否存在
        full_path = Path(os.getcwd()) / model_path
        if not full_path.exists():
            logger.warning(f"模型路径可能不存在: {full_path} (将尝试继续)")
    
    if not config['local_path']:
        errors.append("数据集路径不能为空")
    
    local_path = Path(config['local_path'])
    # 如果是相对路径，尝试基于当前工作目录解析
    if not local_path.is_absolute():
        local_path = Path(os.getcwd()) / local_path
    if not local_path.exists():
        errors.append(f"数据集路径不存在: {local_path}")
    
    if not config['subset_list']:
        errors.append("子集列表不能为空")
    
    if errors:
        raise ValueError(f"配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return True

def run_evaluation(config):
    """运行评估任务"""
    original_dir = None
    try:
        logger.info("=" * 80)
        logger.info("开始医疗模型评估（微调后）")
        logger.info("=" * 80)
        
        # 设置工作目录
        original_dir = setup_workspace(config['workspace_dir'])
        
        logger.info(f"模型路径: {config['model_path']}")
        logger.info(f"数据集类型: {config['dataset_type']}")
        logger.info(f"数据集路径: {config['local_path']}")
        logger.info(f"子集列表: {config['subset_list']}")
        logger.info("=" * 80)
        
        # 验证配置
        validate_config(config)
        
        # 创建输出目录
        output_dir = Path(config['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建任务配置
        task_cfg = TaskConfig(
            model=config['model_path'],
            datasets=[config['dataset_type']],
            dataset_args={
                config['dataset_type']: {
                    "local_path": config['local_path'],
                    "subset_list": config['subset_list']
                }
            },
        )
        
        # 运行评估
        logger.info("开始执行评估任务...")
        results = run_task(task_cfg=task_cfg)
        
        logger.info("=" * 80)
        logger.info("评估任务完成")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"评估过程中发生错误: {str(e)}", exc_info=True)
        raise
    finally:
        # 恢复原始工作目录
        if original_dir:
            try:
                os.chdir(original_dir)
                logger.info(f"已恢复原始工作路径: {original_dir}")
            except Exception as e:
                logger.warning(f"无法恢复原始工作目录: {str(e)}")

if __name__ == "__main__":
    try:
        run_evaluation(EVAL_CONFIG)
    except KeyboardInterrupt:
        logger.warning("用户中断评估")
        sys.exit(1)
    except Exception as e:
        logger.error(f"评估失败: {str(e)}")
        sys.exit(1)