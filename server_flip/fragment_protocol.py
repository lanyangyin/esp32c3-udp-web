import json
import socket
import binascii
import time
import random
import _thread
from constants import (
    FRAGMENT_CACHE_TIMEOUT,
    FRAGMENT_MAX_BYTES,
    FRAGMENT_DEFAULT_TTL,
    FRAGMENT_MAX_CACHE_SIZE, DEBUG_FRAGMENT
)

_frag_lock = _thread.allocate_lock()
_frag_cache = {}
"""分片重组缓存：msg_id → {total, fragments, src_mac, dst_mac, tag, ttl, last_time}"""

def _enforce_cache_size(except_key=None):
    """确保 _frag_cache 不超过 FRAGMENT_MAX_CACHE_SIZE，删除最旧的条目（可排除当前 key）"""
    global _frag_cache
    while len(_frag_cache) > FRAGMENT_MAX_CACHE_SIZE:
        # 找出 last_time 最小的条目（最旧），并删除
        oldest_key = None
        oldest_time = float('inf')
        for key, cache in _frag_cache.items():
            if key == except_key:
                continue   # 不删除当前正在处理的条目
            if cache['last_time'] < oldest_time:
                oldest_time = cache['last_time']
                oldest_key = key
        if oldest_key is None:
            # 若 except_key 是唯一条目，则无法删除，退出循环
            break
        del _frag_cache[oldest_key]
        print(f"[UDP] 分片缓存超限，删除最旧条目: {oldest_key}")


def _get_next_msg_id():
    return random.randint(1, 65535)


def _split_utf8_bytes(text, max_bytes, punctuation):
    data = text.encode('utf-8')
    total = len(data)
    fragments = []
    start = 0
    loop_count = 0
    while start < total:
        loop_count += 1
        if DEBUG_FRAGMENT:
            print(f"[分片] 循环 {loop_count}: start={start}, total={total}")
        end = min(start + max_bytes, total)
        if DEBUG_FRAGMENT:
            print(f"  初始 end={end}")

        # 回退避免截断多字节字符
        while end > start and end < len(data) and (data[end] & 0xC0) == 0x80:
            end -= 1
        if DEBUG_FRAGMENT:
            print(f"  边界回退后 end={end}")

        if end < total:
            # 修改这里：errors='ignore' → 'ignore' 作为位置参数
            segment = data[start:end].decode('utf-8', 'ignore')
            last_punct_pos = -1
            for p in punctuation:
                pos = segment.rfind(p)
                if pos > last_punct_pos:
                    last_punct_pos = pos
            if last_punct_pos >= 0:
                new_end = start + len(segment[:last_punct_pos + 1].encode('utf-8'))
                if new_end > start:
                    end = new_end
            if DEBUG_FRAGMENT:
                print(f"  标点调整后 end={end}")

        if end == start:
            end = min(start + 1, total)
            if DEBUG_FRAGMENT:
                print(f"  强制推进 end={end}")

        frag = data[start:end].decode('utf-8')
        fragments.append(frag)
        if DEBUG_FRAGMENT:
            print(f"  添加片段长度={len(frag.encode('utf-8'))}, 片段内容='{frag[:50]}'")
        start = end

    if DEBUG_FRAGMENT:
        print(f"[分片] 最终共 {len(fragments)} 片")
    return fragments


