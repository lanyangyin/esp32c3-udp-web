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
import minify_html, os, argparse

def minify_html_files(source_dir, dest_dir, exclude_dirs=[]):
    for root, dirs, files in os.walk(source_dir):
        rel = os.path.relpath(root, source_dir)
        if rel == '.':
            rel = ''
        skip = False
        for ex in exclude_dirs:
            if rel == ex or rel.startswith(ex + os.sep):
                skip = True
                break
        if skip:
            continue
        for f in files:
            if f.endswith('.html'):
                src_file = os.path.join(root, f)
                rel_path = os.path.relpath(src_file, source_dir)
                dest_file = os.path.join(dest_dir, rel_path)
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                with open(src_file, 'r', encoding='utf-8') as fp:
                    html = fp.read()
                minified = minify_html.minify(html, minify_js=True, minify_css=True, remove_processing_instructions=True)
                with open(dest_file, 'w', encoding='utf-8') as fp:
                    fp.write(minified)
                print(f"压缩 HTML: {src_file} -> {dest_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='.')
    parser.add_argument('--dest', default='min')
    parser.add_argument('--exclude-dirs', nargs='*', default=[], help='要排除的目录名（相对于source）')
    args = parser.parse_args()
    minify_html_files(args.source, args.dest, args.exclude_dirs)