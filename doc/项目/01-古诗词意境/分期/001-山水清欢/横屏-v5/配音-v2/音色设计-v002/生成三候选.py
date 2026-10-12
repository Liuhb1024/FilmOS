"""Bounded local API orchestration; exactly three sequential auditions, no retry."""
import json
import re
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").is_file())
ASSETS = ROOT / "doc/项目/01-古诗词意境/资产库/001-山水清欢/配音-v2/音色设计-v002"
RECORD = HERE / "实际调用与文件核验.json"
ENDPOINT = "http://127.0.0.1:3000/api/speech/design"


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("local_redirect_rejected")


def main():
    if RECORD.exists():
        raise RuntimeError("existing_run_rejected_no_resubmission")
    tasks = json.loads((HERE / "三候选任务.json").read_text())
    assert [t["candidate"] for t in tasks] == [4, 5, 6]
    for task in tasks:
        source = Path(task["input_file"])
        assert source.parent == HERE
        data = json.loads(source.read_text())
        assert set(data) == {"prompt", "preview_text", "aigc_watermark"}
        assert data["prompt"].strip() and 0 < len(data["preview_text"]) <= 500
        assert data["aigc_watermark"] is False
        assert sum("\u4e00" <= c <= "\u9fff" for c in data["preview_text"]) == 104
        assert not (ASSETS / f"云起时-音色候选-{task['candidate']:02d}.mp3").exists()
    # The local service must never be routed through environment HTTP proxies.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open("http://127.0.0.1:3000/speech", timeout=15) as response:
        assert response.status == 200
    record = {
        "started_at": now(), "scope": "three distinct prompts, sequential, no retry",
        "local_endpoint": ENDPOINT,
        "provider_endpoint": "https://api.minimax.cn/v1/voice_design",
        "model": "未知，设计接口未公开或返回", "quality": "接口无设置字段",
        "seed": "未知", "reference_audio_submitted": False,
        "formal_tts_calls": 0, "new_voice_first_use_activation": False,
        "estimated_preview_billing_characters_per_call": 246,
        "estimated_cost_total_yuan_for_three": 0.1476, "actual_bill": "未知",
        "candidates": [],
    }
    write_json(RECORD, record)
    for task in tasks:
        number = task["candidate"]
        item = {**task, "submitted_at": now(), "state": "submitting"}
        record["candidates"].append(item)
        write_json(RECORD, record)
        print(f"候选 {number:02d} {task['direction']}：提交一次音色设计", flush=True)
        try:
            body = Path(task["input_file"]).read_bytes()
            request = urllib.request.Request(
                ENDPOINT, data=body, method="POST",
                headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:3000"},
            )
            with opener.open(request, timeout=390) as response:
                item["local_http_status"] = response.status
                raw = response.read(32 * 1024 * 1024 + 1)
            if len(raw) > 32 * 1024 * 1024:
                raise RuntimeError("oversized_response")
            result = json.loads(raw)
            voice_id = result.get("voiceId")
            assert isinstance(voice_id, str) and voice_id.strip() and len(voice_id) <= 1024
            assert not re.search(r"[\x00-\x1f]", voice_id)
            hex_audio = result.get("hex")
            assert isinstance(hex_audio, str) and len(hex_audio) % 2 == 0
            assert re.fullmatch(r"[a-fA-F0-9]+", hex_audio)
            fmt = result.get("format")
            assert fmt in {"mp3", "wav", "flac", "ogg"}
            audio = bytes.fromhex(hex_audio)
            target = ASSETS / f"云起时-音色候选-{number:02d}.{fmt}"
            with target.open("xb") as handle:
                handle.write(audio)
            item.update(state="saved", voice_id=voice_id, actual_format=fmt,
                        file=str(target), bytes=len(audio), returned_at=now(),
                        hex_character_count=len(hex_audio))
            metadata = {k: v for k, v in result.items() if k != "hex"}
            metadata.update(original_audio_file=str(target), hex_saved_as_original_bytes=True)
            write_json(HERE / f"候选-{number:02d}-实际返回元数据.json", metadata)
            write_json(HERE / f"候选-{number:02d}-音色信息.json", {
                "provider": "MiniMax", "voice_id": voice_id,
                **json.loads(body), "original_audio_file": str(target),
            })
            write_json(RECORD, record)
            probe = subprocess.run([
                "/opt/homebrew/bin/ffprobe", "-v", "error", "-show_format", "-show_streams",
                "-of", "json", str(target),
            ], capture_output=True, text=True, check=True)
            details = json.loads(probe.stdout)
            write_json(HERE / f"候选-{number:02d}-ffprobe.json", details)
            stream = next(s for s in details["streams"] if s["codec_type"] == "audio")
            decode = subprocess.run([
                "/opt/homebrew/bin/ffmpeg", "-v", "error", "-i", str(target), "-f", "null", "-",
            ], capture_output=True, text=True)
            item.update(duration_seconds=float(details["format"]["duration"]),
                        codec=stream["codec_name"], sample_rate=stream["sample_rate"],
                        channels=stream["channels"], decode_exit_code=decode.returncode,
                        decode_errors=decode.stderr)
            assert decode.returncode == 0 and not decode.stderr.strip()
            write_json(RECORD, record)
            print(f"候选 {number:02d} 原始音频已存盘，{item['duration_seconds']:.3f} 秒，完整解码成功", flush=True)
        except Exception as error:
            item.update(state="stopped_after_error_no_retry", failure_type=type(error).__name__)
            record["stopped_at"] = now()
            record["unresolved_call_warning"] = "失败或超时可能已计费，不重试；已存盘结果仍保留"
            write_json(RECORD, record)
            print(f"候选 {number:02d} 停止：{type(error).__name__}，未重试", flush=True)
            return 1
    assert len({x["voice_id"] for x in record["candidates"]}) == 3
    record.update(finished_at=now(), successful_candidates=3,
                  listening_review="未主观核验，待用户试听比较")
    write_json(RECORD, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
