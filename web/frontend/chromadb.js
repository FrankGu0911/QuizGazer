const { createApp, ref, computed, onMounted } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

const API_BASE_URL = window.location.origin;

const app = createApp({
    setup() {
        const collections = ref([]);
        const selectedCollection = ref('');
        const queryText = ref('');
        const nResults = ref(10);
        const results = ref([]);
        const loading = ref(false);
        const querying = ref(false);
        const loadingSample = ref(false);
        const showingSample = ref(false);
        const currentUsername = ref(localStorage.getItem('username') || '用户');

        const currentCollectionInfo = computed(() => {
            if (!selectedCollection.value) return null;
            return collections.value.find(c => c.name === selectedCollection.value);
        });

        // 获取认证头
        const getAuthHeaders = () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
                return {};
            }
            return {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            };
        };

        // 检查认证状态
        const checkAuth = () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
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

        // 检查配置
        const checkConfig = async () => {
            if (!checkAuth()) return;

            try {
                const response = await fetch(`${API_BASE_URL}/api/chromadb/config`, {
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                
                let message = `配置文件: ${data.config_file}\n`;
                if (data.working_directory) {
                    message += `工作目录: ${data.working_directory}\n\n`;
                }
                
                if (data.error) {
                    message += `错误: ${data.error}`;
                } else {
                    if (data.chromadb) {
                        message += `【ChromaDB 配置】\n`;
                        message += `连接类型: ${data.chromadb.connection_type}\n`;
                        if (data.chromadb.connection_type === 'remote') {
                            message += `服务器: ${data.chromadb.host}:${data.chromadb.port}\n`;
                            message += `SSL: ${data.chromadb.ssl_enabled}\n`;
                        } else {
                            message += `路径: ${data.chromadb.path}\n`;
                        }
                    }
                    
                    if (data.embedding_api) {
                        message += `\n【Embedding API】\n`;
                        if (data.embedding_api.configured) {
                            message += `端点: ${data.embedding_api.endpoint}\n`;
                            message += `模型: ${data.embedding_api.model}\n`;
                            message += `状态: ✅ 已配置`;
                        } else {
                            message += `状态: ❌ 未配置`;
                        }
                    }
                }
                
                ElMessageBox.alert(message, 'ChromaDB 配置信息', {
                    confirmButtonText: '确定'
                });
            } catch (error) {
                console.error('检查配置失败:', error);
                if (!handleAuthError(error)) {
                    ElMessage.error('检查配置失败: ' + error.message);
                }
            }
        };

        // 加载集合列表
        const loadCollections = async () => {
            if (!checkAuth()) return;

            loading.value = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/chromadb/collections`, {
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || `HTTP ${response.status}`);
                }

                const data = await response.json();
                collections.value = data.collections || [];
                
                if (collections.value.length > 0) {
                    ElMessage.success(`加载了 ${collections.value.length} 个集合`);
                } else {
                    ElMessage.warning('未找到任何集合');
                }
            } catch (error) {
                console.error('加载集合失败:', error);
                if (!handleAuthError(error)) {
                    ElMessage.error('加载集合失败: ' + error.message);
                }
            } finally {
                loading.value = false;
            }
        };

        // 集合变化时
        const onCollectionChange = () => {
            results.value = [];
            showingSample.value = false;
            queryText.value = '';
        };

        // 执行查询
        const executeQuery = async () => {
            if (!selectedCollection.value || !queryText.value) {
                ElMessage.warning('请选择集合并输入查询关键词');
                return;
            }

            querying.value = true;
            showingSample.value = false;
            try {
                const response = await fetch(`${API_BASE_URL}/api/chromadb/query`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        collection_name: selectedCollection.value,
                        query_text: queryText.value,
                        n_results: nResults.value
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP ${response.status}`);
                }

                const data = await response.json();
                results.value = data.results || [];
                
                ElMessage.success(`找到 ${results.value.length} 条结果`);
            } catch (error) {
                console.error('查询失败:', error);
                if (!handleAuthError(error)) {
                    ElMessage.error('查询失败: ' + error.message);
                }
            } finally {
                querying.value = false;
            }
        };

        // 加载示例数据
        const loadSample = async () => {
            if (!selectedCollection.value) {
                ElMessage.warning('请先选择集合');
                return;
            }

            loadingSample.value = true;
            showingSample.value = true;
            try {
                const response = await fetch(
                    `${API_BASE_URL}/api/chromadb/collection/${selectedCollection.value}/sample?limit=5`,
                    {
                        headers: getAuthHeaders()
                    }
                );

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP ${response.status}`);
                }

                const data = await response.json();
                results.value = data.samples || [];
                
                ElMessage.success(`加载了 ${results.value.length} 条示例数据`);
            } catch (error) {
                console.error('加载示例失败:', error);
                if (!handleAuthError(error)) {
                    ElMessage.error('加载示例失败: ' + error.message);
                }
            } finally {
                loadingSample.value = false;
            }
        };

        // 返回历史记录页面
        const goBack = () => {
            window.location.href = '/';
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

        onMounted(() => {
            if (!checkAuth()) return;
            loadCollections();
        });

        return {
            collections,
            selectedCollection,
            queryText,
            nResults,
            results,
            loading,
            querying,
            loadingSample,
            showingSample,
            currentCollectionInfo,
            currentUsername,
            checkConfig,
            loadCollections,
            onCollectionChange,
            executeQuery,
            loadSample,
            goBack,
            logout
        };
    }
});

app.use(ElementPlus).mount('#app');
