// 应用状态管理
const AppState = {
    currentChat: [],
    chatHistory: JSON.parse(localStorage.getItem('chatHistory') || '[]'),
    theme: localStorage.getItem('theme') || 'light',
    currentRequest: null,
    serverUrl: 'http://101.32.126.91:80'
};

// DOM元素
const elements = {
    chatContainer: document.getElementById('chatContainer'),
    imageInput: document.getElementById('imageInput'),
    imageInputLabel: document.getElementById('imageInputLabel'),
    sendButton: document.getElementById('sendButton'),
    imagePreviewContainer: document.getElementById('imagePreviewContainer'),
    welcomeScreen: document.getElementById('welcomeScreen'),
    sidebar: document.getElementById('sidebar'),
    sidebarToggle: document.getElementById('sidebarToggle'),
    newChatBtn: document.getElementById('newChatBtn'),
    chatHistory: document.getElementById('chatHistory'),
    themeToggle: document.getElementById('themeToggle'),
    statusIndicator: document.getElementById('statusIndicator')
};

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadChatHistory();
    applyTheme();
});

// 初始化应用
function initializeApp() {
    // 从URL获取服务器地址（如果有）
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('server')) {
        AppState.serverUrl = urlParams.get('server');
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 图片选择
    elements.imageInput.addEventListener('change', handleImageSelect);
    // 移除图片按钮现在在预览中动态创建
    elements.sendButton.addEventListener('click', handleSend);
    
    // 侧边栏
    elements.sidebarToggle.addEventListener('click', toggleSidebar);
    elements.newChatBtn.addEventListener('click', startNewChat);
    elements.themeToggle.addEventListener('click', toggleTheme);
    
    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.sidebar.classList.contains('open')) {
            toggleSidebar();
        }
    });
    
    // 点击外部关闭侧边栏（移动端）
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && 
            elements.sidebar.classList.contains('open') &&
            !elements.sidebar.contains(e.target) &&
            !elements.sidebarToggle.contains(e.target)) {
            toggleSidebar();
        }
    });
}

// 应用主题
function applyTheme() {
    document.documentElement.setAttribute('data-theme', AppState.theme);
    elements.themeToggle.innerHTML = AppState.theme === 'dark' 
        ? getMoonIcon() 
        : getSunIcon();
}

// 切换主题
function toggleTheme() {
    AppState.theme = AppState.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', AppState.theme);
    applyTheme();
}

// 切换侧边栏
function toggleSidebar() {
    elements.sidebar.classList.toggle('open');
}

// 开始新对话
function startNewChat() {
    if (AppState.currentChat.length > 0) {
        saveCurrentChat();
    }
    AppState.currentChat = [];
    clearChatContainer();
    showWelcomeScreen();
    updateStatus('就绪');
}

// 处理图片选择
function handleImageSelect(e) {
    if (e.target.files && e.target.files.length > 0) {
        const file = e.target.files[0];
        compressImage(file, (compressedFile) => {
            displayImagePreview(compressedFile);
            elements.sendButton.disabled = false;
        });
    }
}

