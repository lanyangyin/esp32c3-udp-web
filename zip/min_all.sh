#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "开始批量压缩..."

SERVER_SRC="server_flip/src"
CLIENT_SRC="client/src"
mkdir -p "$SERVER_SRC" "$CLIENT_SRC"

# 复制 boot.py 和 main.py
echo ">>> 复制 boot.py 和 main.py"
cp boot.py "$SERVER_SRC/" 2>/dev/null && echo "boot.py -> $SERVER_SRC/"
cp main.py "$SERVER_SRC/" 2>/dev/null && echo "main.py -> $SERVER_SRC/"
cp boot.py "$CLIENT_SRC/" 2>/dev/null && echo "boot.py -> $CLIENT_SRC/"
cp main.py "$CLIENT_SRC/" 2>/dev/null && echo "main.py -> $CLIENT_SRC/"

# 编译公共模块
echo ">>> 编译公共模块"
for f in constants.py fragment_protocol.py led.py neighbor.py route.py udp.py udp_sender.py util.py wifi.py; do
    [ -f "$f" ] || continue
    mpy-cross-multi "$f"
    base="${f%.py}"
    [ -f "${base}.mpy" ] || { echo "警告: 未生成 ${base}.mpy"; continue; }
    cp "${base}.mpy" "$SERVER_SRC/" && cp "${base}.mpy" "$CLIENT_SRC/"
    rm "${base}.mpy"
    echo "公共模块 $f -> ${base}.mpy 已复制并删除临时文件"
done

# 处理 server_flip
echo ">>> 处理 server_flip"
cd server_flip || exit
# 复制已有 .mpy
find . -name "*.mpy" ! -path "./src/*" ! -path "./min/*" ! -path "./__pycache__/*" | while read -r m; do
    t="src/${m#./}"
    mkdir -p "$(dirname "$t")"
    cp "$m" "$t"
    echo "复制已有 .mpy: $m -> $t"
done
# 编译 .py
for p in $(find . -name "*.py" ! -path "./src/*" ! -path "./min/*" ! -path "./__pycache__/*"); do
    # 排除 min_html.py 和 min_js.py
    case "$p" in
        min_html.py|min_js.py|boot.py|constants.py|fragment_protocol.py|led.py|main.py|neighbor.py|route.py|udp.py|udp_sender.py|util.py|wifi.py) continue ;;
    esac
    mpy-cross-multi "$p"
    b="${p%.py}.mpy"
    [ -f "$b" ] || { echo "警告: 未生成 $b"; continue; }
    td="src/$(dirname "$p")"
    mkdir -p "$td"
    mv "$b" "$td/"
    echo "编译 $p -> $td/$(basename "$b")"
done
cd ..

# 处理 client
echo ">>> 处理 client"
cd client || exit
find . -name "*.mpy" ! -path "./src/*" ! -path "./min/*" ! -path "./__pycache__/*" | while read -r m; do
    t="src/${m#./}"
    mkdir -p "$(dirname "$t")"
    cp "$m" "$t"
    echo "复制已有 .mpy: $m -> $t"
done
for p in $(find . -name "*.py" ! -path "./src/*" ! -path "./min/*" ! -path "./__pycache__/*"); do
    # 排除 min_html.py 和 min_js.py
    case "$p" in
        min_html.py|min_js.py|boot.py|constants.py|fragment_protocol.py|led.py|main.py|neighbor.py|route.py|udp.py|udp_sender.py|util.py|wifi.py) continue ;;
    esac
    mpy-cross-multi "$p"
    b="${p%.py}.mpy"
    [ -f "$b" ] || { echo "警告: 未生成 $b"; continue; }
    td="src/$(dirname "$p")"
    mkdir -p "$td"
    mv "$b" "$td/"
    echo "编译 $p -> $td/$(basename "$b")"
done
cd ..

# 压缩 HTML
echo ">>> 压缩 HTML"
python3 "${SCRIPT_DIR}/min_html.py" --source server_flip --dest server_flip/src

# 压缩 JS
echo ">>> 压缩 JS"
python3 "${SCRIPT_DIR}/min_js.py" --source server_flip --dest server_flip/src

echo "所有任务完成！"