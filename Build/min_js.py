import jsmin, os, argparse

def minify_js_files(source_dir, dest_dir, exclude_dirs=[]):
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
            if f.endswith('.js'):
                src_file = os.path.join(root, f)
                rel_path = os.path.relpath(src_file, source_dir)
                dest_file = os.path.join(dest_dir, rel_path)
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                with open(src_file, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                minified = jsmin.jsmin(content)
                with open(dest_file, 'w', encoding='utf-8') as fp:
                    fp.write(minified)
                print(f"压缩 JS: {src_file} -> {dest_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='.')
    parser.add_argument('--dest', default='min')
    parser.add_argument('--exclude-dirs', nargs='*', default=[], help='要排除的目录名（相对于source）')
    args = parser.parse_args()
    minify_js_files(args.source, args.dest, args.exclude_dirs)