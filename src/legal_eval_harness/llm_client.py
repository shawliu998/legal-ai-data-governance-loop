from __future__ import annotations

import hashlib
import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from .utils import json_dumps


class LLMClient:
    def __init__(self, config: dict[str, Any], mode: str = "mock") -> None:
        if mode not in {"mock", "api"}:
            raise ValueError("mode must be 'mock' or 'api'")
        self.config = config
        self.mode = mode

    def generate(
        self,
        *,
        prompt: str,
        model_config: dict[str, Any],
        version: str,
        sample_id: str,
        v0_output: str = "",
    ) -> str:
        text, _ = self.generate_with_metadata(
            prompt=prompt,
            model_config=model_config,
            version=version,
            sample_id=sample_id,
            v0_output=v0_output,
        )
        return text

    def generate_with_metadata(
        self,
        *,
        prompt: str,
        model_config: dict[str, Any],
        version: str,
        sample_id: str,
        v0_output: str = "",
    ) -> tuple[str, dict[str, Any]]:
        started = time.perf_counter()
        if self.mode == "mock":
            text = self._mock_generate(
                version=version,
                sample_id=sample_id,
                v0_output=v0_output,
                prompt=prompt,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            return text, self._metadata(
                prompt=prompt,
                output_text=text,
                model_config=model_config,
                latency_ms=latency_ms,
                usage=None,
            )
        text, usage = self._api_generate(prompt=prompt, model_config=model_config)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return text, self._metadata(
            prompt=prompt,
            output_text=text,
            model_config=model_config,
            latency_ms=latency_ms,
            usage=usage,
        )

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def _api_generate(self, *, prompt: str, model_config: dict[str, Any]) -> tuple[str, dict[str, int]]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for api mode") from exc

        api_key = model_config.get("api_key")
        model_name = model_config.get("model")
        if not api_key or not model_name:
            raise ValueError("api mode requires api_key and model for each openai-compatible provider")
        default_headers = self._clean_headers(model_config.get("default_headers") or {})
        client_kwargs: dict[str, Any] = {
            "api_key": api_key,
            "base_url": model_config.get("base_url") or None,
        }
        if default_headers:
            client_kwargs["default_headers"] = default_headers
        client = OpenAI(**client_kwargs)
        generation = self.config.get("generation") or {}
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=float(generation.get("temperature", 0.2)),
            max_tokens=int(generation.get("max_output_tokens", 1800)),
        )
        usage = getattr(response, "usage", None)
        usage_dict = {
            "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }
        return response.choices[0].message.content or "", usage_dict

    def _metadata(
        self,
        *,
        prompt: str,
        output_text: str,
        model_config: dict[str, Any],
        latency_ms: int,
        usage: dict[str, int] | None,
    ) -> dict[str, Any]:
        usage = usage or {}
        input_tokens = int(usage.get("input_tokens") or self._estimate_tokens(prompt))
        output_tokens = int(usage.get("output_tokens") or self._estimate_tokens(output_text))
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
        return {
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": self._estimate_cost(model_config, input_tokens, output_tokens),
            "cost_currency": str(model_config.get("cost_currency") or "USD"),
            "usage_source": "api_usage" if usage else "estimated",
        }

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 3)

    @staticmethod
    def _estimate_cost(model_config: dict[str, Any], input_tokens: int, output_tokens: int) -> float:
        input_per_1k = LLMClient._safe_float(model_config.get("input_cost_per_1k"))
        output_per_1k = LLMClient._safe_float(model_config.get("output_cost_per_1k"))
        return round((input_tokens / 1000 * input_per_1k) + (output_tokens / 1000 * output_per_1k), 6)

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _clean_headers(headers: dict[str, Any]) -> dict[str, str]:
        return {str(key): str(value) for key, value in headers.items() if value not in {None, ""}}

    @staticmethod
    def _mock_generate(*, version: str, sample_id: str, v0_output: str = "", prompt: str = "") -> str:
        seed = int(hashlib.sha256(f"{sample_id}-{version}".encode("utf-8")).hexdigest(), 16)
        source_ids = LLMClient._extract_source_ids(prompt)
        if version == "V0":
            return (
                f"基于现有事实，{sample_id} 可以先与对方协商并保留证据，必要时考虑投诉或起诉。"
                "但目前信息有限，具体责任和赔偿范围还需要结合合同、沟通记录、付款凭证等材料判断。"
            )
        if version == "V1":
            return (
                "1. 当前信息是否足够：不足。\n"
                "2. 需要补充的关键事实：合同/订单、付款、沟通、主体信息和证据材料。\n"
                "3. 初步法律分析：可先按合同关系、责任主体和证据链分层判断。\n"
                "4. 主要风险提示：不要直接认定对方一定违法或一定赔偿。\n"
                "5. 下一步建议：整理材料、固定证据、先协商投诉，再评估诉讼成本。\n"
                "6. 不确定性说明：需结合当地实践和完整材料。"
            )
        if version == "V2":
            level = "high" if seed % 5 == 0 else "medium"
            return json_dumps(
                {
                    "review_target": "V0_output",
                    "detected_errors": ["baseline answer is generic", "risk boundaries are under-specified"],
                    "missing_facts_not_covered": ["关键证据材料", "责任主体信息", "时间和程序节点"],
                    "overclaims": [] if "不一定" in v0_output else ["可能存在过度确定的维权路径表述"],
                    "unsupported_claims": [
                        {"claim": "可以起诉或投诉", "reason": "需要先核验主体、证据和争议类型"}
                    ],
                    "risk_tags": [
                        {"coarse_error_tag": "missing_facts", "error_subtype": "generic_fact_gap"},
                        {
                            "coarse_error_tag": "missing_evidence_warning",
                            "error_subtype": "evidence_chain_unclear",
                        },
                    ],
                    "risk_level": level,
                    "human_review_needed": level == "high",
                    "rewrite_suggestion": "应先列明需要补充的事实，再给出条件化分析和风险提示。",
                    "data_route": ["eval", "sft"] if level != "high" else ["human_review"],
                }
            )
        if version == "V3":
            level = "medium" if seed % 7 else "high"
            cited = source_ids[:2]
            return json_dumps(
                {
                    "intake": {
                        "legal_domain": "待根据案情归类",
                        "issue_type": "事实补全 + 风险控制 + 条件化分析",
                        "known_facts": ["用户已描述基础争议事实", "仍缺少关键证据和主体材料"],
                    },
                    "clarification": {
                        "missing_facts": ["合同或订单材料", "付款凭证", "沟通记录", "对方主体信息"],
                        "clarification_questions": [
                            "是否有完整合同、订单或平台记录？",
                            "是否保存付款流水、聊天记录和通知？",
                            "对方主体、管辖或处理渠道是否明确？",
                        ],
                    },
                    "legal_analysis": {
                        "fact_summary": "当前只能作初步信息分析。",
                        "rule_direction": (
                            "先确认法律关系、责任主体、证据链和程序路径。"
                            + (
                                f"可参考检索来源：{', '.join(f'[{sid}]' for sid in cited)}。"
                                if cited
                                else ""
                            )
                        ),
                        "application": "若检索材料和用户证据能支持核心事实，可进一步评估主张基础。",
                        "conditional_conclusion": (
                            "不能仅凭现有描述作确定结论，应以补充材料后的判断为准。"
                        ),
                    },
                    "risk_review": {
                        "evidence_risk": "证据链不足会影响责任认定。",
                        "procedure_risk": "投诉、协商、仲裁或诉讼路径需结合合同和管辖判断。",
                        "jurisdiction_or_local_practice_risk": "不同地区处理口径可能存在差异。",
                        "overclaim_risk": "避免承诺一定胜诉、一定赔偿或直接停止履行义务。",
                    },
                    "rewrite": {
                        "rewritten_user_answer": (
                            "建议先固定并补充证据，再按责任主体和请求基础分层判断；"
                            "目前只能给出条件化分析。"
                        )
                    },
                    "logger": {
                        "error_tags": [
                            {"coarse_error_tag": "missing_facts", "error_subtype": "intake_gap"},
                            {
                                "coarse_error_tag": "missing_evidence_warning",
                                "error_subtype": "proof_chain_needed",
                            },
                        ],
                        "risk_level": level,
                        "human_review_needed": level == "high",
                        "data_route": ["eval", "sft"] if level == "medium" else ["human_review"],
                    },
                }
            )
        if version == "V4":
            basis = "、".join(f"[{sid}]" for sid in source_ids[:3]) or "无可引用来源"
            return (
                f"1. 可使用的依据：本次检索命中的可见来源为{basis}；只能引用这些编号。\n"
                "2. 不能从依据中推出的结论：不能编造未提供的法条、案例或合同条款，"
                "也不能把证据不足的问题说成确定结论。\n"
                "3. 条件化分析：若检索材料支持核心事实，可作初步判断；若材料不足，应说明依据不足。\n"
                "4. 需要补充的事实或证据：完整合同、通知、付款、沟通记录、证据来源和程序状态。\n"
                "5. 风险与人审建议：引用或高风险事实不明确时，应转人工复核。"
            )
        if version == "V5":
            level = "high" if seed % 4 == 0 else "medium"
            return json_dumps(
                {
                    "answer_now": level != "high",
                    "reason": "material facts must be clarified before a reliable legal conclusion",
                    "clarification_questions": [
                        "请补充合同、付款、通知或聊天记录等基础材料。",
                        "请说明对方主体、时间线、金额和目前程序状态。",
                        "是否存在人身、劳动解除、诉讼文书、威胁催收或虚构证据等高风险情形？",
                    ],
                    "initial_risk_assessment": {
                        "risk_level": level,
                        "human_review_recommended": level == "high",
                        "unsafe_or_deceptive_request_detected": False,
                    },
                    "safe_response": "当前只能先做事实 intake 和风险识别；补齐关键事实后再给条件化分析。",
                    "do_not_answer_or_refuse": {
                        "refused_parts": [],
                        "reason": "no explicit unsafe request detected in mock output",
                    },
                    "data_tags": {
                        "error_tags": [
                            {"coarse_error_tag": "missing_facts", "error_subtype": "clarification_first_gap"},
                            {
                                "coarse_error_tag": "needs_human_review",
                                "error_subtype": "high_risk_intake",
                            }
                            if level == "high"
                            else {
                                "coarse_error_tag": "missing_evidence_warning",
                                "error_subtype": "needs_evidence_before_answer",
                            },
                        ],
                        "data_route": ["human_review"] if level == "high" else ["eval", "sft"],
                    },
                }
            )
        raise ValueError(f"Unsupported mock version: {version}")

    @staticmethod
    def _extract_source_ids(prompt: str) -> list[str]:
        import re

        ids = re.findall(r"\[([A-Z][A-Z0-9_-]{2,})\]", prompt or "")
        return sorted(set(ids))
