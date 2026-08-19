import json
import os
import re
import sys
import urllib.error
import urllib.request

SOURCE_REPO = "Bedrock-OSS/BDS-Versions"
README_PATH = "README.md"
GENERATED_COPY_PATH = "other-data/generated_readme_lists.md"

SECTIONS = [
    ("windows", "win", "WIN-RELEASES"),
    ("windows_preview", "win-preview", "WIN-PREVIEWS"),
    ("linux", "linux", "LINUX-RELEASES"),
    ("linux_preview", "linux-preview", "LINUX-PREVIEWS"),
]


def fetch_versions(folder, token=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{SOURCE_REPO}/contents/{folder}",
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"},
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"GitHub API error on '{folder}': {e.code} {e.reason}\n{e.read().decode(errors='replace')}")

    return [entry["name"][:-5] for entry in data if entry["name"].endswith(".json")]


def sort_versions(versions):
    return sorted(versions, key=lambda v: tuple(int(n) for n in re.findall(r"\d+", v)))


def to_markdown(versions, platform_tag):
    return "".join(
        f"* [{v}](https://minecraft.net/bedrockdedicatedserver/bin-{platform_tag}/bedrock-server-{v}.zip)\n\n"
        for v in versions
    )


def swap_section(readme, marker, body):
    start, end = f"<!-- {marker}:START -->", f"<!-- {marker}:END -->"
    block = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not block.search(readme):
        sys.exit(f"couldn't find {start} / {end} in {README_PATH} - did someone touch the markers?")
    return block.sub(f"{start}\n{body}{end}", readme, count=1)


def main():
    token = os.environ.get("GITHUB_TOKEN")
    fetched = {}

    for folder, tag, marker in SECTIONS:
        versions = sort_versions(fetch_versions(folder, token))
        fetched[marker] = (versions, tag)
        print(f"{folder}: {len(versions)} versions")

    with open(README_PATH, encoding="utf-8") as f:
        readme = f.read()

    for marker, (versions, tag) in fetched.items():
        readme = swap_section(readme, marker, to_markdown(versions, tag))

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(readme)

    win_rel, win_rel_tag = fetched["WIN-RELEASES"]
    win_prev, win_prev_tag = fetched["WIN-PREVIEWS"]
    lin_rel, lin_rel_tag = fetched["LINUX-RELEASES"]
    lin_prev, lin_prev_tag = fetched["LINUX-PREVIEWS"]

    os.makedirs("other-data", exist_ok=True)
    with open(GENERATED_COPY_PATH, "w", encoding="utf-8") as f:
        f.write("### Windows Servers:\n**Releases:**\n\n")
        f.write(to_markdown(win_rel, win_rel_tag))
        f.write("\n**Previews:**\n\n")
        f.write(to_markdown(win_prev, win_prev_tag))
        f.write("\n---\n\n### Linux Servers:\n**Releases:**\n\n")
        f.write(to_markdown(lin_rel, lin_rel_tag))
        f.write("\n**Previews:**\n\n")
        f.write(to_markdown(lin_prev, lin_prev_tag))

    total = sum(len(v) for v, _ in fetched.values())
    print(f"done - {total} versions total")


if __name__ == "__main__":
    main()