from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from dataclasses import dataclass
import tkinter as tk
from tkinter import messagebox, ttk


CHECKOUT_ENDPOINT = "https://chatgpt.com/backend-api/payments/checkout"
PROMO_CHECK_ENDPOINT = "https://chatgpt.com/backend-api/promo_campaign/check_coupon"
STRIPE_INIT_BASE = "https://api.stripe.com/v1/payment_pages"
STRIPE_API_VERSION = (
    "2025-03-31.basil; "
    "checkout_server_update_beta=v1; "
    "checkout_manual_approval_preview=v1"
)
ALLOWED_LINK_HOSTS = {
    "chatgpt.com",
    "pay.openai.com",
    "checkout.stripe.com",
}


@dataclass(frozen=True)
class Country:
    name: str
    code: str
    currency: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code} / {self.currency})"


@dataclass(frozen=True)
class PaymentPreset:
    label: str
    country_code: str | None
    expected_methods: tuple[str, ...]
    note: str


COUNTRIES = [
    Country("巴西", "BR", "BRL"),
    Country("印度", "IN", "INR"),
    Country("美国", "US", "USD"),
    Country("英国", "GB", "GBP"),
    Country("德国", "DE", "EUR"),
    Country("法国", "FR", "EUR"),
    Country("荷兰", "NL", "EUR"),
    Country("爱尔兰", "IE", "EUR"),
    Country("意大利", "IT", "EUR"),
    Country("西班牙", "ES", "EUR"),
    Country("葡萄牙", "PT", "EUR"),
    Country("比利时", "BE", "EUR"),
    Country("奥地利", "AT", "EUR"),
    Country("芬兰", "FI", "EUR"),
    Country("日本", "JP", "JPY"),
    Country("印度尼西亚", "ID", "IDR"),
    Country("韩国", "KR", "KRW"),
    Country("新加坡", "SG", "SGD"),
    Country("泰国", "TH", "THB"),
    Country("越南", "VN", "VND"),
    Country("中国香港", "HK", "HKD"),
    Country("中国台湾", "TW", "TWD"),
    Country("加拿大", "CA", "CAD"),
    Country("澳大利亚", "AU", "AUD"),
    Country("新西兰", "NZ", "NZD"),
    Country("墨西哥", "MX", "MXN"),
    Country("土耳其", "TR", "TRY"),
    Country("阿联酋", "AE", "AED"),
    Country("波兰", "PL", "PLN"),
    Country("瑞士", "CH", "CHF"),
    Country("瑞典", "SE", "SEK"),
    Country("挪威", "NO", "NOK"),
    Country("丹麦", "DK", "DKK"),
    Country("捷克", "CZ", "CZK"),
    Country("罗马尼亚", "RO", "RON"),
    Country("希腊", "GR", "EUR"),
    Country("马来西亚", "MY", "MYR"),
    Country("菲律宾", "PH", "PHP"),
    Country("沙特阿拉伯", "SA", "SAR"),
    Country("南非", "ZA", "ZAR"),
    Country("智利", "CL", "CLP"),
    Country("哥伦比亚", "CO", "COP"),
    Country("秘鲁", "PE", "PEN"),
]
COUNTRY_BY_LABEL = {country.label: country for country in COUNTRIES}
COUNTRY_BY_CODE = {country.code: country for country in COUNTRIES}

OFFICIAL_NOTE = (
    "OpenAI 官方列出该地区支付方式；是否出现在本次 Plus 长链，仍由账号、币种、"
    "订阅模式、付款人位置和结账处理器共同决定。"
)
EXPERIMENTAL_NOTE = (
    "实验检测：Stripe 在部分集成中支持该本地方式，但 OpenAI 未公开承诺用于 Plus；"
    "本工具只设置地区并检测，不会强制开启。"
)

