import json

def process_metadata(input_file, output_file):
    """
    Process metadata.jsonl file to add prefix and suffix to additional_feature fields
    """
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            # Parse each line as JSON
            data = json.loads(line.strip())
            
            # Modify the additional_feature field
            if 'additional_feature' in data:
                original_feature = data['additional_feature']
                modified_feature = f"小智提示：{original_feature} （AI 分析仅供参考）"
                data['additional_feature'] = modified_feature
            
            # Write the modified JSON back to the output file
            outfile.write(json.dumps(data, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    input_file = "train/metadata.jsonl"
    output_file = "train/metadata_modified.jsonl"
    
    process_metadata(input_file, output_file)
    print(f"Processing complete. Modified file saved as {output_file}")