def send_udp_fragmented(target_ip, port, src_mac, dst_mac, content,
                        tag='TXT', max_bytes=FRAGMENT_MAX_BYTES,
                        punctuation='.,!?;:\n，。！？；：\n', ttl=FRAGMENT_DEFAULT_TTL):
    """
    发送分片 UDP 消息，阻塞直到所有分片发送完成。

    该函数将长文本按 UTF-8 字节长度切分成多个分片，每个分片携带元数据（ID、总长度、TTL 等），
    使用 Base64 编码分片数据，并以管道符 '|' 拼接成字符串发送。
    接收端根据 ID 和源 MAC 重组分片。

    参数：
        target_ip (str): 目标 IP 地址
        port (int): 目标 UDP 端口
        src_mac (str): 源 MAC 地址（发送方）
        dst_mac (str): 目的 MAC 地址（"FF:FF:FF:FF:FF:FF" 表示广播）
        content (str): 要发送的文本内容（可为 None 或空字符串）
        tag (str): 消息标签，用于标识消息类型（如 "邻居注册请求"）
        max_bytes (int): 每个分片的最大字节数（建议 256~512，避免内存不足）
        punctuation (str): 分片时尽量在标点符号处断开，提高可读性
        ttl (int): 生存时间（跳数），每转发一次减 1，为 0 时丢弃

    返回：
        bool: True 表示所有分片发送成功，False 表示发送失败
    """
    # ===== 调试打印 =====
    print(f"[UDP] send_udp_fragmented 调用: tag={tag}, dst_mac={dst_mac}")
    if DEBUG_FRAGMENT:
        print(f"[UDP] content 类型: {type(content)}, 内容: {content if isinstance(content, str) else repr(content)[:100]}")

    # ---------- 类型防御 ----------
    if content is None:
        content = ""                      # 将 None 转换为空字符串，避免编码报错
    elif type(content) == int:
        content = str(content)
    elif isinstance(content, dict):
        content = json.dumps(content, indent=2)
        print(f"[UDP] 字典已转换为 JSON 字符串")
    elif not isinstance(content, str):
        content = str(content)
        print(f"[UDP] 非字符串类型已转换为字符串")

    if ttl <= 0:
        ttl = 1                           # TTL 至少为 1，保证消息至少能发送出去

    # ---------- 2. 将内容编码为 UTF-8 字节 ----------
    content_bytes = content.encode('utf-8')
    total_bytes = len(content_bytes)      # 总字节数，用于接收端校验完整性

    # ---------- 3. 切分成片（智能分段） ----------
    if DEBUG_FRAGMENT:
        print(f"[UDP] 准备分片: content='{content[:50]}{'...' if len(content)>50 else ''}', 总字节数={total_bytes}, max_bytes={max_bytes}")

    if total_bytes == 0:
        fragments = ['']
        print("[UDP] 内容为空，创建空分片")
    else:
        try:
            fragments = _split_utf8_bytes(content, max_bytes, punctuation)
            print(f"[UDP] 分片完成: 共 {len(fragments)} 片")
        except Exception as e:
            print(f"[UDP] 分片异常: {e}")
            import sys
            sys.print_exception(e)
            return False
        for i, frag in enumerate(fragments):
            frag_bytes = frag.encode('utf-8')
            if DEBUG_FRAGMENT:
                print(f"  分片 {i+1}: 文本='{frag[:30]}{'...' if len(frag)>30 else ''}', 字节长度={len(frag_bytes)}")

    # ---------- 4. 分配消息 ID 和 UDP socket ----------
    msg_id = _get_next_msg_id()           # 获取 1~10 的循环 ID，用于接收端重组
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)  # 防止阻塞
    sent_count = 0
    sent_bytes_total = 0                  # 已发送的字节数（用于计算剩余字节）

    # ---------- 5. 遍历所有分片并发送 ----------
    for idx, frag in enumerate(fragments):
        # 5.1 将分片文本编码为 UTF-8 字节
        frag_bytes = frag.encode('utf-8')
        frag_len = len(frag_bytes)

        # 5.2 计算剩余字节数（用于接收端判断是否还有后续分片）
        remaining = total_bytes - sent_bytes_total - frag_len
        if remaining < 0:
            remaining = 0                 # 防止因计算误差出现负数

        # 5.3 将分片字节进行 Base64 编码（便于在文本协议中传输二进制数据）
        data_b64 = binascii.b2a_base64(frag_bytes).decode('ascii').strip()

        # 5.4 构造分片消息格式（管道符分隔的键值对）
        # 格式示例: TAG=xxx|SRC=...|DST=...|TOT=100|LEN=20|REM=80|ID=3|TTL=16|DATA=SGVsbG8=
        msg = f"TAG={tag}|SRC={src_mac}|DST={dst_mac}|TOT={total_bytes}|LEN={frag_len}|REM={remaining}|ID={msg_id}"
        msg += f"|TTL={ttl}|DATA={data_b64}"

        # 5.5 发送 UDP 数据包
        try:
            sock.sendto(msg.encode('utf-8'), (target_ip, port))
            print(f"[UDP] 发送到{(target_ip, port)}")
            sent_count += 1
            sent_bytes_total += frag_len
        except Exception as e:
            # 发送失败时打印错误并关闭 socket，返回 False
            print(f"[UDP] 发送分片 {idx + 1}/{len(fragments)} 失败: {e}")
            sock.close()
            return False

    # ---------- 6. 关闭 socket 并打印完成信息 ----------
    sock.close()
    if DEBUG_FRAGMENT:
        print(f"[UDP] 分片发送完成: {sent_count}片, ID={msg_id}, TTL={ttl}, DST={dst_mac}")
    return True


