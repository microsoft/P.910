"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

import argparse
import glob
import os
import re
from urllib.parse import urlparse

import pandas as pd
import requests


def find_files(directory):
    """
    Find the .html, .csv, and .cfg files in the given directory.

    :param directory: Path to the directory containing master script output.
    :return: Tuple of (html_path, csv_path, cfg_path).
    """
    html_files = [f for f in glob.glob(os.path.join(directory, "*.html")) if "_row-" not in f]
    csv_files = glob.glob(os.path.join(directory, "*_publish_batch.csv"))
    cfg_files = glob.glob(os.path.join(directory, "*.cfg"))

    if len(html_files) != 1:
        raise FileNotFoundError(
            f"Expected exactly 1 .html file in '{directory}', found {len(html_files)}"
        )
    if len(csv_files) != 1:
        raise FileNotFoundError(
            f"Expected exactly 1 _publish_batch.csv file in '{directory}', found {len(csv_files)}"
        )
    if len(cfg_files) != 1:
        raise FileNotFoundError(
            f"Expected exactly 1 .cfg file in '{directory}', found {len(cfg_files)}"
        )

    return html_files[0], csv_files[0], cfg_files[0]


def replace_placeholders(template, row):
    """
    Replace all ${column_name} placeholders in the template with the row values.

    :param template: The HTML template string.
    :param row: A pandas Series representing one row of the CSV.
    :return: The HTML string with placeholders replaced.
    """
    result = template
    for col_name, value in row.items():
        placeholder = "${" + str(col_name) + "}"
        result = result.replace(placeholder, str(value))
    return result


def download_assets(html_content, assets_dir):
    """
    Find all external .js, .css, .woff, and .woff2 URLs in the HTML, download them
    into assets_dir, and return updated HTML with local relative paths.

    :param html_content: The HTML string to scan.
    :param assets_dir: Directory where downloaded assets will be saved.
    :return: The HTML string with remote URLs replaced by local paths.
    """
    extensions = r'\.(js|css|woff2?)'
    url_pattern = re.compile(r'(https?://[^\s"\'<>]+?' + extensions + r')', re.IGNORECASE)

    urls = set(url_pattern.findall(html_content))
    if not urls:
        return html_content

    os.makedirs(assets_dir, exist_ok=True)
    assets_rel = os.path.basename(assets_dir)

    for url_match in urls:
        url = url_match[0]
        filename = os.path.basename(urlparse(url).path)
        local_path = os.path.join(assets_dir, filename)

        if not os.path.exists(local_path):
            print(f"  Downloading {url}")
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)
            except requests.RequestException as e:
                print(f"  Warning: failed to download {url}: {e}")
                continue

        html_content = html_content.replace(url, f"{assets_rel}/{filename}")

    # Scan downloaded CSS files for font references and download them too
    _download_css_fonts(assets_dir)

    return html_content


def _download_css_fonts(assets_dir):
    """
    Scan all CSS files in assets_dir for url(...) references to font files,
    download them into assets_dir, and rewrite the CSS paths.

    :param assets_dir: Directory containing downloaded CSS files.
    """
    font_url_pattern = re.compile(
        r"""url\(\s*['"]?([^'")]+\.(?:woff2?|ttf|eot|svg)[^'")]*?)['"]?\s*\)""",
        re.IGNORECASE,
    )

    for css_file in glob.glob(os.path.join(assets_dir, "*.css")):
        with open(css_file, "r", encoding="utf-8", errors="replace") as f:
            css_content = f.read()

        matches = font_url_pattern.findall(css_content)
        if not matches:
            continue

        modified = False

        for ref in set(matches):
            clean_ref = ref.split("?")[0].split("#")[0]
            filename = os.path.basename(clean_ref)
            local_path = os.path.join(assets_dir, filename)

            if not os.path.exists(local_path):
                if clean_ref.startswith(("http://", "https://")):
                    download_url = clean_ref
                else:
                    download_url = _guess_font_url(clean_ref, filename)
                    if not download_url:
                        print(f"  Warning: cannot resolve font reference '{ref}' in {os.path.basename(css_file)}")
                        continue

                print(f"  Downloading font {download_url}")
                try:
                    resp = requests.get(download_url, timeout=30)
                    resp.raise_for_status()
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                except requests.RequestException as e:
                    print(f"  Warning: failed to download {download_url}: {e}")
                    continue

            css_content = css_content.replace(ref, filename)
            modified = True

        if modified:
            with open(css_file, "w", encoding="utf-8") as f:
                f.write(css_content)


