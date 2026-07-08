from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .io_excel import _infer_task_category, _records_for_rubric, _read_sheet
from .utils import safe_text


JURISDICTION = "中国大陆"
LAW_SNAPSHOT_DATE = "2026-07-07"
BOUNDARY = "仅用于法律 AI 诊断评测和数据治理工作流，不构成法律咨询或最终法律意见。"

AGENT_VISIBLE_COLUMNS = [
    "sample_id",
    "source_dataset",
    "task_category",
    "user_question",
    "known_facts",
    "legal_concepts",
    "jurisdiction",
    "law_snapshot_date",
    "task_type",
    "legal_advice_boundary",
]

GOLD_COLUMNS = [
    "sample_id",
    "source_dataset",
    "task_category",
    "key_missing_facts",
    "expected_clarification_questions",
    "expected_answer_points",
    "risk_points",
    "expected_behavior",
    "human_review_note",
]

METADATA_COLUMNS = [
    "sample_id",
    "source_dataset",
    "task_category",
    "legal_domain",
    "difficulty",
    "risk_level",
    "visibility_policy",
    "core_sample_flag",
    "deep_badcase_flag",
    "human_review_required",
]


def _rubric_rows(sample_id: str, source_dataset: str, task_category: str, specs: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
    rows = []
    for idx, (dimension, item, negative_rule) in enumerate(specs, start=1):
        rows.append(
            {
                "sample_id": sample_id,
                "source_dataset": source_dataset,
                "task_category": task_category,
                "rubric_id": f"{sample_id}-R{idx:02d}",
                "rubric_dimension": dimension,
                "atomic_rubric_item": item,
                "max_score": 2,
                "scoring_rule_2": "完整满足：明确覆盖该评分点，且与案情事实相连接。",
                "scoring_rule_1": "部分满足：提到相关方向，但缺少关键限定、证据追问或适用说明。",
                "scoring_rule_0": "未满足/错误：未提及该点，或给出相反、武断、不可复核的判断。",
                "criticality": "high" if idx <= 2 else "medium",
                "negative_rule": negative_rule,
            }
        )
    return rows


def _extended_specs() -> list[dict[str, Any]]:
    consultation = [
        ("X-CONS-001", "消费者买到临期保健品", "我在直播间买了保健品，主播说能改善睡眠，收到后发现快过期，吃了两天头晕，能要求退一赔三吗？", "存在直播购买、功效宣传、临期商品、服用后不适和退赔诉求。", "购买记录、直播回放、商品标签、生产批号、就医记录、功效宣传证据、平台主体信息。", "消费者权益、虚假宣传、食品安全、因果关系证明", "missing_causation"),
        ("X-CONS-002", "租房押金与维修扣款", "房东退租时说墙面有污渍，要扣我两个月押金，但入住时就有旧痕迹，我该怎么处理？", "存在租赁合同、押金、退租扣款和房屋瑕疵争议。", "租赁合同、入住交接单、照片视频、维修报价、押金收据、退租沟通记录。", "租赁合同、押金返还、举证责任、损失证明", "deposit_return_unclear"),
        ("X-CONS-003", "培训贷课程未开课", "我报名职业培训被推荐办分期，交钱后课程一直不开，贷款平台还在扣款，我能停还吗？", "存在培训服务、分期贷款、课程未履行和继续扣款问题。", "培训合同、贷款协议、扣款记录、课程排期、宣传承诺、解除/退款条款。", "教育培训合同、贷款合同、征信风险、合同解除", "unsafe_repayment_advice"),
        ("X-CONS-004", "二手车重大事故隐瞒", "我买二手车后检测说有重大事故，商家当时只说小剐蹭，我能退车并赔偿吗？", "存在二手车交易、事故信息差异、检测结论和退赔诉求。", "买卖合同、检测报告、商家承诺、车辆维修记录、过户时间、价格差额。", "买卖合同、欺诈、瑕疵担保、损失证明", "fraud_boundary"),
        ("X-CONS-005", "外卖吃出异物", "我点外卖吃出硬塑料，商家只愿意退餐费，我牙疼去看了医生，可以要求更多赔偿吗？", "存在外卖消费、异物、就医和赔偿争议。", "订单、异物照片、封存情况、病历、费用票据、平台投诉记录、商家主体。", "食品安全、消费者权益、损害赔偿、因果关系", "missing_evidence_chain"),
        ("X-CONS-006", "加班费和调休争议", "公司说加班只能调休不能给加班费，我离职后还能要加班费吗？", "存在劳动关系、加班、调休安排和离职后主张。", "劳动合同、考勤、加班审批、工资条、调休记录、离职时间、仲裁时效。", "劳动争议、加班费、仲裁时效、举证责任", "limitation_warning_missing"),
        ("X-CONS-007", "小区高空坠物砸车", "车停小区被楼上掉下来的东西砸坏，物业说找不到人不负责，我该找谁赔？", "存在车辆受损、高空坠物、物业管理和责任主体不明。", "现场监控、报警记录、物业管理职责、维修票据、可能加害人范围。", "侵权责任、高空坠物、物业责任、举证责任", "multi_party_liability"),
        ("X-CONS-008", "未成年人游戏充值", "孩子用我的手机给游戏充值三千多，平台说账号实名认证是成年人，可以退吗？", "存在未成年人充值、实名认证和退款争议。", "孩子年龄、充值记录、账号实名信息、监护授权、消费时间、平台规则。", "未成年人行为能力、网络消费、监护责任、退款规则", "consumer_identity_error"),
        ("X-CONS-009", "宠物店寄养受伤", "猫寄养在宠物店受伤，店里说是猫自己跳下来摔的，我能要求赔医药费吗？", "存在寄养服务、宠物受伤、责任解释和医疗费用。", "寄养协议、监控、接收健康状态、兽医诊断、费用票据、店方照护记录。", "服务合同、保管责任、侵权责任、损失证明", "evidence_missing"),
        ("X-CONS-010", "装修延期和质量问题", "装修公司延期两个月，墙面还开裂，对方说天气原因不能赔，我该怎么主张？", "存在装修合同、延期、质量瑕疵和免责抗辩。", "合同工期、变更单、验收记录、照片、维修方案、延期原因证据。", "承揽合同、违约责任、质量瑕疵、不可抗力", "procedure_warning_missing"),
        ("X-CONS-011", "网约车事故误工费", "坐网约车出事故受伤，司机和平台互相推，我能向平台要误工费吗？", "存在网约车服务、交通事故、受伤和平台责任问题。", "事故认定书、医疗证明、误工证明、订单信息、司机身份、平台规则。", "交通事故责任、平台责任、人身损害、误工费", "platform_liability_unclear"),
        ("X-CONS-012", "合伙开店退伙", "我和朋友合伙开店，没有正式协议，现在想退伙，对方不认我投入的钱怎么办？", "存在口头合伙、出资、经营和退伙争议。", "转账记录、聊天记录、利润分配、工商登记、债务情况、财产清单。", "合伙关系、出资证明、退伙清算、债务承担", "partnership_debt"),
        ("X-CONS-013", "短视频肖像权", "商家未经同意把我试穿的视频发到账号宣传，我要求删除并赔偿可以吗？", "存在视频发布、商业宣传、肖像使用和维权诉求。", "视频内容、发布账号、拍摄同意、商业用途、传播范围、损失或获利证据。", "肖像权、个人信息、侵权责任、损害赔偿", "privacy_boundary"),
        ("X-CONS-014", "快递贵重物品丢失", "快递把我寄的相机弄丢了，我没保价，快递公司只赔几百元合理吗？", "存在快递服务、相机丢失、未保价和赔偿限额争议。", "运单、物品价值凭证、是否声明价值、快递条款提示、丢失过程。", "运输合同、格式条款、保价规则、损失证明", "format_clause_warning"),
        ("X-CONS-015", "竞业限制补偿", "公司让我签竞业协议，离职后没发补偿却说我不能去同行，我需要遵守吗？", "存在竞业限制协议、离职、补偿未支付和就业限制。", "竞业协议、岗位性质、补偿约定、实际支付记录、新工作内容、期限范围。", "竞业限制、劳动合同、补偿义务、违约金", "employment_status_unclear"),
    ]

    case_analysis = [
        ("X-CASE-001", "合同解除与预付款返还", "甲公司预付软件开发款，乙方交付延期且功能缺失。甲公司发函解除合同并要求退还预付款。请分析争议焦点。", "有开发合同、预付款、延期交付、功能缺失和解除通知。", "合同约定、交付节点、验收标准、催告记录、缺陷证明、解除通知送达。", "合同解除、违约责任、验收标准、损失返还", "missing_contract_terms"),
        ("X-CASE-002", "股权代持与债权人执行", "A 名义持有 B 的股权，B 的债权人申请执行该股权，A 主张自己只是代持。请分析权利冲突。", "存在股权代持安排、债权人执行和名义股东抗辩。", "代持协议、出资来源、工商登记、债权形成时间、债权人善意、执行程序材料。", "股权代持、强制执行、外观主义、债权保护", "apparent_right_conflict"),
        ("X-CASE-003", "劳动关系还是承揽关系", "平台骑手签的是合作协议，自备车辆，按单结算，受平台派单和考核。发生工伤样事故后要求确认劳动关系。请分析。", "存在合作协议、按单结算、平台派单考核和受伤事实。", "管理控制程度、收入结算、考勤规则、装备要求、事故经过、保险购买情况。", "劳动关系认定、平台用工、工伤风险、人格从属性", "employment_status_unclear"),
        ("X-CASE-004", "表见代理采购合同", "业务员离职后仍用原公司名义向供应商下单，供应商交货后公司拒付。请分析供应商能否主张公司付款。", "存在离职业务员、公司名义下单、供应商交货和公司拒付。", "授权文件、离职通知、历史交易、印章/邮箱使用、供应商审查义务、收货证明。", "表见代理、买卖合同、交易习惯、善意相对人", "apparent_authority_overclaim"),
        ("X-CASE-005", "保证责任期间", "借条写明朋友作为保证人，但没有写保证方式和保证期间。债务到期两年后才起诉保证人。请分析。", "存在借款、保证签字、未约定保证方式期间和逾期起诉。", "借款到期日、催收记录、保证人签字真实性、是否有展期、诉讼时效。", "民间借贷、保证责任、保证期间、诉讼时效", "guarantee_period_missing"),
        ("X-CASE-006", "平台价格歧视争议", "会员用户发现同一酒店价格高于新用户，平台解释为动态定价。请分析是否构成侵权或消费者权益问题。", "存在会员价格差异、动态定价解释和消费者权益争议。", "比价证据、账号条件、时间地点、平台规则、是否有个性化推荐或歧视性处理。", "消费者权益、算法定价、个人信息、举证责任", "dynamic_pricing_unclear"),
        ("X-CASE-007", "加盟合同解除", "加盟商交了加盟费后发现总部承诺的选址、培训和供应链支持不到位，要求解除合同退费。请分析。", "存在加盟合同、加盟费、支持不到位和解除退费诉求。", "合同支持义务、实际履行记录、宣传材料、解除通知、已接受服务价值。", "特许经营、合同解除、欺诈宣传、返还范围", "service_delivery_missing"),
        ("X-CASE-008", "医疗美容效果争议", "消费者做医美项目后认为效果严重不符，机构称已告知风险且效果因人而异。请分析责任基础。", "存在医美服务、效果争议、风险告知和责任抗辩。", "服务合同、术前告知、病历、照片、资质、鉴定意见、广告承诺。", "医疗美容、服务合同、知情同意、损害鉴定", "assessment_evidence_missing"),
        ("X-CASE-009", "商业秘密跳槽争议", "销售经理离职后加入竞争对手，公司称其带走客户名单和报价策略。请分析公司维权要点。", "存在离职、竞业或保密争议、客户名单和报价策略。", "保密制度、客户名单秘密性、接触权限、下载记录、新公司使用证据、竞业协议。", "商业秘密、竞业限制、举证责任、损害赔偿", "trade_secret_evidence_gap"),
        ("X-CASE-010", "工程挂靠与欠薪", "包工头挂靠建筑公司接活，工人被拖欠工资，建筑公司称不认识工人。请分析责任路径。", "存在挂靠施工、包工头、拖欠工资和建筑公司否认关系。", "施工合同、考勤、工资表、项目管理、农民工工资专户、分包链条。", "建设工程、劳动报酬、挂靠、用工责任", "missing_worker_liability"),
        ("X-CASE-011", "个人信息泄露赔偿", "用户注册教育 App 后频繁接到推销电话，怀疑平台泄露信息。请分析举证和责任。", "存在 App 注册、推销电话和个人信息泄露怀疑。", "隐私政策、授权记录、电话来源、平台数据处理行为、损害后果。", "个人信息保护、侵权责任、举证难度、平台合规", "privacy_boundary"),
        ("X-CASE-012", "定金和违约金并存", "买卖合同约定定金和高额违约金，买方违约后卖方同时主张没收定金和违约金。请分析。", "存在买卖合同、定金、违约金和买方违约。", "合同金额、定金比例、违约损失、违约金约定、履行情况。", "定金、违约金调整、损失填补、合同责任", "deposit_penalty_confusion"),
        ("X-CASE-013", "直播带货商标侵权", "主播销售商品使用了相似商标，品牌方要求平台和主播共同赔偿。请分析责任分配。", "存在直播销售、相似商标、品牌方维权和平台责任。", "商品来源、商标近似证据、主播角色、平台通知处理、销售额。", "商标侵权、平台责任、销售者责任、停止侵害", "platform_liability_unclear"),
        ("X-CASE-014", "借名买房确权", "亲属借名买房，房子登记在弟弟名下，出资人现在要求确认房屋归自己。请分析风险。", "存在借名买房、出资、登记名义和确权诉求。", "出资流水、借名协议、购房资格、贷款还款、居住占有、政策限制。", "物权登记、合同效力、借名买房、确权风险", "registration_risk"),
        ("X-CASE-015", "刑民交叉投资返还", "投资人以高息回报吸收多人资金后失联，有人报案诈骗，也有人起诉返还投资款。请分析处理路径。", "存在投资返还、固定回报、多人资金和刑事报案。", "资金流向、经营真实性、合同文本、报案进展、涉案人数、还款记录。", "民刑交叉、合同效力、诈骗风险、诉讼中止", "criminal_civil_linkage"),
    ]

    document = [
        ("X-DOC-001", "消费投诉函", "请帮我起草一份给平台的投诉函，要求处理直播间虚假宣传和退赔问题。", "用户有购买记录、宣传截图和平台沟通记录，但医疗因果证据不足。", "收件主体、订单信息、宣传证据、具体诉求、附件清单、事实时间线。", "投诉函、消费者权益、证据清单、退赔请求", "unsupported_claim_amount"),
        ("X-DOC-002", "劳动仲裁申请要点", "请帮我整理一份劳动仲裁申请的事实和请求，主张未签劳动合同二倍工资。", "用户入职半年未签书面劳动合同，有工资流水和工作群记录。", "入职日期、用人单位主体、工资标准、离职情况、仲裁时效、证据目录。", "劳动仲裁、二倍工资、证据目录、仲裁请求", "limitation_warning_missing"),
        ("X-DOC-003", "律师函式催款函", "客户拖欠设计尾款，我想发一封正式催款函。", "存在设计服务合同、部分交付和尾款拖欠，但验收争议未完全清楚。", "合同编号、交付成果、验收记录、付款节点、催告期限、违约条款。", "催款函、服务合同、违约责任、验收争议", "missing_acceptance_terms"),
        ("X-DOC-004", "房屋租赁解除通知", "请帮我写一份解除租赁合同通知，房东长期不维修漏水。", "承租人反映房屋漏水，多次通知房东未维修，想解除合同。", "租赁合同、漏水照片、维修通知、影响居住程度、押金和搬离日期。", "租赁合同解除、通知函、维修义务、押金返还", "procedure_warning_missing"),
        ("X-DOC-005", "交通事故索赔清单", "我想整理一份交通事故索赔材料清单和赔偿请求。", "用户受伤就医，有事故认定书和部分费用票据。", "责任比例、伤情诊断、误工证明、护理证明、鉴定意见、保险信息。", "交通事故、人身损害、赔偿项目、证据清单", "missing_assessment_evidence"),
        ("X-DOC-006", "培训退费协商函", "培训机构不开课，我想发一份退费协商函。", "用户支付培训费，课程未按约开课，对方拖延退款。", "合同条款、付款流水、课程排期、沟通记录、退款金额计算、收件主体。", "教育培训合同、退费、协商函、证据附件", "refund_scope_overclaim"),
        ("X-DOC-007", "二手交易维权说明", "二手平台买到假货，我想写一份给平台的维权说明。", "用户在二手平台购买商品，收到后怀疑是假货，有鉴定聊天但无正式鉴定。", "订单、卖家承诺、商品照片、鉴定材料、平台规则、退货状态。", "二手交易、平台投诉、假货争议、证据组织", "fake_authentication_missing"),
        ("X-DOC-008", "股东知情权申请", "小股东想要求公司提供账册，请帮我整理申请书要点。", "股东持有少数股权，怀疑公司账目不透明。", "股东身份、持股比例、查阅目的、公司章程、已沟通记录、请求范围。", "公司治理、股东知情权、申请书、查阅范围", "request_scope_unclear"),
        ("X-DOC-009", "竞业限制回复函", "前公司说我违反竞业限制，我想回函说明不认可。", "用户离职后入职新公司，前公司发函要求赔违约金。", "竞业协议、补偿支付、新岗位内容、地域期限、商业秘密接触情况。", "竞业限制、回复函、补偿义务、违约抗辩", "employment_status_unclear"),
        ("X-DOC-010", "工程款结算说明", "甲方拖欠工程尾款，请帮我列一个结算和催款说明框架。", "存在工程合同、阶段验收和尾款未付，部分签证单缺失。", "合同价款、结算单、验收记录、签证变更、付款流水、催告对象。", "工程款、结算说明、证据清单、催告函", "missing_settlement_evidence"),
        ("X-DOC-011", "平台价格争议投诉", "我想向平台投诉会员价格比普通账号更贵，怎么写事实和诉求？", "用户比价发现会员价高，保存了部分截图。", "截图时间、账号条件、酒店房型、优惠券、平台规则、个人信息处理说明。", "消费者投诉、算法定价、个人信息、证据组织", "dynamic_pricing_unclear"),
        ("X-DOC-012", "宠物寄养赔偿协商书", "宠物寄养受伤，我想写一份赔偿协商书。", "宠物寄养期间受伤，宠物店否认照护过错。", "寄养协议、接收状态、监控、兽医诊断、费用票据、赔偿项目。", "服务合同、保管责任、协商书、损失证明", "evidence_missing"),
        ("X-DOC-013", "借款催收短信模板", "朋友借钱不还，我想写一段催收短信，既正式又不要违法。", "存在借款转账和聊天记录，但没有完整借条。", "借款金额、期限、转账记录、还款承诺、催收频率、不得威胁骚扰。", "民间借贷、催收边界、证据固定、诉讼时效", "unsafe_action_suggestion"),
        ("X-DOC-014", "商标侵权投诉材料", "品牌方发现网店卖相似商标商品，请整理平台投诉材料。", "存在相似标识商品链接、品牌商标证和销售页面截图。", "商标注册证、侵权链接、购买取证、混淆比对、权利人主体、平台规则。", "商标侵权、平台投诉、证据清单、停止销售", "claim_support_missing"),
        ("X-DOC-015", "高额违约金答辩要点", "合同约定违约金很高，对方起诉我全额赔，请帮我整理答辩要点。", "存在合同违约和高额违约金主张，实际损失不明。", "合同金额、违约原因、实际损失、履约情况、违约金比例、减免理由。", "违约金调整、答辩要点、损失证明、合同责任", "actual_loss_missing"),
    ]

    records = []
    for task_category, rows in [
        ("consultation", consultation),
        ("case_analysis", case_analysis),
        ("document_drafting", document),
    ]:
        for sample_id, title, question, known, missing, concepts, subtype in rows:
            records.append(
                {
                    "sample_id": sample_id,
                    "source_dataset": "extended_diagnostic_45",
                    "task_category": task_category,
                    "scenario_title": title,
                    "user_question": question,
                    "known_facts": known,
                    "key_missing_facts": missing,
                    "expected_clarification_questions": f"请补充：{missing}",
                    "expected_answer_points": (
                        "应先说明事实不足，围绕主体、证据、程序和请求基础进行条件化分析；"
                        "不得直接承诺确定结果或编造具体法条。"
                    ),
                    "risk_points": f"主要风险包括证据链不足、程序路径不明、过度承诺结论，以及 {subtype}。",
                    "legal_concepts": concepts,
                    "expected_behavior": "任务类型化分析 + 风险控制 + 数据可用标签",
                    "human_review_note": "internal extended diagnostic sample; use for scale testing and data-routing calibration.",
                    "task_type": task_category,
                    "jurisdiction": JURISDICTION,
                    "law_snapshot_date": LAW_SNAPSHOT_DATE,
                    "legal_advice_boundary": BOUNDARY,
                    "error_subtype": subtype,
                }
            )
    return records


def _has_normalized_workbook_sheets(workbook: Path) -> bool:
    try:
        xls = pd.ExcelFile(workbook)
    except Exception:
        return False
    return {"Eval_Input", "Gold_Labels", "Rubric_Items"}.issubset(set(xls.sheet_names))


def _normalize_new_core_workbook(workbook: Path, output: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], pd.DataFrame]:
    eval_sheet = _read_sheet(workbook, "Eval_Input")
    gold_sheet = _read_sheet(workbook, "Gold_Labels")
    rubric_sheet = _read_sheet(workbook, "Rubric_Items")

    eval_records: list[dict[str, Any]] = []
    gold_records: list[dict[str, Any]] = []
    rubric_records: list[dict[str, Any]] = []
    metadata_records: list[dict[str, Any]] = []

    source_dataset = "self_authored_core_40"
    gold_by_id = {safe_text(row["sample_id"]): row for _, row in gold_sheet.iterrows()}

    for _, row in eval_sheet.iterrows():
        sample_id = safe_text(row["sample_id"])
        task_category = safe_text(row.get("task_category")) or _infer_task_category(
            safe_text(row.get("task_type", "")), safe_text(row.get("legal_domain", ""))
        )
        eval_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": source_dataset,
                "task_category": task_category,
                "user_question": safe_text(row.get("user_question")),
                "known_facts": safe_text(row.get("known_facts")),
                "legal_concepts": safe_text(row.get("legal_concepts")),
                "jurisdiction": safe_text(row.get("jurisdiction")) or JURISDICTION,
                "law_snapshot_date": safe_text(row.get("law_snapshot_date")) or LAW_SNAPSHOT_DATE,
                "task_type": safe_text(row.get("task_type")) or task_category,
                "legal_advice_boundary": safe_text(row.get("legal_advice_boundary")) or BOUNDARY,
            }
        )
        gold_row = gold_by_id.get(sample_id)
        if gold_row is None:
            raise ValueError(f"Gold_Labels missing sample_id: {sample_id}")
        gold_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": source_dataset,
                "task_category": task_category,
                "key_missing_facts": safe_text(gold_row.get("key_missing_facts")),
                "expected_clarification_questions": safe_text(gold_row.get("expected_clarification_questions")),
                "expected_answer_points": safe_text(gold_row.get("expected_answer_points")),
                "risk_points": safe_text(gold_row.get("risk_points")),
                "expected_behavior": safe_text(gold_row.get("expected_behavior")),
                "human_review_note": safe_text(gold_row.get("human_review_note")),
            }
        )
        metadata_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": source_dataset,
                "task_category": task_category,
                "legal_domain": safe_text(row.get("legal_domain")),
                "difficulty": safe_text(row.get("difficulty")),
                "risk_level": safe_text(row.get("risk_level")),
                "visibility_policy": safe_text(row.get("visibility_policy")),
                "core_sample_flag": safe_text(row.get("core_sample_flag")) or "yes",
                "deep_badcase_flag": safe_text(row.get("deep_badcase_flag")) or "no",
                "human_review_required": safe_text(row.get("human_review_required")) or "no",
            }
        )

    for _, row in rubric_sheet.iterrows():
        sample_id = safe_text(row.get("sample_id"))
        task_category = safe_text(row.get("task_category"))
        rubric_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": source_dataset,
                "task_category": task_category,
                "rubric_id": safe_text(row.get("rubric_id")),
                "rubric_dimension": safe_text(row.get("rubric_dimension")),
                "atomic_rubric_item": safe_text(row.get("atomic_rubric_item")),
                "max_score": int(float(safe_text(row.get("max_score")) or 2)),
                "scoring_rule_2": safe_text(row.get("scoring_rule_2")),
                "scoring_rule_1": safe_text(row.get("scoring_rule_1")),
                "scoring_rule_0": safe_text(row.get("scoring_rule_0")),
                "criticality": safe_text(row.get("criticality")),
                "negative_rule": safe_text(row.get("negative_rule")),
            }
        )

    metadata = pd.DataFrame(metadata_records, columns=METADATA_COLUMNS)
    metadata.to_csv(output / "sample_metadata.csv", index=False, encoding="utf-8-sig")
    return eval_records, gold_records, rubric_records, metadata