def parse_fragmented_msg(msg):
    """解析单条分片消息，返回字典"""
    result = {}
    for part in msg.split('|'):
        if '=' in part:
            key, value = part.split('=', 1)
            result[key] = value.strip()
    return result


def reassemble_fragment(parsed, _addr=None):
    """
    重组分片消息。
    返回 (complete, payload, src_mac, dst_mac, tag, ttl) 或 (False, None, None, None, None, None)
    """
    global _frag_cache

    msg_id = parsed.get('ID')
    src_mac = parsed.get('SRC', '')
    if not msg_id or not src_mac:
        return False, None, None, None, None, None

    # ✅ 缓存键 = msg_id + src_mac（隔离不同来源）
    cache_key = f"{msg_id}_{src_mac}"

    total = int(parsed.get('TOT', 0))
    frag_len = int(parsed.get('LEN', 0))
    data_b64 = parsed.get('DATA', '')
    dst_mac = parsed.get('DST', '')
    tag = parsed.get('TAG', '')
    ttl = int(parsed.get('TTL', FRAGMENT_DEFAULT_TTL))

    # TTL 减 1，如果 < 0 则丢弃
    ttl -= 1

    # 解码数据（无共享资源，可以放在锁外）
    try:
        frag_data = binascii.a2b_base64(data_b64).decode('utf-8')
    except:
        print(f"[UDP] 分片数据解码失败")
        return False, None, None, None, None, None

    # ---- 以下进入临界区 ----
    with _frag_lock:
        # 如果 TTL 耗尽，删除缓存并丢弃
        if ttl < 0:
            if cache_key in _frag_cache:
                del _frag_cache[cache_key]
            print(f"[UDP] 分片 TTL 耗尽，丢弃 ID={msg_id}, SRC={src_mac}")
            return False, None, None, None, None, None

        # 限制缓存大小
        if len(_frag_cache) >= FRAGMENT_MAX_CACHE_SIZE:
            # 删除最旧的条目（按 last_time 排序）
            oldest_key = min(_frag_cache.keys(), key=lambda k: _frag_cache[k]['last_time'])
            del _frag_cache[oldest_key]
            print(f"[UDP] 分片缓存已满，删除最旧条目 {oldest_key}")

        # 初始化或更新缓存
        if cache_key not in _frag_cache:
            _frag_cache[cache_key] = {
                'total': total,
                'src_mac': src_mac,
                'dst_mac': dst_mac,
                'tag': tag,
                'ttl': ttl,
                'fragments': [],
                'received': 0,
                'last_time': time.time()
            }
            # 添加新条目后检查大小限制（不删除当前条目）
            _enforce_cache_size(except_key=cache_key)
        else:
            # 更新 TTL（取较小值）
            if ttl < _frag_cache[cache_key]['ttl']:
                _frag_cache[cache_key]['ttl'] = ttl

        cache = _frag_cache[cache_key]
        cache['fragments'].append(frag_data)
        cache['received'] += frag_len
        cache['last_time'] = time.time()

        # 检查是否完整
        if cache['received'] >= total:
            payload = ''.join(cache['fragments'])
            src = cache['src_mac']
            dst = cache['dst_mac']
            tag_out = cache['tag']
            ttl_out = cache['ttl']
            # 清理缓存
            del _frag_cache[cache_key]
            if DEBUG_FRAGMENT:
                print(f"[UDP] 分片重组完成: {len(cache['fragments'])}片, ID={msg_id}, SRC={src}")
            return True, payload, src, dst, tag_out, ttl_out

    return False, None, None, None, None, None


def clean_frag_cache():
    """清理超时的分片缓存（30秒超时）"""
    global _frag_cache
    now = time.time()
    to_delete = []
    with _frag_lock:
        # 1. 收集超时条目
        for cache_key, cache in _frag_cache.items():
            if now - cache['last_time'] > FRAGMENT_CACHE_TIMEOUT:
                to_delete.append(cache_key)
        # 2. 删除超时条目
        for cache_key in to_delete:
            del _frag_cache[cache_key]
            print(f"[UDP] 分片缓存超时清理: {cache_key}")
        # 3. 裁剪多余条目（调用时已持有锁）
        _enforce_cache_size(except_key=None)