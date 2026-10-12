"""只读核验本轮交付文件；输出核验记录，不调用网络或模型。"""
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import struct
import subprocess

base = Path(__file__).resolve().parent
plan = json.loads((base / "16镜-完整输入-v001.json").read_text())
manifest = json.loads((base / "交付清单-v001.json").read_text())
records = [json.loads(p.read_text()) for p in sorted(base.glob("S*-生成记录-*.json"))]
checks = {}
for p in base.glob("*.json"):
    json.loads(p.read_text())
checks["jsonFilesParsed"] = len(list(base.glob("*.json")))
shots = [f"S{i:02}" for i in range(1, 17)]
assert [s["shot"] for s in plan["shots"]] == shots
assert [s["shot"] for s in manifest["shots"]] == shots
assert len(records) == 20 and sum(d["calls"] for d in records) == 20
kept = [d for d in records if not d["output"]["deleted"]]
deleted = [d for d in records if d["output"]["deleted"]]
assert len(kept) == 16 and len(deleted) == 4
assert sorted(d["shot"] for d in kept) == shots
for s in plan["shots"]:
    text = (base / f'{s["shot"]}-Midjourney-v001.txt').read_text().strip()
    assert text == s["midjourneyPrompt"].strip()
    assert "--ar 16:9 --v 8.2 --hd --s 150" in text
    assert "--q " not in text and "--sref" not in text
    if s["shot"] in {"S01", "S04", "S05", "S10"}:
        assert "gptImagePrompt" not in s and "gptImagePromptDeleted" in s
        assert not (base / f'{s["shot"]}-GPT-Image-v001.txt').exists()
    else:
        assert (base / f'{s["shot"]}-GPT-Image-v001.txt').read_text().strip() == s["gptImagePrompt"].strip()
checks["independentMidjourneyPrompts"] = 16
checks["retainedInitialGptPrompts"] = 12
checks["deletedFailedGptPrompts"] = 4
known_deleted = {d["output"]["original"] for d in deleted}
for d in deleted:
    assert not Path(d["output"]["original"]).exists()
    assert not d["output"].get("project")
checks["deletedFailedImages"] = 4
image_bytes = 0
sizes = set()
historical_deleted_refs = 0
for d in records:
    prep = json.loads((base / f'{d["shot"]}-调用准备-{d["version"]}.json').read_text())
    if d["output"]["deleted"]:
        assert "actualInput" not in prep and "actualInput" not in d
        continue
    assert prep["actualInput"] == d["actualInput"]
    assert prep["status"] == "已有返回，已归档"
    for ref in d["actualInput"].get("referenced_image_paths", []):
        if ref in known_deleted:
            historical_deleted_refs += 1
        else:
            assert Path(ref).is_file(), "missing live reference"
    if d["output"]["deleted"]:
        continue
    out = d["output"]
    data = Path(out["project"]).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    size = struct.unpack(">II", data[16:24])
    assert size == (out["width"], out["height"]) == (1672, 941)
    assert len(data) == out["bytes"]
    assert data == Path(out["original"]).read_bytes()
    assert not out["native4k"] and not out["exact16to9"]
    assert d["userAdoption"] == "待用户决定"
    sizes.add(size)
    image_bytes += len(data)
checks["retainedPngFilesAndExactCopyComparison"] = 16
checks["actualPixels"] = [list(s) for s in sorted(sizes)]
checks["historicalReferencesToSubsequentlyDeletedFailures"] = historical_deleted_refs
checks["retainedCandidateActualInputsAndPreparedRecords"] = 16
checks["failureBriefRecordsWithoutPrompts"] = 4
broken_links = []
links_checked = 0
for p in base.glob("*.md"):
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", p.read_text()):
        target = target.strip("<>")
        if "://" in target or target.startswith("#"):
            continue
        path = target.split("#", 1)[0]
        if not path:
            continue
        links_checked += 1
        if not (p.parent / path).exists():
            broken_links.append((p.name, target))
assert not broken_links, broken_links
checks["localMarkdownLinks"] = links_checked
credential_patterns = [r"sk-[A-Za-z0-9_-]{20,}", r"Bearer\s+[A-Za-z0-9._-]{20,}", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
credential_hits = 0
for p in base.iterdir():
    if p.suffix in {".md", ".txt", ".json"} and p.name != "核验记录.json":
        content = p.read_text()
        credential_hits += sum(len(re.findall(pattern, content)) for pattern in credential_patterns)
assert credential_hits == 0
checks["credentialPatternHits"] = credential_hits
repo = next(p for p in base.parents if (p / ".git").exists())
status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", str(base)], cwd=repo, capture_output=True, text=True, check=True)
asset_paths = [d["output"]["project"] for d in kept]
ignored = subprocess.run(["git", "check-ignore", "--", *asset_paths], cwd=repo, capture_output=True, text=True)
assert ignored.returncode == 0 and len(ignored.stdout.splitlines()) == 16
checks["mediaFilesIgnoredByGit"] = 16
checks["gitStatusScopeEntries"] = len(status.stdout.splitlines())
report = {
    "verifiedAtUtc": datetime.now(timezone.utc).isoformat(),
    "command": f'python3 "{base / "核验交付.py"}"',
    "checks": checks,
    "retainedImageBytes": image_bytes,
    "sha256": "按项目规则未额外计算；归档复制使用完整字节比较核验",
    "result": "文件、记录与链接核验通过；不等于原生4K、审美、史实复原或视频连续性通过",
    "remaining": ["原生3840×2160未达到", "实际模型与质量档未知", "纹理密度、光色与人物尺度仍需用户审阅", "Midjourney提示词待用户试图", "用户未决定采用；视频未生成或提交"],
    "scope": "核验只读本轮文件及Git忽略状态；输出本记录。未改代码，无代码测试需求。本轮仅公开研究与已授权内置生图；未安装依赖、读取密钥、上传至MJ、写看板采用、覆盖旧媒体、提交或推送Git。"
}
(base / "核验记录.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