// 压缩图片（客户端）
function compressImage(file, callback) {
    const maxWidth = 1920;
    const maxHeight = 1920;
    const quality = 0.85;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement('canvas');
            let width = img.width;
            let height = img.height;
            
            // 计算新尺寸
            if (width > height) {
                if (width > maxWidth) {
                    height = (height * maxWidth) / width;
                    width = maxWidth;
                }
            } else {
                if (height > maxHeight) {
                    width = (width * maxHeight) / height;
                    height = maxHeight;
                }
            }
            
            canvas.width = width;
            canvas.height = height;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            
            canvas.toBlob((blob) => {
                const compressedFile = new File([blob], file.name, {
                    type: 'image/jpeg',
                    lastModified: Date.now()
                });
                callback(compressedFile);
            }, 'image/jpeg', quality);
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

// 显示图片预览
function displayImagePreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        // 创建预览包装器
        const previewWrapper = document.createElement('div');
        previewWrapper.className = 'preview-wrapper';
        
        const img = document.createElement('img');
        img.src = e.target.result;
        img.alt = '医疗报告预览';
        img.style.maxWidth = '120px';
        img.style.maxHeight = '120px';
        img.style.borderRadius = '8px';
        img.style.objectFit = 'cover';
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-image-btn';
        removeBtn.innerHTML = '×';
        removeBtn.title = '移除图片';
        removeBtn.onclick = () => {
            previewWrapper.remove();
            if (elements.imagePreviewContainer.children.length === 0) {
                elements.imagePreviewContainer.style.display = 'none';
            }
            elements.sendButton.disabled = true;
            AppState.selectedImage = null;
        };
        
        previewWrapper.appendChild(img);
        previewWrapper.appendChild(removeBtn);
        elements.imagePreviewContainer.appendChild(previewWrapper);
        elements.imagePreviewContainer.style.display = 'flex';
        AppState.selectedImage = file;
    };
    reader.readAsDataURL(file);
}

// 移除图片
function removeImage() {
    elements.imageInput.value = '';
    elements.imagePreviewContainer.innerHTML = '';
    elements.imagePreviewContainer.style.display = 'none';
    elements.sendButton.disabled = true;
    AppState.selectedImage = null;
}

// 处理发送
function handleSend() {
    if (!AppState.selectedImage) return;
    
    const imageFile = AppState.selectedImage;
    sendImageToServer(imageFile);
}

// 发送图片到服务器
function sendImageToServer(imageFile) {
    // 保存图片文件以便重试
    AppState.lastImageFile = imageFile;
    
    // 隐藏欢迎界面
    hideWelcomeScreen();
    
    // 显示用户图片
    displayUserImage(imageFile);
    
    // 清除输入
    removeImage();
    
    // 显示加载消息
    const loadingMessageId = displayLoadingMessage();
    updateStatus('分析中...');
    
    // 创建FormData
    const formData = new FormData();
    formData.append('image', imageFile);
    
    // 创建请求
    const xhr = new XMLHttpRequest();
    AppState.currentRequest = xhr;
    
    xhr.open('POST', `${AppState.serverUrl}/analyze_medical_report`, true);
    xhr.timeout = 600000; // 10分钟
    
    // 添加进度监听
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable && loadingProgress) {
            const uploadProgress = (e.loaded / e.total) * 25; // 上传占25%
            loadingProgress.style.width = `${uploadProgress}%`;
        }
    });
    
    xhr.onload = function() {
        AppState.currentRequest = null;
        clearLoadingTimer();
        removeMessageById(loadingMessageId);
        updateStatus('就绪');
        
        if (xhr.status === 200) {
            try {
                const response = JSON.parse(xhr.responseText);
                // 显示处理时间信息
                if (response.processing_time) {
                    console.log(`处理完成，总耗时: ${response.processing_time}秒`);
                }
                displayServerResponse(response);
            } catch (e) {
                displayErrorMessage('解析服务器响应时出错: ' + e.message);
                showToast('解析响应失败', 'error');
            }
        } else {
            try {
                const errorResponse = JSON.parse(xhr.responseText);
                displayErrorMessage(`服务器错误: ${xhr.status} - ${errorResponse.error}`);
                showToast('服务器错误', 'error');
                // 添加重试按钮
                addRetryButton(errorResponse.error);
            } catch (e) {
                displayErrorMessage(`服务器错误: ${xhr.status}`);
                showToast('服务器错误', 'error');
                addRetryButton('未知错误');
            }
        }
    };
    
    xhr.onerror = function() {
        AppState.currentRequest = null;
        clearLoadingTimer();
        removeMessageById(loadingMessageId);
        updateStatus('就绪');
        displayErrorMessage('网络错误，请检查连接。');
        showToast('网络错误', 'error');
        addRetryButton('网络错误');
    };
    
    xhr.ontimeout = function() {
        AppState.currentRequest = null;
        clearLoadingTimer();
        removeMessageById(loadingMessageId);
        updateStatus('就绪');
        displayErrorMessage('请求超时，请稍后重试。');
        showToast('请求超时', 'error');
        addRetryButton('请求超时');
    };
    
    xhr.send(formData);
}