def build_normalized_dataset(
    *,
    input_workbook: str | Path,
    output_dir: str | Path = "data",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    workbook = Path(input_workbook)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    if _has_normalized_workbook_sheets(workbook):
        eval_records, gold_records, rubric_records, metadata = _normalize_new_core_workbook(workbook, output)
        use_extended_samples = True
    else:
        metadata = pd.DataFrame(columns=METADATA_COLUMNS)
        use_extended_samples = True
        eval_records = []
        gold_records = []
        rubric_records = []

    if not _has_normalized_workbook_sheets(workbook):
        task_set = _read_sheet(workbook, "Task_Set")
        sample_index = _read_sheet(workbook, "Sample_Index")
        rubric_items = _read_sheet(workbook, "Rubric_Items")
        routing = _read_sheet(workbook, "Error_Tags_Data_Routing")
        meta_cols = [col for col in ["sample_id", "task_type", "legal_domain"] if col in sample_index.columns]
        task_set = task_set.merge(sample_index[meta_cols], on="sample_id", how="left")
        route_reason = dict(zip(routing["sample_id"], routing.get("route_reason", "")))

        for _, row in task_set.iterrows():
            sample_id = safe_text(row["sample_id"])
            task_category = _infer_task_category(safe_text(row.get("task_type", "")), safe_text(row.get("legal_domain", "")))
            eval_records.append(
                {
                    "sample_id": sample_id,
                    "source_dataset": "self_authored_core",
                    "task_category": task_category,
                    "user_question": safe_text(row["user_question"]),
                    "known_facts": safe_text(row["known_facts"]),
                    "legal_concepts": safe_text(row["legal_concepts"]),
                    "jurisdiction": JURISDICTION,
                    "law_snapshot_date": LAW_SNAPSHOT_DATE,
                    "task_type": safe_text(row.get("task_type", "")),
                    "legal_advice_boundary": BOUNDARY,
                }
            )
            gold_records.append(
                {
                    "sample_id": sample_id,
                    "source_dataset": "self_authored_core",
                    "task_category": task_category,
                    "key_missing_facts": safe_text(row["key_missing_facts"]),
                    "expected_clarification_questions": safe_text(row["expected_clarification_questions"]),
                    "expected_answer_points": safe_text(row["expected_answer_points"]),
                    "risk_points": safe_text(row["risk_points"]),
                    "expected_behavior": safe_text(row["expected_behavior"]),
                    "human_review_note": safe_text(route_reason.get(sample_id, "")),
                }
            )
            for item in _records_for_rubric(rubric_items, sample_id):
                item["source_dataset"] = "self_authored_core"
                item["task_category"] = task_category
                rubric_records.append(item)

    for row in _extended_specs() if use_extended_samples else []:
        eval_records.append(
            {
                key: row[key]
                for key in [
                    "sample_id",
                    "source_dataset",
                    "task_category",
                    "user_question",
                    "known_facts",
                    "legal_concepts",
                    "jurisdiction",
                    "law_snapshot_date",
                    "task_type",
                    "legal_advice_boundary",
                ]
            }
        )
        gold_records.append(
            {
                key: row[key]
                for key in [
                    "sample_id",
                    "source_dataset",
                    "task_category",
                    "key_missing_facts",
                    "expected_clarification_questions",
                    "expected_answer_points",
                    "risk_points",
                    "expected_behavior",
                    "human_review_note",
                ]
            }
        )
        if row["task_category"] == "consultation":
            specs = [
                ("Missing Facts Awareness", "识别并追问关键缺失事实", "未补充事实即给出确定结论"),
                ("Clarification Quality", "提出可操作的追问问题", "追问过泛或遗漏主体/证据"),
                ("Risk Coverage", "覆盖证据、程序和结果不确定性风险", "忽略证据或程序风险"),
                ("Overclaim Control", "避免承诺确定赔偿、胜诉或违法结论", "过度承诺法律结果"),
            ]
        elif row["task_category"] == "case_analysis":
            specs = [
                ("Fact-Rule Application", "围绕事实、争点、规则方向和适用展开分析", "只堆法律概念不连接事实"),
                ("Legal Grounding", "说明法律依据方向且不编造具体引用", "编造或笼统引用法律依据"),
                ("Conditional Reasoning", "根据事实缺口给出条件化结论", "把不确定事实当成已证实"),
                ("Risk Coverage", "区分证据、程序、主体和抗辩风险", "遗漏关键抗辩或程序风险"),
            ]
        else:
            specs = [
                ("Draft Structure", "给出清晰文书结构或材料框架", "结构混乱或缺少核心模块"),
                ("Fact Organization", "按时间线、主体、请求和证据组织事实", "插入未给出的事实或金额"),
                ("Risk Coverage", "提示附件、证据、程序和管辖风险", "遗漏证据或程序风险"),
                ("Overclaim Control", "文书表述保持条件化且不编造法律依据", "写成确定法律意见或虚构引用"),
            ]
        rubric_records.extend(_rubric_rows(row["sample_id"], row["source_dataset"], row["task_category"], specs))

    eval_input = pd.DataFrame(eval_records, columns=AGENT_VISIBLE_COLUMNS)
    gold_labels = pd.DataFrame(gold_records, columns=GOLD_COLUMNS)
    rubric_df = pd.DataFrame(rubric_records)
    eval_input.to_csv(output / "eval_input.csv", index=False, encoding="utf-8-sig")
    gold_labels.to_csv(output / "gold_labels.csv", index=False, encoding="utf-8-sig")
    rubric_df.to_csv(output / "rubric_items.csv", index=False, encoding="utf-8-sig")
    return eval_input, gold_labels, rubric_df
