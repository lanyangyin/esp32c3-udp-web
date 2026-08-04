# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: 2026 lanyangyin <2436725966@qq.com>
#
# This file is part of the ESP32-C3 Multi-Function Control Platform project.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# loader.py - 按需加载 JSON 配置文件
import json
import time
import gc

# 简单的 LRU 缓存（最多保留 3 个模块）
_cache = {}
CACHE_MAX = 3

def _load_json_file(filepath):
    """加载 JSON 文件并返回对象，失败返回 None"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[LOADER] 加载 {filepath} 失败: {e}")
        return None

def _cache_get(key):
    if key in _cache:
        _cache[key]['last_used'] = time.time()
        return _cache[key]['data']
    return None

def _cache_set(key, data):
    global _cache
    if len(_cache) >= CACHE_MAX:
        oldest_key = min(_cache.keys(), key=lambda k: _cache[k]['last_used'])
        del _cache[oldest_key]
        gc.collect()
    _cache[key] = {'data': data, 'last_used': time.time()}

def load_commands(module_name):
    """
    加载指定模块的命令列表
    返回 list，若失败返回空列表
    """
    key = f"commands_{module_name}"
    data = _cache_get(key)
    if data is not None:
        return data
    filepath = f"commands/{module_name}.json"
    data = _load_json_file(filepath)
    if data is None:
        return []
    _cache_set(key, data)
    return data

def load_api_catalog(api_type):
    """
    加载指定类型的 API 列表
    返回 list，若失败返回空列表
    """
    key = f"api_{api_type}"
    data = _cache_get(key)
    if data is not None:
        return data
    filepath = f"api_catalog/{api_type}.json"
    data = _load_json_file(filepath)
    if data is None:
        return []
    _cache_set(key, data)
    return data

def load_all_api_types():
    """
    加载所有 API 类型名称列表（从文件名读取）
    返回 list of strings
    """
    import os
    try:
        files = os.listdir('api_catalog')
        types = [f.replace('.json', '') for f in files if f.endswith('.json')]
        return types
    except:
        return []

def release_cache(module_name=None):
    """
    释放缓存
    如果指定 module_name，只释放该模块；否则清空所有缓存
    """
    global _cache
    if module_name is None:
        _cache.clear()
        gc.collect()
    else:
        key1 = f"commands_{module_name}"
        key2 = f"api_{module_name}"
        if key1 in _cache:
            del _cache[key1]
        if key2 in _cache:
            del _cache[key2]
        gc.collect()