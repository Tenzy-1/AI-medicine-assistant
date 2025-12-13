from evalscope import TaskConfig, run_task

task_cfg = TaskConfig(
    model='unsloth/llama-3-8b-bnb-4bit',
    datasets=['general_qa'],  # Data format: The format for multiple-choice questions is fixed as 'general_qa'
    dataset_args={
        'general_qa': {
            "local_path": "qa", # Custom Dataset Path
            "subset_list": [
                # Name of the evaluation dataset. The * in the *.jsonl files can be configured to represent multiple sub-datasets.
                "med"       
            ]
        }
    },
)

run_task(task_cfg=task_cfg)