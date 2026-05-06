// API utility for SchoolCat Guardian

const API = {
    baseUrl: '',

    async request(method, url, data, options = {}) {
        const config = {
            method,
            headers: {},
        };

        if (options.upload && data) {
            // FormData for file upload
            config.body = data;
        } else if (data) {
            config.headers['Content-Type'] = 'application/json';
            config.body = JSON.stringify(data);
        }

        const response = await fetch(this.baseUrl + url, config);

        if (response.status === 401) {
            // Redirect to login
            window.location.href = '/login.html';
            throw new Error('请先登录');
        }
        if (response.status === 403) {
            alert('需要管理员权限');
            throw new Error('权限不足');
        }

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || '请求失败');
        }
        return result;
    },

    get(url, params = {}) {
        const query = new URLSearchParams(params).toString();
        const fullUrl = query ? url + '?' + query : url;
        return this.request('GET', fullUrl);
    },

    post(url, data) {
        return this.request('POST', url, data);
    },

    put(url, data) {
        return this.request('PUT', url, data);
    },

    del(url) {
        return this.request('DELETE', url);
    },

    upload(method, url, formData) {
        return this.request(method, url, formData, { upload: true });
    },

    // Auth helpers
    async login(username, password) {
        const result = await this.post('/api/auth/login', { username, password });
        return result;
    },

    async logout() {
        return this.post('/api/auth/logout');
    },

    async getCurrentUser() {
        return this.get('/api/auth/me');
    },

    // Cat helpers
    async getCats(params = {}) {
        return this.get('/api/cats', params);
    },

    async getCat(id) {
        return this.get('/api/cats/' + id);
    },

    async createCat(formData) {
        return this.upload('POST', '/api/cats', formData);
    },

    async updateCat(id, formData) {
        return this.upload('PUT', '/api/cats/' + id, formData);
    },

    async deleteCat(id) {
        return this.del('/api/cats/' + id);
    },

    // Check-in helpers
    async getCheckins(params = {}) {
        return this.get('/api/checkins', params);
    },

    async createCheckin(formData) {
        return this.upload('POST', '/api/checkins', formData);
    },

    async approveCheckin(id) {
        return this.put('/api/checkins/' + id, { status: 'approved' });
    },

    async rejectCheckin(id) {
        return this.put('/api/checkins/' + id, { status: 'rejected' });
    },

    async deleteCheckin(id) {
        return this.del('/api/checkins/' + id);
    },

    // Stats
    async getStats() {
        return this.get('/api/stats');
    },

    async seedData() {
        return this.post('/api/seed');
    },
};
