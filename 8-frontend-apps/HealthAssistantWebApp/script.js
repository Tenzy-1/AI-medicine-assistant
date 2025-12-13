document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chatContainer');
    const imageInput = document.getElementById('imageInput');
    const imageInputLabel = document.getElementById('imageInputLabel');
    const sendButton = document.getElementById('sendButton');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const removeImageBtn = document.getElementById('removeImageBtn');
    
    let selectedImage = null;
    let timerInterval = null;

    imageInput.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            selectedImage = file;

            const reader = new FileReader();
            reader.onload = function(event) {
                imagePreview.src = event.target.result;
                imagePreviewContainer.style.display = 'inline-block';
                sendButton.disabled = false;
            };
            reader.readAsDataURL(file);
        }
    });
    
    removeImageBtn.addEventListener('click', function() {
        imageInput.value = '';
        selectedImage = null;
        imagePreviewContainer.style.display = 'none';
        sendButton.disabled = true;
    });

    sendButton.addEventListener('click', function() {
        if (selectedImage) {
            sendImageToServer(selectedImage);
        }
    });
    

    function sendImageToServer(imageFile) {

        displayUserImage(imageFile);

        imageInput.value = '';
        selectedImage = null;
        imagePreviewContainer.style.display = 'none';
        sendButton.disabled = true;

        const loadingMessageId = displayLoadingMessage();

        const formData = new FormData();
        formData.append('image', imageFile);

        const xhr = new XMLHttpRequest();

        xhr.open('POST', 'http://101.32.126.91:80/analyze_medical_report', true);
        
        xhr.onload = function() {

            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }

            removeMessageById(loadingMessageId);
            
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    displayServerResponse(response);
                } catch (e) {
                    displayErrorMessage('解析服务器响应时出错: ' + e.message);
                }
            } else {
                try {
                    const errorResponse = JSON.parse(xhr.responseText);
                    displayErrorMessage(`服务器错误: ${xhr.status} - ${errorResponse.error}`);
                } catch (e) {
                    displayErrorMessage(`服务器错误: ${xhr.status} - ${xhr.responseText}`);
                }
            }
        };
        
        xhr.onerror = function() {

            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }

            removeMessageById(loadingMessageId);
            displayErrorMessage('网络错误，请检查连接。如果您使用的是本地服务器，请确保服务器正在运行并且您是通过服务器访问此页面的。');
        };
        
        xhr.ontimeout = function() {

            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
            

            removeMessageById(loadingMessageId);
            displayErrorMessage('请求超时，请稍后重试。');
        };
        

        xhr.timeout = 600000; // 10 minutes (600000ms) - reasonable timeout for medical image analysis
        
        xhr.send(formData);
    }

    function displayUserImage(imageFile) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message image-message';
        
        const img = document.createElement('img');
        img.src = URL.createObjectURL(imageFile);
        img.alt = 'User uploaded image';

        img.style.maxWidth = '200px';
        img.style.maxHeight = '200px';
        
        img.onload = function() {
            URL.revokeObjectURL(img.src);
        };
        
        messageDiv.appendChild(img);
        chatContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    function displayLoadingMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message server-message loading-message';
        messageDiv.id = 'loading-' + Date.now(); 
        
        const loadingDots = document.createElement('div');
        loadingDots.className = 'loading-dots';
        loadingDots.innerHTML = '<span></span><span></span><span></span>';
        
        const timerDiv = document.createElement('div');
        timerDiv.className = 'timer';
        timerDiv.textContent = '0秒';
        
        messageDiv.appendChild(loadingDots);
        messageDiv.appendChild(timerDiv);
        chatContainer.appendChild(messageDiv);
        scrollToBottom();

        let seconds = 0;
        timerInterval = setInterval(function() {
            seconds++;
            timerDiv.textContent = `${seconds}秒`;
        }, 1000);
        
        return messageDiv.id;
    }
    
    function removeMessageById(messageId) {
        const messageElement = document.getElementById(messageId);
        if (messageElement) {
            messageElement.remove();
        }
    }
    
    function convertMarkdownToHtml(markdown) {
        let html = markdown.replace(/^###### (.*$)/gm, '<h6>$1</h6>')
                           .replace(/^##### (.*$)/gm, '<h5>$1</h5>')
                           .replace(/^#### (.*$)/gm, '<h4>$1</h4>')
                           .replace(/^### (.*$)/gm, '<h3>$1</h3>')
                           .replace(/^## (.*$)/gm, '<h2>$1</h2>')
                           .replace(/^# (.*$)/gm, '<h1>$1</h1>');
        

        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                   .replace(/__(.*?)__/g, '<strong>$1</strong>');
        

        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
                   .replace(/_(.*?)_/g, '<em>$1</em>');
        

        html = html.replace(/^[\s]*[-\*][\s]+(.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
        

        html = html.replace(/^[\s]*\d+\.[\s]+(.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/gs, '<ol>$1</ol>');
        
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }
    

    function displayServerResponse(response) {

        const analysisMessage = document.createElement('div');
        analysisMessage.className = 'message server-message';
        
        const analysisSection = document.createElement('div');
        analysisSection.className = 'analysis-section';
        
        const analysisTitle = document.createElement('h3');
        analysisTitle.textContent = '检测结果分析';
        
        const analysisContent = document.createElement('div');
        analysisContent.className = 'markdown-content';
        analysisContent.innerHTML = convertMarkdownToHtml(response.analysis_result);
        
        analysisSection.appendChild(analysisTitle);
        analysisSection.appendChild(analysisContent);
        analysisMessage.appendChild(analysisSection);
        
        chatContainer.appendChild(analysisMessage);
        scrollToBottom();

        const recommendationMessage = document.createElement('div');
        recommendationMessage.className = 'message server-message';
        
        const recommendationSection = document.createElement('div');
        recommendationSection.className = 'recommendation-section';
        
        const recommendationTitle = document.createElement('h3');
        recommendationTitle.textContent = '健康建议';
        
        const recommendationContent = document.createElement('div');
        recommendationContent.className = 'markdown-content';
        recommendationContent.innerHTML = convertMarkdownToHtml(response.health_recommendations);
        
        recommendationSection.appendChild(recommendationTitle);
        recommendationSection.appendChild(recommendationContent);
        recommendationMessage.appendChild(recommendationSection);
        
        chatContainer.appendChild(recommendationMessage);
        scrollToBottom();
    }
    

    function displayErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message server-message';
        errorDiv.textContent = `错误: ${message}`;
        chatContainer.appendChild(errorDiv);
        scrollToBottom();
    }
    

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});