// 显示用户图片
function displayUserImage(imageFile) {
    const messageDiv = createMessageElement('user');
    const img = document.createElement('img');
    img.src = URL.createObjectURL(imageFile);
    img.alt = '上传的医疗报告';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '300px';
    img.style.borderRadius = '8px';
    
    img.onload = function() {
        URL.revokeObjectURL(img.src);
    };
    
    messageDiv.querySelector('.message-content').appendChild(img);
    elements.chatContainer.appendChild(messageDiv);
    AppState.currentChat.push({ type: 'user', content: 'image', file: imageFile });
    scrollToBottom();
}

// 显示加载消息（改进版）
let loadingTimer = null;
let loadingProgress = null;
function displayLoadingMessage() {
    const messageDiv = createMessageElement('assistant');
    messageDiv.id = 'loading-' + Date.now();
    
    const loadingContainer = document.createElement('div');
    loadingContainer.style.display = 'flex';
    loadingContainer.style.flexDirection = 'column';
    loadingContainer.style.gap = '12px';
    
    const statusText = document.createElement('div');
    statusText.className = 'loading-status';
    statusText.textContent = '正在分析医疗报告...';
    statusText.style.fontSize = '14px';
    statusText.style.color = 'var(--text-secondary)';
    
    const loadingDots = document.createElement('div');
    loadingDots.className = 'loading-dots';
    loadingDots.innerHTML = '<span></span><span></span><span></span>';
    
    // 添加进度条
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    progressBar.style.width = '100%';
    progressBar.style.height = '4px';
    progressBar.style.backgroundColor = 'var(--bg-tertiary)';
    progressBar.style.borderRadius = '2px';
    progressBar.style.overflow = 'hidden';
    progressBar.style.marginTop = '8px';
    
    const progressFill = document.createElement('div');
    progressFill.className = 'progress-fill';
    progressFill.style.height = '100%';
    progressFill.style.width = '0%';
    progressFill.style.background = 'var(--accent-gradient)';
    progressFill.style.borderRadius = '2px';
    progressFill.style.transition = 'width 0.3s ease';
    progressBar.appendChild(progressFill);
    loadingProgress = progressFill;
    
    const timerDiv = document.createElement('div');
    timerDiv.className = 'timer';
    timerDiv.textContent = '0秒';
    
    loadingContainer.appendChild(statusText);
    loadingContainer.appendChild(loadingDots);
    loadingContainer.appendChild(progressBar);
    loadingContainer.appendChild(timerDiv);
    
    messageDiv.querySelector('.message-content').appendChild(loadingContainer);
    elements.chatContainer.appendChild(messageDiv);
    scrollToBottom();
    
    // 模拟进度（实际进度由服务器响应控制）
    let progress = 25; // 从25%开始（上传完成）
    const progressInterval = setInterval(() => {
        if (progress < 95) {
            // 更平滑的进度增长
            const increment = Math.random() * 2 + 0.5;
            progress = Math.min(progress + increment, 95);
            if (loadingProgress) {
                loadingProgress.style.width = `${progress}%`;
            }
        }
    }, 800);
    
    let seconds = 0;
    loadingTimer = setInterval(function() {
        seconds++;
        timerDiv.textContent = `${seconds}秒`;
    }, 1000);
    
    // 保存进度间隔以便清理
    messageDiv._progressInterval = progressInterval;
    
    return messageDiv.id;
}

// 清除加载计时器
function clearLoadingTimer() {
    if (loadingTimer) {
        clearInterval(loadingTimer);
        loadingTimer = null;
    }
    // 完成进度条
    if (loadingProgress) {
        loadingProgress.style.width = '100%';
        setTimeout(() => {
            loadingProgress = null;
        }, 300);
    }
    // 清除所有进度间隔
    document.querySelectorAll('[id^="loading-"]').forEach(el => {
        if (el._progressInterval) {
            clearInterval(el._progressInterval);
        }
    });
}

