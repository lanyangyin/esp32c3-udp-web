import minify_html, os, argparse

def minify_html_files(source_dir, dest_dir, exclude_dirs=['src']):
    for root, dirs, files in os.walk(source_dir):
        rel = os.path.relpath(root, source_dir)
        if rel == '.': rel = ''
        if any(rel.startswith(ex + os.sep) or rel == ex for ex in exclude_dirs):
            continue
        for f in files:
            if f.endswith('.html'):
                p = os.path.join(root, f)
                rp = os.path.relpath(p, source_dir)
                dp = os.path.join(dest_dir, rp)
                os.makedirs(os.path.dirname(dp), exist_ok=True)
                with open(p, 'r', encoding='utf-8') as fp:
                    html = fp.read()
                minified = minify_html.minify(html, minify_js=True, minify_css=True, remove_processing_instructions=True)
                with open(dp, 'w', encoding='utf-8') as fp:
                    fp.write(minified)
                print(f"压缩完成: {p} -> {dp}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='.')
    parser.add_argument('--dest', default='min')
    args = parser.parse_args()
    minify_html_files(args.source, args.dest)