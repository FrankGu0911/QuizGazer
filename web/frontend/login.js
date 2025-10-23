const { createApp, ref, onMounted } = Vue;
const { ElMessage } = ElementPlus;

const API_BASE_URL = window.location.origin;

const app = createApp({
    setup() {
        const loginFormRef = ref(null);
        const loginForm = ref({
            username: '',
            password: ''
        });
        const loading = ref(false);
        const isDarkMode = ref(false);

        const rules = {
            username: [
                { required: true, message: '请输入用户名', trigger: 'blur' }
            ],
            password: [
                { required: true, message: '请输入密码', trigger: 'blur' },
                { min: 6, message: '密码长度至少6位', trigger: 'blur' }
            ]
        };

        // 主题管理
        const detectSystemDarkMode = () => {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        };

        const updateTheme = () => {
            const themeMode = localStorage.getItem('themeMode') || 'system';
            let shouldBeDark = false;

            if (themeMode === 'dark') {
                shouldBeDark = true;
            } else if (themeMode === 'light') {
                shouldBeDark = false;
            } else {
                shouldBeDark = detectSystemDarkMode();
            }

            isDarkMode.value = shouldBeDark;

            if (shouldBeDark) {
                document.documentElement.classList.add('dark-theme');
                document.documentElement.classList.remove('light-theme');
            } else {
                document.documentElement.classList.add('light-theme');
                document.documentElement.classList.remove('dark-theme');
            }
        };

        const toggleTheme = () => {
            const currentMode = localStorage.getItem('themeMode') || 'system';
            const newMode = currentMode === 'dark' ? 'light' : 'dark';
            localStorage.setItem('themeMode', newMode);
            updateTheme();
        };

        // 登录处理
        const handleLogin = async () => {
            if (!loginFormRef.value) return;

            try {
                await loginFormRef.value.validate();
            } catch (error) {
                return;
            }

            loading.value = true;

            try {
                const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: loginForm.value.username,
                        password: loginForm.value.password
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || '登录失败');
                }

                const data = await response.json();

                // 保存token
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('username', data.username);

                ElMessage.success('登录成功');

                // 跳转到主页
                setTimeout(() => {
                    window.location.href = '/';
                }, 500);

            } catch (error) {
                console.error('登录失败:', error);
                ElMessage.error(error.message || '登录失败，请检查用户名和密码');
            } finally {
                loading.value = false;
            }
        };

        // 检查是否已登录
        const checkAuth = () => {
            const token = localStorage.getItem('access_token');
            if (token) {
                // 已登录，跳转到主页
                window.location.href = '/';
            }
        };

        onMounted(() => {
            updateTheme();
            checkAuth();
        });

        return {
            loginFormRef,
            loginForm,
            rules,
            loading,
            isDarkMode,
            handleLogin,
            toggleTheme
        };
    }
});

app.use(ElementPlus).mount('#app');