// 显示服务器响应
function displayServerResponse(response) {
    // 分析结果
    const analysisMessage = createMessageElement('assistant');
    const analysisSection = document.createElement('div');
    analysisSection.className = 'analysis-section';
    
    const analysisTitle = document.createElement('h3');
    analysisTitle.innerHTML = '<span style="margin-right: 8px;">📊</span>检测结果分析';
    
    // 添加处理时间信息（如果有）
    if (response.processing_time) {
        const timeInfo = document.createElement('div');
        timeInfo.style.cssText = 'font-size: 12px; color: var(--text-secondary); margin-top: 4px;';
        timeInfo.textContent = `处理时间: ${response.processing_time}秒`;
        analysisTitle.appendChild(timeInfo);
    }
    
    const analysisContent = document.createElement('div');
    analysisContent.className = 'markdown-content';
    typewriterEffect(analysisContent, response.analysis_result, () => {
        // 分析完成后再显示建议
        setTimeout(() => {
            displayRecommendations(response.health_recommendations);
        }, 800);
    });
    
    analysisSection.appendChild(analysisTitle);
    analysisSection.appendChild(analysisContent);
    analysisMessage.querySelector('.message-content').appendChild(analysisSection);
    elements.chatContainer.appendChild(analysisMessage);
    scrollToBottom();
    
    AppState.currentChat.push({
        type: 'assistant',
        content: 'analysis',
        text: response.analysis_result
    });
}

// 显示健康建议
function displayRecommendations(recommendations) {
    const recommendationMessage = createMessageElement('assistant');
    const recommendationSection = document.createElement('div');
    recommendationSection.className = 'recommendation-section';
    
    const recommendationTitle = document.createElement('h3');
    recommendationTitle.innerHTML = '<span style="margin-right: 8px;">💡</span>健康建议';
    
    const recommendationContent = document.createElement('div');
    recommendationContent.className = 'markdown-content';
    typewriterEffect(recommendationContent, recommendations, () => {
        // 显示完成提示
        showToast('分析完成', 'success');
    });
    
    recommendationSection.appendChild(recommendationTitle);
    recommendationSection.appendChild(recommendationContent);
    recommendationMessage.querySelector('.message-content').appendChild(recommendationSection);
    elements.chatContainer.appendChild(recommendationMessage);
    scrollToBottom();
    
    AppState.currentChat.push({
        type: 'assistant',
        content: 'recommendations',
        text: recommendations
    });
}

// 打字机效果（改进版，支持更流畅的显示）
function typewriterEffect(element, text, onComplete) {
    const html = convertMarkdownToHtml(text);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const textContent = tempDiv.textContent || tempDiv.innerText || '';
    
    // 如果文本太长，直接显示以提高性能
    if (textContent.length > 2000) {
        element.innerHTML = html;
        if (onComplete) onComplete();
        return;
    }
    
    let index = 0;
    const baseSpeed = 15; // 基础打字速度（毫秒）
    let currentSpeed = baseSpeed;
    
    function type() {
        if (index < textContent.length) {
            // 动态调整速度：标点符号后稍慢
            const char = textContent[index];
            if (['。', '，', '！', '？', '.', ',', '!', '?'].includes(char)) {
                currentSpeed = baseSpeed * 2;
            } else {
                currentSpeed = baseSpeed;
            }
            
            // 计算当前应该显示的文本长度
            const displayLength = index + 1;
            const ratio = displayLength / textContent.length;
            const textToShow = text.substring(0, Math.floor(text.length * ratio));
            
            element.innerHTML = convertMarkdownToHtml(textToShow);
            index++;
            
            // 自动滚动到底部
            if (index % 10 === 0) {
                scrollToBottom();
            }
            
            setTimeout(type, currentSpeed);
        } else {
            element.innerHTML = html;
            scrollToBottom();
            if (onComplete) onComplete();
        }
    }
    
    type();
}

