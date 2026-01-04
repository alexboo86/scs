/**
 * JavaScript код для встраивания Secure Content Viewer на Tilda
 * 
 * ИНСТРУКЦИЯ:
 * 1. Замените YOUR_EXTERNAL_IP на ваш внешний IP адрес
 * 2. Замените DOCUMENT_TOKEN на токен документа из админ-панели
 * 3. Вставьте этот код в HTML блок Tilda
 */

(function() {
    'use strict';
    
    // ========== НАСТРОЙКИ ==========
    const CONFIG = {
        // Внешний IP адрес сервера
        SERVER_URL: 'http://185.88.159.33:8000',
        
        // Токен документа (получите из админ-панели)
        DOCUMENT_TOKEN: 'q6hl9470ZvfUoNmx5fSJ_7yBaSqWwHoMiLoVNVk1LOo',
        
        // Email пользователя (опционально, для водяных знаков)
        // Можно получить из URL параметров или из переменных Tilda
        USER_EMAIL: null, // Например: 'user@example.com' или получить из window.location.search
        
        // Размеры iframe
        WIDTH: '100%',
        HEIGHT: '800px',
        MIN_HEIGHT: '600px'
    };
    
    // ========== ПОЛУЧЕНИЕ EMAIL ИЗ URL ==========
    // Если Tilda передает email через URL параметр ?email=user@example.com
    function getUserEmailFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('email') || null;
    }
    
    // ========== ПОЛУЧЕНИЕ EMAIL ИЗ ПЕРЕМЕННЫХ TILDA ==========
    // Если у вас есть доступ к данным пользователя в Tilda
    function getUserEmailFromTilda() {
        // Примеры способов получения email из Tilda:
        // return window.TildaUserEmail || null;
        // return localStorage.getItem('user_email') || null;
        // return sessionStorage.getItem('user_email') || null;
        return null;
    }
    
    // ========== СОЗДАНИЕ IFRAME ==========
    function createViewerIframe() {
        // Получаем email пользователя
        const userEmail = CONFIG.USER_EMAIL || getUserEmailFromURL() || getUserEmailFromTilda();
        
        // Формируем URL для embed
        let embedUrl = `${CONFIG.SERVER_URL}/api/viewer/embed?document_token=${encodeURIComponent(CONFIG.DOCUMENT_TOKEN)}`;
        if (userEmail) {
            embedUrl += `&user_email=${encodeURIComponent(userEmail)}`;
        }
        
        // Создаем контейнер для viewer
        const container = document.createElement('div');
        container.id = 'secure-content-viewer-container';
        container.style.cssText = `
            width: ${CONFIG.WIDTH};
            height: ${CONFIG.HEIGHT};
            min-height: ${CONFIG.MIN_HEIGHT};
            position: relative;
            margin: 0;
            padding: 0;
            background: transparent;
            border: none;
        `;
        
        // Создаем элемент загрузки
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'viewer-loading';
        loadingDiv.style.cssText = `
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 18px;
            color: #666;
        `;
        loadingDiv.textContent = 'Загрузка документа...';
        container.appendChild(loadingDiv);
        
        // Создаем iframe
        const iframe = document.createElement('iframe');
        iframe.id = 'secure-content-viewer-iframe';
        iframe.src = embedUrl;
        iframe.width = CONFIG.WIDTH;
        iframe.height = CONFIG.HEIGHT;
        iframe.frameBorder = '0';
        iframe.allowFullscreen = true;
        iframe.style.cssText = `
            border: none;
            width: 100%;
            height: 100%;
            min-height: ${CONFIG.MIN_HEIGHT};
            display: none;
            margin: 0;
            padding: 0;
            background: transparent;
        `;
        iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-popups allow-forms');
        
        // Обработчики событий iframe
        iframe.onload = function() {
            loadingDiv.style.display = 'none';
            iframe.style.display = 'block';
            console.log('[Secure Content Viewer] Document loaded successfully');
        };
        
        iframe.onerror = function() {
            loadingDiv.textContent = 'Ошибка загрузки документа. Проверьте настройки.';
            loadingDiv.style.color = '#d32f2f';
            console.error('[Secure Content Viewer] Failed to load document');
        };
        
        container.appendChild(iframe);
        
        return container;
    }
    
    // ========== ИНИЦИАЛИЗАЦИЯ ==========
    function init() {
        // Ждем загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                initializeViewer();
            });
        } else {
            initializeViewer();
        }
    }
    
    function initializeViewer() {
        // Ищем контейнер для viewer (если уже есть на странице)
        let container = document.getElementById('secure-content-viewer-container');
        
        if (!container) {
            // Создаем новый контейнер
            container = createViewerIframe();
            
            // Вставляем в текущий элемент (если код выполняется внутри HTML блока)
            // Или в body, если выполняется в глобальном контексте
            const targetElement = document.currentScript?.parentElement || document.body;
            targetElement.appendChild(container);
        } else {
            // Если контейнер уже есть, обновляем iframe
            const iframe = container.querySelector('#secure-content-viewer-iframe');
            if (iframe) {
                const userEmail = CONFIG.USER_EMAIL || getUserEmailFromURL() || getUserEmailFromTilda();
                let embedUrl = `${CONFIG.SERVER_URL}/api/viewer/embed?document_token=${encodeURIComponent(CONFIG.DOCUMENT_TOKEN)}`;
                if (userEmail) {
                    embedUrl += `&user_email=${encodeURIComponent(userEmail)}`;
                }
                iframe.src = embedUrl;
            }
        }
        
        console.log('[Secure Content Viewer] Initialized');
    }
    
    // Запускаем инициализацию
    init();
})();
