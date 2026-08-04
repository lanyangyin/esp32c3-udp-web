// ============================================================
// 全局配置
// ============================================================
let baseUrl = '';

function getBaseUrl() {
    return baseUrl;
}

function setBaseUrl(url) {
    url = url.trim();
    if (!/^https?:\/\//i.test(url)) {
        url = 'http://' + url;
    }
    baseUrl = url.replace(/\/+$/, '');
    localStorage.setItem('esp32_ip', baseUrl);
    document.getElementById('conn_status').textContent = '已连接 ' + baseUrl;
    document.getElementById('conn_status').className = 'status online';
}

function loadSavedIp() {
    const saved = localStorage.getItem('esp32_ip');
    if (saved) {
        document.getElementById('device_ip').value = saved.replace(/^https?:\/\//, '');
        setBaseUrl(saved);
    } else {
        connectDevice();
    }
}

function connectDevice() {
    const ip = document.getElementById('device_ip').value;
    setBaseUrl(ip);
}

// ============================================================
// 通用 API 调用辅助
// ============================================================
function apiFetch(endpoint, options) {
    const url = getBaseUrl() + endpoint;
    return fetch(url, options);
}

function showResult(containerId, text) {
    const el = document.getElementById(containerId);
    if (el) el.textContent = text;
}

// ============================================================
// 主页状态刷新函数（多处使用）
// ============================================================
function fetchApStatus() {
    apiFetch('/api/get_ap_status')
        .then(res => res.json())
        .then(data => {
            document.getElementById('ap_ssid').textContent = data.ssid || '-';
            document.getElementById('ap_ip').textContent = data.ip || '-';
        })
        .catch(() => {});
}
function fetchStaStatus() {
    apiFetch('/api/get_sta_status')
        .then(res => res.json())
        .then(data => {
            document.getElementById('sta_ssid').textContent = data.ssid || '-';
            document.getElementById('sta_ip').textContent = data.ip || '-';
            document.getElementById('sta_connected').textContent = data.connected ? '已连接' : '未连接';
        })
        .catch(() => {});
}
function fetchStaTimeout() {
    apiFetch('/api/get_sta_timeout')
        .then(res => res.json())
        .then(data => { document.getElementById('sta_timeout').textContent = data.value || '-'; })
        .catch(() => {});
}
function fetchUdpRecvPort() {
    apiFetch('/api/get_udp_recv_port')
        .then(res => res.json())
        .then(data => { document.getElementById('udp_recv_port').textContent = data.value || '-'; })
        .catch(() => {});
}
function fetchUdpBroadcastPort() {
    apiFetch('/api/get_udp_broadcast_port')
        .then(res => res.json())
        .then(data => { document.getElementById('udp_broadcast_port').textContent = data.value || '-'; })
        .catch(() => {});
}
function fetchPollInterval() {
    apiFetch('/api/get_udp_poll_interval')
        .then(res => res.json())
        .then(data => { document.getElementById('poll_interval').textContent = data.interval || '-'; })
        .catch(() => {});
}
function fetchLedPin() {
    apiFetch('/api/get_led_pin')
        .then(res => res.json())
        .then(data => { document.getElementById('led_pin').textContent = data.pin || '-'; })
        .catch(() => {});
}
function fetchLedStatus() {
    apiFetch('/api/get_led_status')
        .then(res => res.json())
        .then(data => { document.getElementById('led_status').textContent = data.status || '-'; })
        .catch(() => {});
}
function fetchMemory() {
    apiFetch('/api/memory')
        .then(res => res.json())
        .then(data => {
            var used = data.used || 0;
            var total = data.total || 1;
            var percent = (used/total*100).toFixed(1);
            document.getElementById('memory_usage').textContent = used + '/' + total + ' (' + percent + '%)';
        })
        .catch(() => {});
}
function fetchSelfMac() {
    apiFetch('/api/get_self_mac')
        .then(res => res.json())
        .then(data => {
            document.getElementById('self_mac').textContent = data.mac || '-';
        })
        .catch(() => {});
}
function fetchAllStatus() {
    fetchApStatus();
    fetchStaStatus();
    fetchStaTimeout();
    fetchUdpRecvPort();
    fetchUdpBroadcastPort();
    fetchPollInterval();
    fetchLedPin();
    fetchLedStatus();
    fetchMemory();
    fetchSelfMac();
}

function showConnectedMacs() {
    apiFetch('/api/get_macs')
        .then(res => res.text())
        .then(data => { document.getElementById('connectedMacs').textContent = data; })
        .catch(err => { document.getElementById('connectedMacs').textContent = '获取失败: ' + err; });
}
function showNicknames() {
    apiFetch('/api/get_nicknames')
        .then(res => res.json())
        .then(data => {
            var lines = Object.entries(data).map(([mac, nick]) => mac + ' -> ' + nick);
            document.getElementById('nicknameList').textContent = lines.join('\n') || '暂无昵称';
        })
        .catch(err => { document.getElementById('nicknameList').textContent = '获取失败: ' + err; });
}

// ============================================================
// UDP 消息列表（通用）
// ============================================================
function fetchUdpMessages(containerId) {
    apiFetch('/api/udp_messages')
        .then(res => res.json())
        .then(data => {
            var container = document.getElementById(containerId);
            if (!container) return;
            if (data.length === 0) {
                container.textContent = '暂无消息';
                return;
            }
            var lines = data.map(item => {
                var timeStr = new Date(item.time * 1000).toLocaleTimeString();
                return timeStr + ' ' + item.addr + ': ' + item.msg;
            });
            container.textContent = lines.join('\n\n');
        })
        .catch(err => console.error('获取UDP消息失败:', err));
}
function refreshUdpMessages(page) {
    var map = {
        'broadcast': 'udpMsgList_broadcast',
        'unicast': 'udpMsgList_unicast',
        'neighbor': 'udpMsgList_neighbor',
        'route': 'udpMsgList_route'
    };
    var containerId = map[page] || 'udpMsgList_broadcast';
    showResult('result_' + page, '正在刷新...');
    fetchUdpMessages(containerId);
    showResult('result_' + page, '刷新完成');
}
function clearUdpMsg(page) {
    if (!confirm('确定清空所有UDP消息记录吗？')) return;
    apiFetch('/api/clear_udp_messages', { method: 'POST' })
        .then(res => res.text())
        .then(data => {
            showResult('result_' + page, '清空消息: ' + data);
            refreshUdpMessages(page);
        })
        .catch(err => showResult('result_' + page, '请求失败: ' + err.toString()));
}

// ============================================================
// 页面加载时恢复 IP
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    loadSavedIp();
});