// 创建消息元素
function createMessageElement(type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = type === 'user' ? '你' : 'AI';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const actions = document.createElement('div');
    actions.className = 'message-actions';
    
    if (type === 'assistant') {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" style="margin-right: 4px;"><path d="M9.5 1H3.5C2.67 1 2 1.67 2 2.5V10.5H3.5V2.5H9.5V1ZM11 3.5H5.5C4.67 3.5 4 4.17 4 5V11.5C4 12.33 4.67 13 5.5 13H11C11.83 13 12.5 12.33 12.5 11.5V5C12.5 4.17 11.83 3.5 11 3.5ZM11 11.5H5.5V5H11V11.5Z" fill="currentColor"/></svg>复制';
        copyBtn.onclick = function() {
            copyMessageContent(content);
        };
        actions.appendChild(copyBtn);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    messageDiv.appendChild(actions);
    
    return messageDiv;
}

// 复制消息内容
function copyMessageContent(element) {
    const text = element.textContent || element.innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板', 'success');
    }).catch(() => {
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('已复制到剪贴板', 'success');
    });
}

// 显示错误消息（改进版）
function displayErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style="flex-shrink: 0;">
                <path d="M10 18C14.4183 18 18 14.4183 18 10C18 5.58172 14.4183 2 10 2C5.58172 2 2 5.58172 2 10C2 14.4183 5.58172 18 10 18Z" stroke="currentColor" stroke-width="2"/>
                <path d="M10 6V10M10 14H10.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>${message}</span>
        </div>
    `;
    elements.chatContainer.appendChild(errorDiv);
    scrollToBottom();
}

// 添加重试按钮
function addRetryButton(errorType) {
    const errorDiv = document.querySelector('.error-message:last-child');
    if (!errorDiv) return;
    
    const retryBtn = document.createElement('button');
    retryBtn.className = 'retry-button';
    retryBtn.textContent = '🔄 重试';
    retryBtn.style.cssText = `
        margin-top: 12px;
        padding: 8px 16px;
        background: var(--accent-gradient);
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(16, 163, 127, 0.3);
    `;
    
    retryBtn.onmouseover = () => {
        retryBtn.style.transform = 'scale(1.05)';
        retryBtn.style.boxShadow = '0 4px 12px rgba(16, 163, 127, 0.4)';
    };
    retryBtn.onmouseout = () => {
        retryBtn.style.transform = 'scale(1)';
        retryBtn.style.boxShadow = '0 2px 8px rgba(16, 163, 127, 0.3)';
    };
    
    retryBtn.onclick = () => {
        if (AppState.lastImageFile) {
            retryBtn.disabled = true;
            retryBtn.textContent = '重试中...';
            sendImageToServer(AppState.lastImageFile);
        }
    };
    
    errorDiv.appendChild(retryBtn);
}

// 移除消息
function removeMessageById(messageId) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        messageElement.remove();
    }
}

// Markdown转HTML（改进版，支持更多格式和更好的渲染）
function convertMarkdownToHtml(markdown) {
    if (!markdown) return '';
    
    let html = markdown;
    
    // 转义HTML特殊字符（在代码块之外）
    const escapeHtml = (text) => {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };
    
    // 代码块（先处理，避免被其他规则影响）
    html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
        const escaped = escapeHtml(code.trim());
        return `<pre class="code-block"><code>${escaped}</code></pre>`;
    });
    
    // 行内代码（避免匹配代码块内的内容）
    html = html.replace(/(?<!`)(?<!`)`([^`\n]+)`(?!`)/g, '<code class="inline-code">$1</code>');
    
    // 标题（按从大到小顺序处理）
    html = html.replace(/^###### (.*$)/gim, '<h6>$1</h6>');
    html = html.replace(/^##### (.*$)/gim, '<h5>$1</h5>');
    html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // 粗体（避免与代码冲突）
    html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_\n]+)__/g, '<strong>$1</strong>');
    
    // 斜体
    html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');
    html = html.replace(/(?<!_)_([^_\n]+)_(?!_)/g, '<em>$1</em>');
    
    // 删除线
    html = html.replace(/~~([^~\n]+)~~/g, '<del>$1</del>');
    
    // 无序列表和有序列表（改进处理）
    const lines = html.split('\n');
    let inUnorderedList = false;
    let inOrderedList = false;
    let unorderedItems = [];
    let orderedItems = [];
    let processedLines = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const unorderedMatch = line.match(/^[\s]*[-*+][\s]+(.+)$/);
        const orderedMatch = line.match(/^[\s]*(\d+)\.[\s]+(.+)$/);
        
        if (unorderedMatch) {
            if (inOrderedList && orderedItems.length > 0) {
                processedLines.push(`<ol>${orderedItems.join('')}</ol>`);
                orderedItems = [];
                inOrderedList = false;
            }
            if (!inUnorderedList) {
                if (unorderedItems.length > 0) {
                    processedLines.push(`<ul>${unorderedItems.join('')}</ul>`);
                    unorderedItems = [];
                }
                inUnorderedList = true;
            }
            unorderedItems.push(`<li>${unorderedMatch[1]}</li>`);
        } else if (orderedMatch) {
            if (inUnorderedList && unorderedItems.length > 0) {
                processedLines.push(`<ul>${unorderedItems.join('')}</ul>`);
                unorderedItems = [];
                inUnorderedList = false;
            }
            if (!inOrderedList) {
                if (orderedItems.length > 0) {
                    processedLines.push(`<ol>${orderedItems.join('')}</ol>`);
                    orderedItems = [];
                }
                inOrderedList = true;
            }
            orderedItems.push(`<li>${orderedMatch[2]}</li>`);
        } else {
            if (inUnorderedList && unorderedItems.length > 0) {
                processedLines.push(`<ul>${unorderedItems.join('')}</ul>`);
                unorderedItems = [];
                inUnorderedList = false;
            }
            if (inOrderedList && orderedItems.length > 0) {
                processedLines.push(`<ol>${orderedItems.join('')}</ol>`);
                orderedItems = [];
                inOrderedList = false;
            }
            if (line.trim()) {
                processedLines.push(line);
            }
        }
    }
    if (unorderedItems.length > 0) {
        processedLines.push(`<ul>${unorderedItems.join('')}</ul>`);
    }
    if (orderedItems.length > 0) {
        processedLines.push(`<ol>${orderedItems.join('')}</ol>`);
    }
    html = processedLines.join('\n');
    
    // 链接
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="markdown-link">$1</a>');
    
    // 水平分割线
    html = html.replace(/^---$/gim, '<hr>');
    html = html.replace(/^\*\*\*$/gim, '<hr>');
    
    // 换行处理
    html = html.replace(/\n\n+/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    
    // 包装段落（但保留已有标签）
    if (!html.match(/^<(h[1-6]|pre|ul|ol|div|hr|p)/)) {
        html = '<p>' + html + '</p>';
    }
    
    return html;
}

// 滚动到底部
function scrollToBottom() {
    setTimeout(() => {
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    }, 100);
}

// 显示/隐藏欢迎界面
function showWelcomeScreen() {
    elements.welcomeScreen.style.display = 'flex';
}

function hideWelcomeScreen() {
    elements.welcomeScreen.style.display = 'none';
}

function clearChatContainer() {
    elements.chatContainer.innerHTML = '';
    showWelcomeScreen();
}

// 更新状态指示器
function updateStatus(text) {
    elements.statusIndicator.textContent = text;
    if (text === '分析中...') {
        elements.statusIndicator.classList.add('processing');
    } else {
        elements.statusIndicator.classList.remove('processing');
    }
}

// 显示提示消息
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 加载对话历史
function loadChatHistory() {
    elements.chatHistory.innerHTML = '';
    AppState.chatHistory.forEach((chat, index) => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.textContent = `对话 ${index + 1}`;
        item.onclick = () => loadChat(index);
        elements.chatHistory.appendChild(item);
    });
}

// 加载对话
function loadChat(index) {
    // 保存当前对话
    if (AppState.currentChat.length > 0) {
        saveCurrentChat();
    }
    
    // 加载历史对话
    AppState.currentChat = AppState.chatHistory[index].messages || [];
    renderChat();
    hideWelcomeScreen();
    toggleSidebar();
}

// 保存当前对话
function saveCurrentChat() {
    if (AppState.currentChat.length === 0) return;
    
    const chatData = {
        timestamp: Date.now(),
        messages: AppState.currentChat
    };
    
    AppState.chatHistory.unshift(chatData);
    if (AppState.chatHistory.length > 50) {
        AppState.chatHistory = AppState.chatHistory.slice(0, 50);
    }
    
    localStorage.setItem('chatHistory', JSON.stringify(AppState.chatHistory));
    loadChatHistory();
}

// 渲染对话
function renderChat() {
    clearChatContainer();
    hideWelcomeScreen();
    
    AppState.currentChat.forEach(msg => {
        if (msg.type === 'user' && msg.content === 'image') {
            // 重新显示用户图片（需要从文件或URL）
            displayUserImage(msg.file);
        } else if (msg.type === 'assistant') {
            const messageDiv = createMessageElement('assistant');
            const content = document.createElement('div');
            content.className = 'markdown-content';
            content.innerHTML = convertMarkdownToHtml(msg.text);
            messageDiv.querySelector('.message-content').appendChild(content);
            elements.chatContainer.appendChild(messageDiv);
        }
    });
    
    scrollToBottom();
}

// 图标辅助函数
function getSunIcon() {
    return `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 3V1M10 19V17M17 10H19M1 10H3M15.657 4.343L16.778 3.222M3.222 16.778L4.343 15.657M15.657 15.657L16.778 16.778M3.222 3.222L4.343 4.343M14 10C14 12.2091 12.2091 14 10 14C7.79086 14 6 12.2091 6 10C6 7.79086 7.79086 6 10 6C12.2091 6 14 7.79086 14 10Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`;
}

function getMoonIcon() {
    return `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M17.293 13.293C16.3782 14.2078 15.2207 14.8481 13.9742 15.1418C12.7277 15.4355 11.4334 15.3754 10.22 14.9681C9.00658 14.5607 7.91518 13.8176 7.06282 12.8151C6.21047 11.8127 5.62547 10.5851 5.36786 9.26387C5.11025 7.9426 5.18851 6.57181 5.59545 5.28396C6.00238 3.9961 6.72263 2.83212 7.68396 1.90078C8.6453 0.969437 9.80928 0.249192 11.0971 0.842258C12.385 1.43532 13.5556 2.35719 14.5 3.5C15.5875 4.79218 16.2273 6.40039 16.3174 8.07078C16.4075 9.74117 15.9437 11.3983 14.9882 12.7772C14.0327 14.1561 12.6317 15.1881 11 15.707C10.3256 15.8938 9.62547 15.986 8.92212 15.9806C8.21877 15.9752 7.52062 15.8722 6.85 15.675L7.75 13.75L9.5 12.5L11.25 11.25L13 10L15.675 6.85C15.8722 7.52062 15.9752 8.21877 15.9806 8.92212C15.986 9.62547 15.8938 10.3256 15.707 11C15.1881 12.6317 14.1561 14.0327 12.7772 14.9882C11.3983 15.9437 9.74117 16.4075 8.07078 16.3174C6.40039 16.2273 4.79218 15.5875 3.5 14.5L5.28396 12.7161C6.57181 12.3092 7.9426 12.2309 9.26387 12.4885C10.5851 12.7461 11.8127 13.3311 12.8151 14.1835C13.8176 15.0358 14.5607 16.1272 14.9681 17.3406C15.3754 18.554 15.4355 19.8483 15.1418 21.0948C14.8481 22.3413 14.2078 23.4988 13.293 24.4136L17.293 20.4136V13.293Z" fill="currentColor"/>
    </svg>`;
}
