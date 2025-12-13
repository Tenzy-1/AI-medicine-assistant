# 医疗报告分析服务器

这是一个使用来自OpenRouter的两个OpenAI兼容API处理医疗报告图像的Python Flask服务器。

## 功能

1. 接收来自Android应用程序的医疗报告图像
2. 将图像发送到API A (qwen/qwen2.5-vl-32b-instruct:free) 进行医疗报告分析
3. 将分析结果发送到API B (qwen/qwen3-30b-a3b:free) 获取健康建议
4. 将健康建议返回给Android应用程序

## 先决条件

- Python 3.7 或更高版本
- pip (Python包安装程序)

## 安装

1. 克隆或下载此仓库
2. 安装所需包：
   ```
   pip install -r requirements.txt
   ```

## 使用方法

1. 运行服务器：
   ```
   python medical_report_server.py
   ```

2. 服务器将在 `http://localhost:5000` 启动

## API端点

### 分析医疗报告

- **URL**: `/analyze_medical_report`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **文件参数**: `image` (医疗报告图像)
- **成功响应**: 
  - **代码**: 200
  - **内容**: 
    ```json
    {
      "analysis_result": "识别出医疗报告中的异常...",
      "health_recommendations": "根据分析结果，以下是健康建议..."
    }
    ```

### 健康检查

- **URL**: `/health`
- **方法**: `GET`
- **成功响应**: 
  - **代码**: 200
  - **内容**: 
    ```json
    {
      "status": "healthy"
    }
    ```

## 工作原理

1. Android应用程序向 `/analyze_medical_report` 发送POST请求，包含医疗报告图像
2. 服务器将图像编码为base64
3. 服务器将图像发送到API A (qwen/qwen2.5-vl-32b-instruct:free)，提示识别医疗报告中的异常指标
4. 服务器从API A接收分析结果
5. 服务器将分析结果发送到API B (qwen/qwen3-30b-a3b:free)，提示提供健康建议
6. 服务器从API B接收健康建议
7. 服务器将分析结果和健康建议返回给Android应用程序

## 提示词工程

### API A (图像分析)
```
请仔细分析这张医学检测报告图片，识别并列出其中的异常指标。如果没有发现异常指标，请明确说明'未发现异常指标'。请以简洁、专业的中文医学术语回答。
```

### API B (健康建议)
```
根据以下医学检测报告分析结果，提供相应的健康建议和注意事项：

[analysis result]

请以简洁明了的中文给出实用的健康建议，包括饮食、运动和生活方式等方面的指导。
```