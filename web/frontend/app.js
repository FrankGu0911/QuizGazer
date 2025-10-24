const { createApp, ref, computed, onMounted } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

// 自动检测API基础URL
const API_BASE_URL = window.location.origin;

const app = createApp({
    setup() {
        const records = ref([]);
        const stats = ref(null);
        const loading = ref(false);
        const currentPage = ref(1);
        const pageSize = ref(20);
        const totalCount = ref(0);
        const searchQuery = ref('');
        const selectedRecords = ref([]);
        const exportDialogVisible = ref(false);
        const exportFormat = ref('json');
        const exporting = ref(false);
        const wsConnected = ref(false);
        const userList = ref([]);
        const selectedUser = ref('');
        let websocket = null;

        // 主题相关
        const themeMode = ref(localStorage.getItem('themeMode') || 'system');
        const isDarkMode = ref(false);

        const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value));
        const isAllSelected = computed(() =>
            records.value.length > 0 && selectedRecords.value.length === records.value.length
        );

        // 获取认证头
        const getAuthHeaders = () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
                return {};
            }
            return {
                'Authorization': `Bearer ${token}`
            };
        };

        // 检查认证状态
        const checkAuth = () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
                // 未登录，跳转到登录页
                window.location.href = '/login';
                return false;
            }
            return true;
        };

        // 处理认证错误
        const handleAuthError = (error) => {
            if (error.message.includes('401') || error.message.includes('Unauthorized')) {
                ElMessage.error('登录已过期，请重新登录');
                localStorage.removeItem('access_token');
                localStorage.removeItem('username');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
                return true;
            }
            return false;
        };

        // 登出
        const logout = async () => {
            try {
                await ElMessageBox.confirm('确定要退出登录吗？', '确认退出', {
                    type: 'warning'
                });

                const token = localStorage.getItem('access_token');
                if (token) {
                    try {
                        await fetch(`${API_BASE_URL}/api/auth/logout`, {
                            method: 'POST',
                            headers: getAuthHeaders()
                        });
                    } catch (error) {
                        console.error('登出请求失败:', error);
                    }
                }

                localStorage.removeItem('access_token');
                localStorage.removeItem('username');
                ElMessage.success('已退出登录');

                setTimeout(() => {
                    window.location.href = '/login';
                }, 500);
            } catch (error) {
                // 用户取消
            }
        };

        // 加载用户列表
        const loadUsers = async () => {
            if (!checkAuth()) return;

            try {
                const response = await fetch(`${API_BASE_URL}/api/quiz/users`, {
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                userList.value = data.users || [];
            } catch (error) {
                console.error('加载用户列表失败:', error);
                handleAuthError(error);
            }
        };

        // 加载记录
        const loadRecords = async () => {
            if (!checkAuth()) return;

            loading.value = true;
            try {
                const params = new URLSearchParams({
                    skip: (currentPage.value - 1) * pageSize.value,
                    limit: pageSize.value
                });

                if (searchQuery.value) {
                    params.append('search', searchQuery.value);
                }

                if (selectedUser.value) {
                    params.append('user_id', selectedUser.value);
                }

                const response = await fetch(`${API_BASE_URL}/api/quiz/records?${params}`, {
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();

                records.value = data.records || [];
                totalCount.value = data.total || 0;
            } catch (error) {
                console.error('加载记录失败:', error);
                if (!handleAuthError(error)) {
                    ElMessage.error('加载记录失败: ' + error.message);
                }
            } finally {
                loading.value = false;
            }
        };

        // 加载统计
        const loadStats = async () => {
            if (!checkAuth()) return;

            try {
                const response = await fetch(`${API_BASE_URL}/api/stats`, {
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                stats.value = await response.json();
            } catch (error) {
                console.error('加载统计失败:', error);
                handleAuthError(error);
            }
        };

        // 刷新数据
        const refreshData = () => {
            loadRecords();
            loadStats();
        };

        // 搜索
        const handleSearch = () => {
            currentPage.value = 1;
            loadRecords();
        };

        // 用户筛选
        const handleUserFilter = () => {
            currentPage.value = 1;
            loadRecords();
        };

        // 翻页
        const handlePageChange = () => {
            loadRecords();
        };

        // 切换选择
        const toggleSelection = (recordId) => {
            const index = selectedRecords.value.indexOf(recordId);
            if (index > -1) {
                selectedRecords.value.splice(index, 1);
            } else {
                selectedRecords.value.push(recordId);
            }
        };

        // 全选/取消全选
        const selectAllRecords = () => {
            if (isAllSelected.value) {
                selectedRecords.value = [];
            } else {
                selectedRecords.value = records.value.map(r => r.id);
            }
        };

        // 删除记录
        const deleteRecord = async (recordId) => {
            try {
                await ElMessageBox.confirm('确定要删除这条记录吗？', '确认删除', {
                    type: 'warning'
                });

                const response = await fetch(`${API_BASE_URL}/api/quiz/record/${recordId}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                ElMessage.success('删除成功');
                selectedRecords.value = selectedRecords.value.filter(id => id !== recordId);
                refreshData();
            } catch (error) {
                if (error !== 'cancel') {
                    if (!handleAuthError(error)) {
                        ElMessage.error('删除失败');
                    }
                }
            }
        };

        // 显示导出对话框
        const showExportDialog = () => {
            if (selectedRecords.value.length === 0) {
                ElMessage.warning('请先选择要导出的记录');
                return;
            }
            exportDialogVisible.value = true;
        };

        // 确认导出
        const confirmExport = async () => {
            exporting.value = true;
            try {
                const selectedData = records.value.filter(r =>
                    selectedRecords.value.includes(r.id)
                );

                let content, filename, mimeType;

                if (exportFormat.value === 'json') {
                    // 移除模型信息
                    const exportData = selectedData.map(r => ({
                        id: r.id,
                        timestamp: r.timestamp,
                        question_text: r.question_text,
                        answer_text: r.answer_text,
                        total_time: r.total_time,
                        image_path: r.image_path
                    }));
                    content = JSON.stringify(exportData, null, 2);
                    filename = `quiz_records_${Date.now()}.json`;
                    mimeType = 'application/json';
                } else if (exportFormat.value === 'csv') {
                    // 简单的CSV导出（不包含模型信息）
                    const headers = ['ID', '时间', '题目', '答案', '处理时间'];
                    const rows = selectedData.map(r => [
                        r.id,
                        formatDate(r.timestamp),
                        `"${r.question_text.replace(/"/g, '""')}"`,
                        `"${r.answer_text.replace(/"/g, '""')}"`,
                        r.total_time?.toFixed(2) || ''
                    ]);

                    content = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
                    filename = `quiz_records_${Date.now()}.csv`;
                    mimeType = 'text/csv;charset=utf-8;';
                }

                // 下载文件
                const blob = new Blob(['\ufeff' + content], { type: mimeType });
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);

                ElMessage.success(`成功导出 ${selectedRecords.value.length} 条记录`);
                exportDialogVisible.value = false;
            } catch (error) {
                console.error('导出失败:', error);
                ElMessage.error('导出失败');
            } finally {
                exporting.value = false;
            }
        };

        // 格式化日期
        const formatDate = (dateStr) => {
            // 如果时间字符串没有时区信息，添加 'Z' 表示 UTC 时间
            let isoString = dateStr;
            if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('T')) {
                // 格式如 "2025-10-24 02:15:31.134845"，需要转换为 ISO 格式
                isoString = dateStr.replace(' ', 'T') + 'Z';
            } else if (dateStr.includes('T') && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
                // 格式如 "2025-10-24T02:15:31.134845"，添加 Z
                isoString = dateStr + 'Z';
            }
            
            const date = new Date(isoString);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        };

        // 获取图片URL
        const getImageUrl = (imagePath) => {
            return `${API_BASE_URL}/${imagePath}`;
        };

        // WebSocket连接
        const connectWebSocket = () => {
            try {
                const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws';
                websocket = new WebSocket(wsUrl);

                websocket.onopen = () => {
                    console.log('WebSocket连接成功');
                    wsConnected.value = true;
                };

                websocket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        handleWebSocketMessage(message);
                    } catch (error) {
                        console.error('WebSocket消息解析失败:', error);
                    }
                };

                websocket.onclose = () => {
                    console.log('WebSocket连接关闭');
                    wsConnected.value = false;
                    // 5秒后重连
                    setTimeout(connectWebSocket, 5000);
                };

                websocket.onerror = (error) => {
                    console.error('WebSocket错误:', error);
                    wsConnected.value = false;
                };
            } catch (error) {
                console.error('WebSocket连接失败:', error);
            }
        };

        // 处理WebSocket消息
        const handleWebSocketMessage = (message) => {
            console.log('收到WebSocket消息:', message);

            if (message.type === 'new_record') {
                // 新记录到达，添加到列表顶部
                const newRecord = message.data;

                // 如果在第一页且没有搜索，则添加到列表
                if (currentPage.value === 1 && !searchQuery.value) {
                    records.value.unshift(newRecord);
                    totalCount.value += 1;

                    // 限制显示数量
                    if (records.value.length > pageSize.value) {
                        records.value = records.value.slice(0, pageSize.value);
                    }

                    ElMessage({
                        message: '收到新的答题记录',
                        type: 'success',
                        duration: 3000
                    });
                } else {
                    // 显示提示
                    ElMessage({
                        message: '有新的答题记录，刷新页面查看',
                        type: 'info',
                        duration: 5000
                    });
                }
            }
        };

        // 发送心跳
        const sendHeartbeat = () => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({ type: 'ping' }));
            }
        };

        // 主题管理
        const detectSystemDarkMode = () => {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        };

        const updateTheme = () => {
            let shouldBeDark = false;

            if (themeMode.value === 'dark') {
                shouldBeDark = true;
            } else if (themeMode.value === 'light') {
                shouldBeDark = false;
            } else { // system
                shouldBeDark = detectSystemDarkMode();
            }

            isDarkMode.value = shouldBeDark;

            // 应用主题到document
            if (shouldBeDark) {
                document.documentElement.classList.add('dark-theme');
                document.documentElement.classList.remove('light-theme');
            } else {
                document.documentElement.classList.add('light-theme');
                document.documentElement.classList.remove('dark-theme');
            }
        };

        const setThemeMode = (mode) => {
            themeMode.value = mode;
            localStorage.setItem('themeMode', mode);
            updateTheme();
        };

        // 监听系统主题变化
        const setupSystemThemeListener = () => {
            if (window.matchMedia) {
                const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
                mediaQuery.addListener(() => {
                    if (themeMode.value === 'system') {
                        updateTheme();
                    }
                });
            }
        };

        onMounted(() => {
            // 检查认证状态
            if (!checkAuth()) {
                return;
            }

            // 初始化主题
            updateTheme();
            setupSystemThemeListener();

            loadUsers();
            refreshData();
            connectWebSocket();

            // 每30秒发送心跳
            setInterval(sendHeartbeat, 30000);
        });

        // 获取当前用户名
        const currentUsername = ref(localStorage.getItem('username') || '用户');

        // 跳转到 ChromaDB 查询页面
        const goToChromaDB = () => {
            window.location.href = '/chromadb';
        };

        return {
            records,
            stats,
            loading,
            currentPage,
            pageSize,
            totalCount,
            totalPages,
            searchQuery,
            selectedRecords,
            isAllSelected,
            exportDialogVisible,
            exportFormat,
            exporting,
            refreshData,
            handleSearch,
            handlePageChange,
            toggleSelection,
            selectAllRecords,
            deleteRecord,
            showExportDialog,
            confirmExport,
            formatDate,
            getImageUrl,
            wsConnected,
            // 用户筛选
            userList,
            selectedUser,
            handleUserFilter,
            // 主题相关
            themeMode,
            isDarkMode,
            setThemeMode,
            // 认证相关
            currentUsername,
            logout,
            goToChromaDB
        };
    }
});

app.use(ElementPlus).mount('#app');
