# 大模型微调课程项目 - 健康助手

医疗领域的大模型微调与应用开发，涵盖环境初始化到前端应用开发的全流程

## 项目特点

1. **完整的微调流程**: 从数据准备、模型微调、模型评估、模型服务部署的全流程
2. **医疗领域专用**: 专注于医疗领域的问答和图像分析
3. **多模型支持**: 支持大语言模型和视觉语言模型的微调
4. **端到端应用**: 包含可用于移动端和桌面端的响应式 Web 应用
5. **评估体系**: 提供微调前后的模型评估对比

## 项目结构

项目按照实施顺序分为以下步骤：

1. [0-env-init](0-env-init) - 环境初始化
   - 包含在不同平台（AutoDL、CloudStudio）上的环境初始化脚本和说明

2. [1-eval-data-prepare](1-eval-data-prepare) - 评估数据准备
   - 包含医疗领域问答数据集 CMB-Clin（Chinese-Medical-Benchmark）的数据处理脚本

3. [2-eval-before-tuning](2-eval-before-tuning) - 微调前评估
   - 包含对原始模型进行评估的脚本和结果

4. [3-fine-tuning-llm](3-fine-tuning-llm) - 大语言模型微调
   - 包含针对医疗领域的大语言模型微调的步骤和脚本

5. [4-eval-after-tuning](4-eval-after-tuning) - 微调后评估
   - 包含对微调后模型进行评估的脚本和结果

6. [5-build-server](5-build-server) - 服务构建
   - 包含提供模型服务的服务器代码

7. [6-fine-tuning-vl](6-fine-tuning-vl) - 视觉语言模型微调
   - 包含针对医疗图像的视觉语言模型微调脚本和相关工具

8. [7-endpoint-integration-server](7-endpoint-integration-server) - 端点集成服务
   - 包含医疗报告服务端点集成和测试客户端

9. [8-frontend-apps](8-frontend-apps) - 前端应用
   - 包含健康助手的 Web 应用

## 系统架构

```mermaid
graph TB
    subgraph "前端层"
        A[Web应用] -->|HTTP请求| D
        B[Android应用] -->|HTTP请求| D
    end

    subgraph "服务层"
        D[医疗报告分析服务] -->|API A请求| E[微调后图像QA API A<br>Qwen2.5-VL]
        D -->|API B请求| F[健康建议 API B<br>Qwen3]
    end

    subgraph "模型微调层"
        G[大语言模型微调] --> H[Qwen2.5 14B]
        I[视觉语言模型微调] --> J[Qwen2-VL 7B]
    end

    subgraph "评估层"
        K[微调前评估] --> L[评估报告]
        M[微调后评估] --> N[评估报告]
    end

    subgraph "数据层"
        O[CMB-Clin医疗问答数据集]
        P[医疗图像数据集]
    end

    H --> D
    J --> D
```

## 部署图

以下部署图展示了项目在服务器和客户端的部署情况：

```mermaid
graph LR
    subgraph "客户端设备"
        A[Web浏览器]
        B[Android设备]
    end

    subgraph "服务器端"
        subgraph "应用服务器"
            C[医疗报告服务]
        end
        
        subgraph "模型API服务"
            D[Qwen2.5-VL API]
            E[Qwen3 API]
        end
        
        subgraph "数据存储"
            F[CMB-Clin数据集]
            G[医疗图像数据集]
        end
    end

    A -- "HTTP请求" --> C
    B -- "HTTP请求" --> C
    C -- "API调用" --> D
    C -- "API调用" --> E
    D -- "数据访问" --> G
    E -- "数据访问" --> F
```

## 时序图

以下时序图展示了用户通过Web应用请求医疗图像分析的完整流程：

```mermaid
sequenceDiagram
    participant U as 用户
    participant W as Web应用
    participant S as 医疗报告服务
    participant API_A as Qwen2.5-VL API
    participant API_B as Qwen3 API

    U->>W: 上传医疗图像
    W->>S: 发送图像分析请求
    S->>API_A: 调用图像问答API
    API_A-->>S: 返回图像分析结果
    S->>API_B: 调用健康建议API
    API_B-->>S: 返回健康建议
    S-->>W: 返回完整分析报告
    W-->>U: 展示分析结果
```

## 数据流图

以下数据流图展示了数据在系统中的流动过程：

```mermaid
graph LR
    A[用户] --> B[Web/Android应用]
    B --> C[医疗报告服务]
    
    subgraph "数据处理流程"
        C --> D[图像分析请求]
        C --> E[健康建议请求]
        D --> F[Qwen2.5-VL模型]
        E --> G[Qwen3模型]
        F --> H[图像分析结果]
        G --> I[健康建议结果]
        H --> C
        I --> C
    end
    
    subgraph "数据源"
        J[CMB-Clin数据集]
        K[医疗图像数据集]
    end
    
    C --> L[分析报告]
    L --> A
    F -.-> K
    G -.-> J
```

## 技术栈

- **模型微调**: Qwen2.5, Unsloth
- **视觉语言模型微调**: Qwen2-VL, Unsloth
- **后端**: Python, Flask
- **前端**: 
  - Web: HTML, CSS, JavaScript
- **评估**: EvalScope

## 使用说明

按照目录顺序逐步执行项目，每个目录都有其特定的功能和依赖关系。   
   
建议按照数字顺序（0, 1, 2, ...）依次完成各步骤。

## 注意事项

- 执行前请确保已按照[0-env-init](0-env-init)目录中的说明完成环境配置
- 某些步骤可能需要大量的计算资源，需要在有GPU的环境下运行
- 各步骤之间存在依赖关系，请按顺序执行

## 项目截图

### 服务端集成界面

![服务端集成界面](7-endpoint-integration-server/screenshot.png)

### 前端应用界面

#### 主界面和图片选择
![前端应用界面1](8-frontend-apps/HealthAssistantWebApp/screenshot1.png)

#### 上传图片和等待动画
![前端应用界面2](8-frontend-apps/HealthAssistantWebApp/screenshot2.png)

#### 分析结果展示
![前端应用界面3](8-frontend-apps/HealthAssistantWebApp/screenshot3.png)

## 参考资料

1. [上海交大人工智能学院论文：Towards Evaluating and Building Versatile Large Language Models for Medicine](https://arxiv.org/pdf/2408.12547)
2. [上海交大人工智能学院智慧医疗团队在开源大语言模型的临床任务测评与对齐研究中取得新进展](https://news.sjtu.edu.cn/jdzh/20250304/207662.html)
3. [MedBench: 所有医学相关任务的综合基准](https://medbench.opencompass.org.cn/home)