import os
import re
import json


# ---------- 文件读写辅助函数 ----------
def load_personas_from_file(fp):
    """从 JSON 文件加载 personas 列表，若文件不存在则返回空列表"""
    if os.path.exists(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_personas_to_file(personas_list, fp):
    """将 personas 列表写入 JSON 文件"""
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(personas_list, f, ensure_ascii=False, indent=2)


def parse_json_from_text(text):
    """从模型回复中解析 JSON，兼容 markdown 代码块包裹"""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except Exception:
        return None