PAYMENT_PRESETS = [
    PaymentPreset("🇧🇷 巴西 · Pix【OpenAI 官方】", "BR", ("pix",), OFFICIAL_NOTE),
    PaymentPreset("🇮🇳 印度 · UPI【OpenAI 官方】", "IN", ("upi",), OFFICIAL_NOTE),
    PaymentPreset("🇮🇩 印尼 · GoPay【OpenAI 官方】", "ID", ("gopay",), OFFICIAL_NOTE),
    PaymentPreset(
        "🇰🇷 韩国 · KakaoPay / NaverPay / 本地卡【OpenAI 官方】",
        "KR",
        ("kakao_pay", "naver_pay", "card"),
        OFFICIAL_NOTE,
    ),
    PaymentPreset("🇬🇧 英国 · Link 银行扣款【OpenAI 官方】", "GB", ("link", "bacs_debit"), OFFICIAL_NOTE),
    PaymentPreset("🇩🇪 德国 · Link 银行扣款【OpenAI 官方】", "DE", ("link",), OFFICIAL_NOTE),
    PaymentPreset("🇫🇷 法国 · Link 银行扣款【OpenAI 官方】", "FR", ("link",), OFFICIAL_NOTE),
    PaymentPreset("🇳🇱 荷兰 · Link 银行扣款【OpenAI 官方】", "NL", ("link",), OFFICIAL_NOTE),
    PaymentPreset("🇪🇸 西班牙 · Link 银行扣款【OpenAI 官方】", "ES", ("link",), OFFICIAL_NOTE),
    PaymentPreset("🇮🇹 意大利 · Link 银行扣款【OpenAI 官方】", "IT", ("link",), OFFICIAL_NOTE),
    PaymentPreset("🇳🇱 荷兰 · iDEAL【实验检测】", "NL", ("ideal",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇧🇪 比利时 · Bancontact【实验检测】", "BE", ("bancontact",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇦🇹 奥地利 · EPS【实验检测】", "AT", ("eps",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇵🇱 波兰 · BLIK【实验检测】", "PL", ("blik",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇵🇱 波兰 · Przelewy24 / P24【实验检测】", "PL", ("p24",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇨🇭 瑞士 · TWINT【实验检测】", "CH", ("twint",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇩🇪 德国 · PayPal【实验检测】", "DE", ("paypal",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇫🇷 法国 · PayPal【实验检测】", "FR", ("paypal",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇬🇧 英国 · PayPal【实验检测】", "GB", ("paypal",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇯🇵 日本 · Konbini 便利店【实验检测】", "JP", ("konbini",), EXPERIMENTAL_NOTE),
    PaymentPreset("🇯🇵 日本 · PayPay【实验检测】", "JP", ("paypay",), EXPERIMENTAL_NOTE),
    PaymentPreset(
        "🌐 自定义国家/地区 · Stripe 自动检测",
        None,
        (),
        "自由选择国家和币种；最终支付方式完全以 Checkout 实际返回为准。",
    ),
]
PRESET_BY_LABEL = {preset.label: preset for preset in PAYMENT_PRESETS}
METHOD_PIX = PAYMENT_PRESETS[0].label

METHOD_FRIENDLY_NAMES = {
    "card": "银行卡 Card",
    "pix": "Pix",
    "upi": "UPI",
    "gopay": "GoPay",
    "kakao_pay": "KakaoPay",
    "naver_pay": "NaverPay",
    "link": "Link",
    "bacs_debit": "Bacs 银行扣款",
    "sepa_debit": "SEPA 银行扣款",
    "ideal": "iDEAL",
    "bancontact": "Bancontact",
    "eps": "EPS",
    "blik": "BLIK",
    "p24": "Przelewy24 / P24",
    "twint": "TWINT",
    "paypal": "PayPal",
    "konbini": "Konbini 便利店",
    "paypay": "PayPay",
    "apple_pay": "Apple Pay",
    "google_pay": "Google Pay",
}

PROMO_NONE = "不使用优惠"
PROMO_CAMPAIGN = "活动 ID（promo_campaign，适合 plus-1-month-free）"
PROMO_CODE = "普通优惠码（promo_code）"
PROMO_MODES = [PROMO_CAMPAIGN, PROMO_CODE, PROMO_NONE]


def find_token_in_value(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("accessToken", "access_token", "token"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for child in value.values():
            found = find_token_in_value(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_token_in_value(child)
            if found:
                return found
    return None


def extract_access_token(raw: str) -> str:
    text = raw.strip()
    if not text:
        raise ValueError("请粘贴 Access Token 或完整 Session JSON。")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    if parsed is not None:
        token = find_token_in_value(parsed)
        if token:
            return token

    bearer_match = re.search(r"\bBearer\s+([^\s\"']+)", text, re.IGNORECASE)
    if bearer_match:
        return bearer_match.group(1).strip()

    field_match = re.search(
        r'["\']?access(?:T|_t)oken["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        text,
        re.IGNORECASE,
    )
    if field_match:
        return field_match.group(1).strip()

    if not any(char.isspace() for char in text) and len(text) >= 80:
        return text

    raise ValueError("没有识别到 Access Token。请粘贴原始 Token 或 Session JSON。")


def allowed_checkout_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host in ALLOWED_LINK_HOSTS


def response_error_message(status: int, raw_body: str) -> str:
    detail = ""
    try:
        data = json.loads(raw_body)
        if isinstance(data, dict):
            value = data.get("detail") or data.get("message") or data.get("error")
            if isinstance(value, dict):
                value = value.get("message") or value.get("code") or json.dumps(value, ensure_ascii=False)
            if value:
                detail = str(value)
    except json.JSONDecodeError:
        detail = raw_body[:500].strip()

    suffix = f"\n{detail}" if detail else ""
    return f"ChatGPT Checkout 请求失败（HTTP {status}）。{suffix}"


def stripe_locale_and_timezone(country_code: str) -> tuple[str, str]:
    if country_code == "BR":
        return "pt-BR", "America/Sao_Paulo"
    if country_code == "IN":
        return "en-IN", "Asia/Kolkata"
    return "en", "UTC"


def checkout_accept_language(country_code: str) -> str:
    if country_code == "BR":
        return "pt-BR,pt;q=0.9,en;q=0.8"
    if country_code == "IN":
        return "en-IN,en;q=0.9"
    if country_code == "ID":
        return "id-ID,id;q=0.9,en;q=0.8"
    if country_code == "KR":
        return "ko-KR,ko;q=0.9,en;q=0.8"
    return "en-US,en;q=0.9"


def stripe_init_long_link(
    session_id: str,
    publishable_key: str,
    country: Country,
) -> tuple[str, list[str]]:
    locale, timezone = stripe_locale_and_timezone(country.code)
    form = {
        "browser_locale": locale,
        "browser_timezone": timezone,
        "elements_session_client[client_betas][0]": "custom_checkout_server_updates_1",
        "elements_session_client[client_betas][1]": "custom_checkout_manual_approval_1",
        "elements_session_client[elements_init_source]": "custom_checkout",
        "elements_session_client[referrer_host]": "chatgpt.com",
        "elements_session_client[stripe_js_id]": str(uuid.uuid4()),
        "elements_session_client[locale]": locale,
        "elements_session_client[is_aggregation_expected]": "false",
        "elements_options_client[saved_payment_method][enable_save]": "auto",
        "elements_options_client[saved_payment_method][enable_redisplay]": "auto",
        "key": publishable_key,
        "_stripe_version": STRIPE_API_VERSION,
    }
    request = urllib.request.Request(
        f"{STRIPE_INIT_BASE}/{urllib.parse.quote(session_id, safe='')}/init",
        data=urllib.parse.urlencode(form).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {publishable_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Stripe 长链初始化失败（HTTP {error.code}）：{body[:300]}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"无法连接 Stripe 长链接口：{error.reason}") from None

    if status < 200 or status >= 300:
        raise RuntimeError(f"Stripe 长链初始化失败（HTTP {status}）。")
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        raise RuntimeError("Stripe 返回了无法解析的响应。") from None
    if not isinstance(data, dict):
        raise RuntimeError("Stripe 返回的数据格式不正确。")

    link = data.get("stripe_hosted_url") or data.get("hosted_url") or data.get("url")
    if not isinstance(link, str) or not link.strip():
        raise RuntimeError("Stripe 没有返回 Hosted 长链接。")
    link = link.strip()
    if not allowed_checkout_url(link):
        raise RuntimeError(f"Stripe 返回了未允许的链接域名：{urllib.parse.urlparse(link).hostname}")

    raw_methods = data.get("payment_method_types")
    methods = [str(item) for item in raw_methods] if isinstance(raw_methods, list) else []
    return link, methods


def check_campaign_eligibility(access_token: str, campaign_id: str) -> str:
    query = urllib.parse.urlencode(
        {
            "coupon": campaign_id,
            "is_coupon_from_query_param": "true",
        }
    )
    request = urllib.request.Request(
        f"{PROMO_CHECK_ENDPOINT}?{query}",
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Referer": f"https://chatgpt.com/?promo_campaign={urllib.parse.quote(campaign_id)}",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"优惠资格预检失败（HTTP {error.code}）：{body[:300]}"
        ) from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"无法检查优惠资格：{error.reason}") from None

    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        raise RuntimeError("优惠资格接口返回了无法解析的响应。") from None
    if not isinstance(data, dict):
        raise RuntimeError("优惠资格接口返回的数据格式不正确。")
    state = data.get("state") or data.get("coupon_state") or data.get("reason")
    return str(state or "unknown")


def request_checkout_link(
    access_token: str,
    country: Country,
    promo_mode: str,
    promo_value: str,
) -> tuple[str, str, list[str], str]:
    promo_state = "not_requested"
    payload: dict[str, object] = {
        "plan_name": "chatgptplusplan",
        "billing_details": {
            "country": country.code,
            "currency": country.currency,
        },
        "cancel_url": "https://chatgpt.com/#pricing",
        "checkout_ui_mode": "hosted",
    }
    referer = "https://chatgpt.com/"
    if promo_mode == PROMO_CAMPAIGN:
        promo_state = check_campaign_eligibility(access_token, promo_value)
        if promo_state.lower() != "eligible":
            raise RuntimeError(f"该账号不符合活动 {promo_value}：{promo_state}")
        payload["promo_campaign"] = {
            "promo_campaign_id": promo_value,
            "is_coupon_from_query_param": False,
        }
        referer = f"https://chatgpt.com/?promo_campaign={urllib.parse.quote(promo_value)}"
    elif promo_mode == PROMO_CODE:
        payload["promo_code"] = promo_value

    request = urllib.request.Request(
        CHECKOUT_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": checkout_accept_language(country.code),
            "Origin": "https://chatgpt.com",
            "Referer": referer,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as error:
        raw_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(response_error_message(error.code, raw_body)) from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"无法连接 ChatGPT Checkout：{error.reason}") from None

    if status < 200 or status >= 300:
        raise RuntimeError(response_error_message(status, raw_body))

    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        raise RuntimeError("ChatGPT 返回了无法解析的响应。") from None
    if not isinstance(data, dict):
        raise RuntimeError("ChatGPT 返回的数据格式不正确。")

    for key in ("url", "stripe_hosted_url", "checkout_url"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            link = value.strip()
            if not allowed_checkout_url(link):
                raise RuntimeError(f"服务器返回了未允许的链接域名：{urllib.parse.urlparse(link).hostname}")
            raw_methods = data.get("payment_method_types")
            methods = [str(item) for item in raw_methods] if isinstance(raw_methods, list) else []
            applied = bool(data.get("promo_campaign")) if promo_mode == PROMO_CAMPAIGN else None
            promo_result = (
                f"eligible / checkout={'confirmed' if applied else 'unconfirmed'}"
                if promo_mode == PROMO_CAMPAIGN
                else ("promo_code_requested" if promo_mode == PROMO_CODE else "not_requested")
            )
            return link, "hosted", methods, promo_result

    session_id = data.get("checkout_session_id") or data.get("session_id")
    entity = data.get("processor_entity")
    if isinstance(session_id, str) and session_id.strip():
        session_id = session_id.strip()
        publishable_key = data.get("publishable_key")
        if isinstance(publishable_key, str) and publishable_key.strip():
            try:
                link, methods = stripe_init_long_link(
                    session_id,
                    publishable_key.strip(),
                    country,
                )
                applied = bool(data.get("promo_campaign")) if promo_mode == PROMO_CAMPAIGN else None
                promo_result = (
                    f"eligible / checkout={'confirmed' if applied else 'unconfirmed'}"
                    if promo_mode == PROMO_CAMPAIGN
                    else ("promo_code_requested" if promo_mode == PROMO_CODE else "not_requested")
                )
                return link, "stripe_hosted", methods, promo_result
            except RuntimeError:
                pass
        if isinstance(entity, str) and entity.strip():
            fallback = f"https://chatgpt.com/checkout/{entity.strip()}/{session_id}"
        else:
            fallback = f"https://chatgpt.com/checkout/{session_id}"
        promo_result = (
            f"{promo_state} / checkout={'confirmed' if bool(data.get('promo_campaign')) else 'unconfirmed'}"
            if promo_mode == PROMO_CAMPAIGN
            else ("promo_code_requested" if promo_mode == PROMO_CODE else "not_requested")
        )
        return fallback, "fallback", [], promo_result

    detail = data.get("detail") or data.get("message") or data.get("error")
    raise RuntimeError(f"服务器没有返回支付链接。{f'\n{detail}' if detail else ''}")


class CheckoutApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ChatGPT Plus 支付长链接生成器")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(840, max(700, screen_width - 80))
        window_height = min(800, max(650, screen_height - 100))
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(680, 620)

        self.country_var = tk.StringVar(value=COUNTRIES[0].label)
        self.method_var = tk.StringVar(value=METHOD_PIX)
        self.promo_mode_var = tk.StringVar(value=PROMO_CAMPAIGN)
        self.promo_var = tk.StringVar(value="plus-1-month-free")
        self.clear_token_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="就绪。凭证只保存在内存中。")
        self.result_var = tk.StringVar()
        self.result_url = ""

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)

        title = ttk.Label(
            container,
            text="ChatGPT Plus 支付长链接生成器",
            font=("Microsoft YaHei UI", 17, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            container,
            text="本地运行 · 不保存 Token · 只请求 ChatGPT 与 Stripe 官方接口 · 最终付款由你确认",
            foreground="#555555",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 16))

        ttk.Label(container, text="1. Access Token 或完整 Session JSON").grid(
            row=2, column=0, sticky="w"
        )
        self.token_text = tk.Text(container, height=5, wrap="word", undo=True)
        self.token_text.grid(row=3, column=0, sticky="nsew", pady=(6, 6))
        self.token_text.insert("1.0", "")

        token_actions = ttk.Frame(container)
        token_actions.grid(row=4, column=0, sticky="ew", pady=(0, 14))
        ttk.Checkbutton(
            token_actions,
            text="生成后清空凭证",
            variable=self.clear_token_var,
        ).pack(side="left")
        ttk.Button(token_actions, text="立即清空", command=self.clear_token).pack(side="right")

        options = ttk.LabelFrame(container, text="2. 结账设置", padding=12)
        options.grid(row=5, column=0, sticky="ew")
        options.columnconfigure(1, weight=1)

        ttk.Label(options, text="国家/地区 + 支付渠道").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        method_combo = ttk.Combobox(
            options,
            textvariable=self.method_var,
            values=[preset.label for preset in PAYMENT_PRESETS],
            state="readonly",
        )
        method_combo.grid(row=0, column=1, sticky="ew")
        method_combo.bind("<<ComboboxSelected>>", self.on_method_changed)

        ttk.Label(options, text="国家与币种").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0)
        )
        self.country_combo = ttk.Combobox(
            options,
            textvariable=self.country_var,
            values=[country.label for country in COUNTRIES],
            state="readonly",
        )
        self.country_combo.grid(row=1, column=1, sticky="ew", pady=(10, 0))

        ttk.Label(options, text="优惠类型").grid(
            row=2, column=0, sticky="w", padx=(0, 12), pady=(10, 0)
        )
        promo_mode_combo = ttk.Combobox(
            options,
            textvariable=self.promo_mode_var,
            values=PROMO_MODES,
            state="readonly",
        )
        promo_mode_combo.grid(row=2, column=1, sticky="ew", pady=(10, 0))
        promo_mode_combo.bind("<<ComboboxSelected>>", self.on_promo_mode_changed)

        ttk.Label(options, text="活动 ID / 优惠码").grid(
            row=3, column=0, sticky="w", padx=(0, 12), pady=(10, 0)
        )
        promo_entry = ttk.Entry(options, textvariable=self.promo_var)
        promo_entry.grid(row=3, column=1, sticky="ew", pady=(10, 0))

        self.method_note = ttk.Label(
            options,
            text="Pix 会使用巴西 BR / BRL，但不能强制出现；程序会显示长链实际开放的支付方式。",
            foreground="#6b4f00",
            wraplength=650,
        )
        self.method_note.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.promo_note = ttk.Label(
            options,
            text=(
                "plus-1-month-free 是活动 ID，不是普通 promo_code。程序会先检查 eligible，"
                "再把 promo_campaign 写入 Checkout。"
            ),
            foreground="#6b4f00",
            wraplength=650,
        )
        self.promo_note.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.generate_button = ttk.Button(
            container,
            text="3. 生成支付长链接",
            command=self.generate,
        )
        self.generate_button.grid(row=6, column=0, sticky="ew", pady=(16, 10), ipady=6)

        result_frame = ttk.LabelFrame(container, text="生成结果（成功后长链接会显示在这里）", padding=10)
        result_frame.grid(row=7, column=0, sticky="ew", pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)

        result_entry = ttk.Entry(
            result_frame,
            textvariable=self.result_var,
            state="readonly",
        )
        result_entry.grid(row=0, column=0, columnspan=3, sticky="ew")

        ttk.Button(result_frame, text="复制链接", command=self.copy_link).grid(
            row=1, column=0, sticky="ew", padx=(0, 6), pady=(10, 0)
        )
        ttk.Button(result_frame, text="浏览器打开", command=self.open_link).grid(
            row=1, column=1, sticky="ew", padx=6, pady=(10, 0)
        )
        ttk.Button(result_frame, text="清除结果", command=self.clear_result).grid(
            row=1, column=2, sticky="ew", padx=(6, 0), pady=(10, 0)
        )

        status_box = ttk.LabelFrame(container, text="状态", padding=(10, 7))
        status_box.grid(row=8, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(status_box, textvariable=self.status_var, wraplength=760).pack(
            fill="x"
        )

        warning = ttk.Label(
            container,
            text=(
                "安全提示：只使用本人账号和合法优惠；国家、付款人及支付方式应真实匹配。"
                "只把最终支付链接发给付款人，绝不要发送 Access Token 或 Session JSON。"
            ),
            foreground="#9b1c1c",
            wraplength=710,
        )
        warning.grid(row=9, column=0, sticky="w", pady=(14, 0))
        self.on_method_changed()

    def on_method_changed(self, _event: object | None = None) -> None:
        preset = PRESET_BY_LABEL[self.method_var.get()]
        if preset.country_code:
            country = COUNTRY_BY_CODE[preset.country_code]
            self.country_var.set(country.label)
            self.country_combo.configure(state="disabled")
        else:
            self.country_combo.configure(state="readonly")
        expected = ", ".join(
            METHOD_FRIENDLY_NAMES.get(item, item) for item in preset.expected_methods
        )
        expected_text = f" 期望检测：{expected}。" if expected else ""
        self.method_note.config(text=preset.note + expected_text)

    def on_promo_mode_changed(self, _event: object | None = None) -> None:
        mode = self.promo_mode_var.get()
        if mode == PROMO_CAMPAIGN:
            if not self.promo_var.get().strip():
                self.promo_var.set("plus-1-month-free")
            self.promo_note.config(
                text=(
                    "活动模式会先调用资格接口；只有 eligible 才创建 Checkout，并发送 "
                    "promo_campaign.promo_campaign_id。"
                )
            )
        elif mode == PROMO_CODE:
            if self.promo_var.get().strip() == "plus-1-month-free":
                self.promo_var.set("")
            self.promo_note.config(text="普通优惠码将作为 promo_code 发送，不进行活动资格预检。")
        else:
            self.promo_note.config(text="本次 Checkout 不携带任何优惠参数。")

    def selected_country(self) -> Country:
        preset = PRESET_BY_LABEL[self.method_var.get()]
        if preset.country_code:
            return COUNTRY_BY_CODE[preset.country_code]
        return COUNTRY_BY_LABEL[self.country_var.get()]

    def generate(self) -> None:
        raw_token = self.token_text.get("1.0", "end").strip()
        promo_mode = self.promo_mode_var.get()
        promo_value = self.promo_var.get().strip()

        if promo_value.lower().startswith(("http://", "https://")):
            messagebox.showerror("优惠码格式", "请填写优惠码本身，不要粘贴完整邀请链接。")
            return
        if promo_mode != PROMO_NONE and not promo_value:
            messagebox.showerror("优惠参数", "请选择不使用优惠，或填写活动 ID / 优惠码。")
            return

        try:
            access_token = extract_access_token(raw_token)
            country = self.selected_country()
        except (ValueError, KeyError) as error:
            messagebox.showerror("输入错误", str(error))
            return

        self.generate_button.config(state="disabled")
        self.status_var.set(
            f"正在请求 ChatGPT Hosted Checkout：{country.code} / {country.currency} ..."
        )
        self.clear_result()

        thread = threading.Thread(
            target=self._generate_worker,
            args=(access_token, country, promo_mode, promo_value, self.method_var.get()),
            daemon=True,
        )
        thread.start()

    def _generate_worker(
        self,
        access_token: str,
        country: Country,
        promo_mode: str,
        promo_value: str,
        method: str,
    ) -> None:
        try:
            url, link_kind, methods, promo_result = request_checkout_link(
                access_token,
                country,
                promo_mode,
                promo_value,
            )
        except Exception as error:  # UI boundary: show a concise message to the user.
            self.root.after(0, self._generation_failed, str(error))
            return
        finally:
            access_token = ""  # Best-effort removal of the local reference.

        self.root.after(
            0,
            self._generation_succeeded,
            url,
            link_kind,
            methods,
            promo_result,
            country,
            method,
        )

    def _generation_succeeded(
        self,
        url: str,
        link_kind: str,
        methods: list[str],
        promo_result: str,
        country: Country,
        method: str,
    ) -> None:
        self.result_url = url
        self.result_var.set(url)

        if link_kind in {"hosted", "stripe_hosted"}:
            message = "已生成并验证 Hosted 长链接。"
        else:
            message = "服务器未返回 Hosted URL，已提供 ChatGPT Checkout 回退链接。"
        if methods:
            friendly_methods = [METHOD_FRIENDLY_NAMES.get(item, item) for item in methods]
            message += f" 长链实际开放：{', '.join(friendly_methods)}。"
            preset = PRESET_BY_LABEL.get(method)
            if preset and preset.expected_methods:
                expected_set = set(preset.expected_methods)
                if not expected_set.intersection(methods):
                    expected_text = ", ".join(
                        METHOD_FRIENDLY_NAMES.get(item, item)
                        for item in preset.expected_methods
                    )
                    message += f" 注意：预设渠道 {expected_text} 本次没有出现。"
        if promo_result != "not_requested":
            message += f" 优惠状态：{promo_result}；请以结账页划线价/应付金额为准。"
        if "PayPal" in method:
            message += " 请打开页面确认是否实际出现 PayPal。"
        else:
            message += f" 请打开页面确认 {country.code} 当地支付方式和最终金额。"
        self.status_var.set(message)

        if self.clear_token_var.get():
            self.clear_token()
        self.generate_button.config(state="normal")

    def _generation_failed(self, message: str) -> None:
        self.status_var.set(message)
        self.generate_button.config(state="normal")
        if self.clear_token_var.get():
            self.clear_token()
        messagebox.showerror("生成失败", message)

    def clear_token(self) -> None:
        self.token_text.delete("1.0", "end")

    def clear_result(self) -> None:
        self.result_url = ""
        self.result_var.set("")

    def copy_link(self) -> None:
        if not self.result_url:
            messagebox.showinfo("没有链接", "请先生成支付链接。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result_url)
        self.root.update()
        self.status_var.set("支付链接已复制到剪贴板。")

    def open_link(self) -> None:
        if not self.result_url:
            messagebox.showinfo("没有链接", "请先生成支付链接。")
            return
        if not allowed_checkout_url(self.result_url):
            messagebox.showerror("链接被阻止", "链接域名不在允许列表中。")
            return
        webbrowser.open_new_tab(self.result_url)


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    CheckoutApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
