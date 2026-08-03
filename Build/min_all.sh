#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== 开始构建（源文件保持不变） ==="
echo "项目根目录: $PROJECT_ROOT"

# 1. 生成 commands 和 api_catalog（写入 PublicModule）
echo ">>> 运行 generate_jsons.py"
python3 "$SCRIPT_DIR/generate_jsons.py"
if [ ! -d "PublicModule/commands" ] || [ ! -d "PublicModule/api_catalog" ]; then
    echo "错误: generate_jsons.py 未生成所需目录"
    exit 1
fi
echo "generate_jsons.py 完成"

# 2. 同步 PublicModule 到 server_flip 和 client（覆盖）
echo ">>> 同步 PublicModule 到 server_flip 和 client"
cp -r PublicModule/* server_flip/
cp -r PublicModule/* client/
echo "同步完成"

# 3. 构建 Build/server 和 Build/client（完整复制，保留 src）
build_from_source() {
    local src_dir=$1
    local dst_dir=$2
    echo ">>> 构建 $dst_dir 从 $src_dir（完整复制，保留所有子目录，包括 src）"
    rm -rf "$dst_dir"
    mkdir -p "$dst_dir"
    cp -r "$src_dir"/* "$dst_dir/"
    echo "复制完成"
}

build_from_source "server_flip" "Build/server"
build_from_source "client" "Build/client"

# 4. 在构建目录中编译 .py → .mpy，并删除 .py（除 boot.py 和 main.py）
compile_mpy() {
    local build_dir=$1
    echo ">>> 在 $build_dir 中编译 .py → .mpy，并删除原 .py（保留 boot.py 和 main.py）"
    find "$build_dir" -name "*.py" ! -name "boot.py" ! -name "main.py" -type f | while read -r pyfile; do
        echo "  编译: $pyfile"
        mpy-cross-multi "$pyfile" || { echo "    警告: 编译失败，跳过"; continue; }
        mpypath="${pyfile%.py}.mpy"
        if [ -f "$mpypath" ]; then
            rm "$pyfile"
            echo "    生成: $mpypath，已删除原 .py: $pyfile"
        else
            echo "    警告: 未生成 .mpy，保留 .py"
        fi
    done
    echo "编译和清理完成"
}

compile_mpy "Build/server"
compile_mpy "Build/client"

# 5. 压缩 HTML 和 JS（从源目录读取，输出到构建目录）
compress_assets() {
    local src_dir=$1
    local dst_dir=$2
    echo ">>> 压缩 HTML（从 $src_dir 到 $dst_dir）"
    python3 "$SCRIPT_DIR/min_html.py" --source "$src_dir" --dest "$dst_dir"
    echo ">>> 压缩 JS（从 $src_dir 到 $dst_dir）"
    python3 "$SCRIPT_DIR/min_js.py" --source "$src_dir" --dest "$dst_dir"
}

compress_assets "server_flip" "Build/server"
compress_assets "client" "Build/client"

# 6. 清理构建目录中的 __pycache__
find "Build/server" "Build/client" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 7. 额外将生成的 commands/api_catalog 复制到 Build/server 和 Build/client（确保最新）
# 其实已经通过复制源目录获得了，但为保险再复制一次（覆盖）
echo ">>> 确保 Build 中有最新的 commands 和 api_catalog"
cp -r PublicModule/commands Build/server/ 2>/dev/null || true
cp -r PublicModule/api_catalog Build/server/ 2>/dev/null || true
cp -r PublicModule/commands Build/client/ 2>/dev/null || true
cp -r PublicModule/api_catalog Build/client/ 2>/dev/null || true

echo "=== 构建完成 ==="
echo "源文件 server_flip 和 client 未被修改（除同步 PublicModule 外）"
echo "构建产物位于 Build/server 和 Build/client"
echo "所有原有目录（包括 src）均被保留，未主动创建新的 src"
echo "入口 boot.py 和 main.py 保留为 .py，其余 .py 已编译为 .mpy 并删除原文件"