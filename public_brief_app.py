from __future__ import annotations

import json
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = APP_DIR / "public_form_schema.json"


def _secret(name: str, default: Any = "") -> Any:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _config() -> dict[str, Any]:
    return {
        "supabase_url": str(_secret("SUPABASE_URL", "") or "").rstrip("/"),
        "anon_key": str(_secret("SUPABASE_ANON_KEY", "") or ""),
        "smtp_host": str(_secret("SMTP_HOST", "") or ""),
        "smtp_port": int(_secret("SMTP_PORT", 587) or 587),
        "smtp_username": str(_secret("SMTP_USERNAME", "") or ""),
        "smtp_password": str(_secret("SMTP_PASSWORD", "") or ""),
        "smtp_from": str(_secret("SMTP_FROM", "") or ""),
        "notify_to": str(_secret("NOTIFY_TO", "") or ""),
    }


def _headers(config: dict[str, Any]) -> dict[str, str]:
    key = config["anon_key"]
    if not config["supabase_url"] or not key:
        raise RuntimeError("公网表单尚未配置 Supabase。")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _rpc(config: dict[str, Any], name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = requests.post(
        f"{config['supabase_url']}/rest/v1/rpc/{name}",
        headers=_headers(config),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _load_schema() -> dict[str, Any]:
    try:
        value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        value = {}
    return value if isinstance(value, dict) else {}


def _query_param(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return str(value[0] if value else "")
    return str(value or "")


def _load_record(config: dict[str, Any], record_id: str, token: str) -> dict[str, Any] | None:
    rows = _rpc(
        config,
        "get_public_brief_submission",
        {"p_id": record_id, "p_access_token": token},
    )
    return rows[0] if rows else None


def _save_record(config: dict[str, Any], record_id: str, token: str, brief: dict[str, Any]) -> dict[str, Any] | None:
    rows = _rpc(
        config,
        "save_public_brief_submission",
        {"p_id": record_id, "p_access_token": token, "p_brief": brief},
    )
    return rows[0] if rows else None


def _submit_record(config: dict[str, Any], record_id: str, token: str, brief: dict[str, Any]) -> dict[str, Any] | None:
    rows = _rpc(
        config,
        "submit_public_brief_submission",
        {"p_id": record_id, "p_access_token": token, "p_brief": brief},
    )
    return rows[0] if rows else None


def _send_notification(config: dict[str, Any], record: dict[str, Any]) -> None:
    if not (config["smtp_host"] and config["smtp_from"] and config["notify_to"]):
        return
    brief = record.get("brief") if isinstance(record.get("brief"), dict) else {}
    project = brief.get("project_name") or brief.get("product") or "未命名项目"
    contact = brief.get("contact") or record.get("client_email") or "未填写"
    submitted_at = record.get("submitted_at") or record.get("updated_at") or ""
    msg = EmailMessage()
    msg["Subject"] = f"客户需求表单已提交：{project}"
    msg["From"] = config["smtp_from"]
    msg["To"] = config["notify_to"]
    msg.set_content(
        "\n".join([
            f"项目：{project}",
            f"客户/联系方式：{contact}",
            f"提交时间：{submitted_at}",
            "",
            "请回到小快乐工作室点击“同步客户反馈”。",
        ])
    )
    with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=20) as smtp:
        smtp.starttls()
        if config["smtp_username"] and config["smtp_password"]:
            smtp.login(config["smtp_username"], config["smtp_password"])
        smtp.send_message(msg)


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def _duration_seconds(value: str) -> int:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits or 30)


def _date_value(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _seed_state(brief: dict[str, Any]) -> None:
    constraints = brief.get("constraints") if isinstance(brief.get("constraints"), dict) else {}
    defaults = {
        "project_name": brief.get("project_name", ""),
        "client_name": brief.get("client_name", ""),
        "contact": brief.get("contact", ""),
        "product": brief.get("product", ""),
        "product_description": brief.get("product_description", ""),
        "video_goal": brief.get("video_goal", ""),
        "platforms": _as_list(constraints.get("platforms")),
        "duration_choice": f"{int(constraints.get('duration') or 30)}秒",
        "video_type": brief.get("video_type", ""),
        "visual_styles": _as_list(brief.get("visual_styles")),
        "emotion_goals": _as_list(brief.get("emotion_goals")),
        "audience_segments": _as_list(brief.get("audience_segments")),
        "audience_stage": brief.get("audience_stage", ""),
        "call_to_action": _as_list(constraints.get("call_to_actions") or brief.get("call_to_action")),
        "product_category": _as_list(constraints.get("product_categories") or brief.get("product_category")),
        "selling_point_categories": _as_list(brief.get("selling_point_categories")),
        "pain_point_categories": _as_list(brief.get("pain_point_categories")),
        "language": brief.get("language", ""),
        "people_mode": brief.get("people_mode", ""),
        "asset_readiness": brief.get("asset_readiness", ""),
        "deadline_date": _date_value(brief.get("deadline")),
        "reference_links": brief.get("reference_links", ""),
        "must_include": brief.get("must_include", ""),
        "banned_words": constraints.get("banned_words", ""),
        "client_notes": brief.get("client_notes", ""),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _options(schema: dict[str, Any], key: str) -> list[str]:
    values = schema.get("options", {}).get(key, [])
    return [str(item) for item in values] if isinstance(values, list) else []


def _options_with_current(schema: dict[str, Any], option_key: str, state_key: str, *, blank: bool = False) -> list[str]:
    result = [""] if blank else []
    for item in _options(schema, option_key):
        if item not in result:
            result.append(item)
    for item in _as_list(st.session_state.get(state_key)):
        if item and item not in result:
            result.append(item)
    return result


def _brief_from_state() -> dict[str, Any]:
    duration_choice = st.session_state.get("duration_choice", "30秒")
    return {
        "schema_version": 2,
        "project_name": str(st.session_state.get("project_name") or "").strip(),
        "client_name": str(st.session_state.get("client_name") or "").strip(),
        "contact": str(st.session_state.get("contact") or "").strip(),
        "product": str(st.session_state.get("product") or "").strip(),
        "product_description": str(st.session_state.get("product_description") or "").strip(),
        "video_goal": str(st.session_state.get("video_goal") or "").strip(),
        "video_type": str(st.session_state.get("video_type") or "").strip(),
        "visual_styles": _as_list(st.session_state.get("visual_styles")),
        "emotion_goals": _as_list(st.session_state.get("emotion_goals")),
        "audience_segments": _as_list(st.session_state.get("audience_segments")),
        "audience_stage": str(st.session_state.get("audience_stage") or "").strip(),
        "call_to_action": "、".join(_as_list(st.session_state.get("call_to_action"))),
        "product_category": "、".join(_as_list(st.session_state.get("product_category"))),
        "selling_point_categories": _as_list(st.session_state.get("selling_point_categories")),
        "pain_point_categories": _as_list(st.session_state.get("pain_point_categories")),
        "language": str(st.session_state.get("language") or "").strip(),
        "people_mode": str(st.session_state.get("people_mode") or "").strip(),
        "asset_readiness": str(st.session_state.get("asset_readiness") or "").strip(),
        "deadline": str(st.session_state.get("deadline_date") or "").strip(),
        "reference_links": str(st.session_state.get("reference_links") or "").strip(),
        "must_include": str(st.session_state.get("must_include") or "").strip(),
        "client_notes": str(st.session_state.get("client_notes") or "").strip(),
        "constraints": {
            "platforms": _as_list(st.session_state.get("platforms")),
            "duration": _duration_seconds(str(duration_choice)),
            "banned_words": str(st.session_state.get("banned_words") or "").strip(),
            "call_to_actions": _as_list(st.session_state.get("call_to_action")),
            "product_categories": _as_list(st.session_state.get("product_category")),
        },
    }


def _validate(brief: dict[str, Any]) -> list[str]:
    required = {
        "品牌、产品或服务名称": brief.get("product"),
        "产品介绍和具体卖点": brief.get("product_description"),
        "联系方式": brief.get("contact"),
        "希望交付日期": brief.get("deadline"),
    }
    return [f"请填写“{label}”" for label, value in required.items() if not value]


def main() -> None:
    st.set_page_config(page_title="AI视频项目需求表", page_icon="📝", layout="centered")
    config = _config()
    schema = _load_schema()
    record_id = _query_param("brief_form")
    token = _query_param("token")
    st.title(schema.get("title") or "AI视频项目需求表")
    if not record_id or not token:
        st.error("链接缺少必要参数，请确认你打开的是完整客户表单链接。")
        return
    try:
        record = _load_record(config, record_id, token)
    except Exception as exc:
        st.error(f"表单加载失败：{exc}")
        return
    if not record:
        st.error("链接无效或表单不存在。")
        return
    if record.get("status") not in {"DRAFT", "NEEDS_CHANGES"}:
        st.success("需求已经提交，我们会在制作前进行确认。")
        return

    brief = record.get("brief") if isinstance(record.get("brief"), dict) else {}
    _seed_state(brief)
    st.caption("请按真实想法填写。可以先保存草稿，确认无误后再提交。")
    with st.form("public_brief_form"):
        st.subheader("视频方向")
        c1, c2 = st.columns(2)
        c1.selectbox("视频目标", _options_with_current(schema, "video_goal", "video_goal", blank=True), key="video_goal")
        c2.selectbox("视频类型", _options_with_current(schema, "video_type", "video_type", blank=True), key="video_type")
        st.multiselect("发布平台", _options_with_current(schema, "platforms", "platforms"), key="platforms")
        st.selectbox("最终成片时长", _options_with_current(schema, "duration_choice", "duration_choice"), key="duration_choice")

        st.subheader("创意感觉")
        st.multiselect("视觉感觉", _options_with_current(schema, "visual_styles", "visual_styles"), key="visual_styles")
        st.multiselect("希望观众产生的感受", _options_with_current(schema, "emotion_goals", "emotion_goals"), key="emotion_goals")

        st.subheader("受众与行动")
        st.multiselect("这条视频主要是给谁看的？", _options_with_current(schema, "audience_segments", "audience_segments"), key="audience_segments")
        st.selectbox("目标受众当前阶段", _options_with_current(schema, "audience_stage", "audience_stage", blank=True), key="audience_stage")
        st.multiselect("希望观众看完以后做什么？", _options_with_current(schema, "call_to_action", "call_to_action"), key="call_to_action")

        st.subheader("产品与优势")
        st.multiselect("产品或服务属于哪个行业？", _options_with_current(schema, "product_category", "product_category"), key="product_category")
        st.multiselect("最想强调哪些优势？", _options_with_current(schema, "selling_point_categories", "selling_point_categories"), key="selling_point_categories")
        st.multiselect("目标受众通常遇到哪些问题？", _options_with_current(schema, "pain_point_categories", "pain_point_categories"), key="pain_point_categories")
        st.text_input("品牌、产品或服务名称 *", key="product")
        st.text_area("产品介绍和具体卖点 *", height=120, key="product_description")

        st.subheader("制作信息")
        c1, c2 = st.columns(2)
        c1.selectbox("视频语言", _options_with_current(schema, "language", "language", blank=True), key="language")
        c2.selectbox("人物呈现方式", _options_with_current(schema, "people_mode", "people_mode", blank=True), key="people_mode")
        c1.selectbox("素材准备情况", _options_with_current(schema, "asset_readiness", "asset_readiness", blank=True), key="asset_readiness")
        c2.date_input("希望交付日期 *", value=None, key="deadline_date")
        st.text_input("联系方式 *", key="contact")
        st.text_input("怎么称呼你", key="client_name")
        st.text_area("参考视频或参考链接", height=80, key="reference_links")
        st.text_area("必须出现的内容", height=70, key="must_include")
        st.text_area("禁止出现的内容", height=70, key="banned_words")
        st.text_area("其他补充备注", height=90, key="client_notes")

        save_clicked = st.form_submit_button("保存草稿", use_container_width=True)
        submit_clicked = st.form_submit_button("确认并提交", type="primary", use_container_width=True)

    brief_data = _brief_from_state()
    if isinstance(brief_data.get("deadline"), date):
        brief_data["deadline"] = brief_data["deadline"].isoformat()
    errors = _validate(brief_data)
    if save_clicked:
        try:
            _save_record(config, record_id, token, brief_data)
        except Exception as exc:
            st.error(f"保存失败：{exc}")
        else:
            st.success("草稿已保存。")
    if submit_clicked:
        if errors:
            st.error("请先完成这些内容：\n\n- " + "\n- ".join(errors))
            return
        try:
            submitted = _submit_record(config, record_id, token, brief_data)
            if submitted:
                _send_notification(config, submitted)
        except Exception as exc:
            st.error(f"提交失败：{exc}")
        else:
            st.success("需求已提交，谢谢。")


if __name__ == "__main__":
    main()