def _guess_font_url(relative_ref, filename):
    """
    Try to resolve a relative font path to an absolute URL using known CDN patterns.

    :param relative_ref: The relative path found in the CSS (e.g. '../fonts/glyphicons-halflings-regular.woff').
    :param filename: Just the filename portion.
    :return: An absolute URL string or None.
    """
    known_sources = [
        f"https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.3.7/fonts/{filename}",
    ]
    for url in known_sources:
        try:
            resp = requests.head(url, timeout=10)
            if resp.status_code == 200:
                return url
        except requests.RequestException:
            continue
    return None


def _disable_fetch_for_local(html_content):
    """
    Replace the checkScripts() function body with a no-op so that the preview
    works with the file:// protocol. fetch() does not support file:// URLs.

    Uses brace-counting to reliably find the function boundary regardless of
    indentation style (tabs vs. spaces).

    :param html_content: The HTML string.
    :return: The HTML string with checkScripts() neutralized.
    """
    match = re.search(r'async\s+function\s+checkScripts\s*\(\s*\)\s*\{', html_content)
    if not match:
        return html_content

    start = match.start()
    brace_pos = match.end() - 1
    depth = 1
    i = brace_pos + 1
    while i < len(html_content) and depth > 0:
        if html_content[i] == '{':
            depth += 1
        elif html_content[i] == '}':
            depth -= 1
        i += 1

    replacement = (
        "async function checkScripts() {\n"
        "  // Disabled in local preview \u2014 fetch() does not work with file:// protocol\n"
        "  return;\n"
        "}"
    )
    return html_content[:start] + replacement + html_content[i:]


def _replace_local_assets_with_cdn(html_content):
    """
    Replace relative asset paths (e.g. ../assets/bootstrap.min.css) with
    publicly available CDN URLs so the preview works without local files.

    :param html_content: The HTML string.
    :return: The HTML string with CDN URLs.
    """
    cdn_map = {
        'bootstrap.min.css': 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css',
        'jquery.min.js': 'https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js',
        'bootstrap.min.js': 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js',
    }
    for filename, cdn_url in cdn_map.items():
        html_content = re.sub(
            r'["\']\.\.\/assets\/' + re.escape(filename) + r'["\']',
            f'"{cdn_url}"',
            html_content,
        )
    return html_content


def generate_previews(directory, samples):
    """
    Generate preview HTML files by substituting CSV row values into the HTML template
    and downloading external assets for local use.

    :param directory: Path to the directory containing master script output.
    :param samples: Number of rows from the CSV to generate previews for.
    :return: List of generated file paths.
    """
    html_path, csv_path, _ = find_files(directory)
    df = pd.read_csv(csv_path)

    if samples > len(df):
        print(f"Warning: requested {samples} samples but CSV only has {len(df)} rows. Using all rows.")
        samples = len(df)

    with open(html_path, "r", encoding="utf-8") as f:
        template = f.read()

    template = _replace_local_assets_with_cdn(template)

    base_name = os.path.splitext(os.path.basename(html_path))[0]
    generated_files = []

    for i in range(samples):
        row = df.iloc[i]
        html_content = replace_placeholders(template, row)
        html_content = _disable_fetch_for_local(html_content)
        output_path = os.path.join(directory, f"{base_name}_row-{i + 1}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        generated_files.append(output_path)
        print(f"  [{output_path}] is created")

    print(f"Generated {samples} preview file(s).")

    return generated_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate preview HTML files from master script output by substituting CSV values "
                    "into the HTML template. External .js, .css, .woff, .woff2 files are downloaded "
                    "into a local assets/ directory so the preview works offline without CORS issues."
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Path to the directory containing the .html, .csv, and .cfg output files from master_script.py",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Number of CSV rows to generate preview HTML files for (default: 1)",
    )
    args = parser.parse_args()

    assert os.path.isdir(args.dir), f"Directory not found: {args.dir}"
    assert args.samples > 0, "Number of samples must be at least 1"

    generate_previews(args.dir, args.samples)
