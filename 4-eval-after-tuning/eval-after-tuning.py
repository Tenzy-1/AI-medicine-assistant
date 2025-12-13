from evalscope import TaskConfig, run_task
import os

print("原始工作路径:", os.getcwd())
os.chdir("/workspace/")
print("新工作路径:", os.getcwd())

task_cfg = TaskConfig(
    model='model/',
    datasets=['general_qa'], 
    dataset_args={
        'general_qa': {
            "local_path": "qa",  
            "subset_list": [
             
                "med"       
            ]
        }
    },
)

run_task(task_cfg=task_cfg)