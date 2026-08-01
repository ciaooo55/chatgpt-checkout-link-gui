# 💳 ChatGPT Plus 支付长链接生成器

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-Tkinter-4B8BBE)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows11&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-standard%20library-success)

一个本地 Tkinter 图形工具：使用用户自己提供的 ChatGPT Access Token 或 Session JSON 创建 Checkout 会话，再请求 Stripe `payment_pages/init` 获取可在浏览器打开的托管支付长链接。

> [!CAUTION]
> 这不是 OpenAI 或 Stripe 官方项目。程序依赖 ChatGPT 网站内部接口，可能随时变化或失效；它不能绕过地区、身份、优惠资格、付款方式或风控限制。最终套餐、币种、金额、优惠和续费规则只以官方结账页面显示为准。

## 📌 项目速览

| 项目 | 说明 |
| --- | --- |
| 仓库名 | `chatgpt-checkout-link-gui` |
| 运行方式 | Windows 批处理或 Python 命令行 |
| 第三方依赖 | 无；只使用 Python 标准库和 Tkinter |
| 输入 | 当前用户自己的 Access Token、Bearer 文本或含 Token 的 Session JSON |
| 输出 | HTTPS 托管结账链接及 Stripe 返回的可用付款方式 |
| 网络目标 | `chatgpt.com` 与 `api.stripe.com` |
| 本地持久化 | 不保存 Token、Session JSON 或生成结果到配置文件 |

## ✨ 真实功能

- 从原始 Token、`Bearer ...` 文本或嵌套 Session JSON 中识别 Access Token。
- 提供多个国家/地区和币种组合，以及 Pix、UPI、GoPay、Link 等付款方式预设。
- 支持不使用优惠、`promo_campaign` 活动 ID 和普通 `promo_code` 三种模式。
- 活动 ID 模式会先请求优惠资格检查；只有返回符合资格才继续创建对应 Checkout。
- 从 ChatGPT Checkout 响应中解析会话信息，并向 Stripe 初始化接口换取 Hosted 长链接。
- 展示 Stripe 实际返回的付款方式，便于和所选预设对照。
- 生成过程在后台线程运行，界面支持清空输入、复制链接和用默认浏览器打开。
- 只允许打开 `chatgpt.com`、`pay.openai.com` 和 `checkout.stripe.com` 的 HTTPS 链接。

预设只会设置国家、币种和期望的付款方式，不会强制 Stripe 或 OpenAI 开放某种渠道。“实验检测”表示 Stripe 在部分集成中存在该方式，不代表 ChatGPT Plus 必然支持。

## 🚀 安装与运行

### 环境要求

- Windows 10/11。
- Python 3.10 或更高版本。
- Python 安装包含 Tkinter；Windows 官方 Python 安装包通常默认包含。
- 能正常访问 ChatGPT 和 Stripe 的网络环境。

本项目不需要 `pip install`。

### Windows 双击运行

将仓库完整下载到本地，双击：

```text
run_checkout_gui.cmd
```

启动脚本会先尝试 `py -3`，找不到 Python Launcher 时回退到 `python`。

### 命令行运行

```powershell
python .\chatgpt_checkout_gui.py
```

## 🧭 使用方法

1. 在输入框中粘贴你自己当前会话的 Access Token 或完整 Session JSON。项目不提供凭据获取、共享或代登录功能。
2. 选择“国家/地区 + 支付渠道”预设；自定义模式允许另选国家和币种。
3. 选择优惠模式：
   - 不使用优惠：不提交优惠字段。
   - 活动 ID：用于 `promo_campaign` 类型的活动标识。
   - 普通优惠码：提交 `promo_code`。
4. 填写对应活动 ID 或优惠码；不要粘贴完整邀请链接。
5. 点击“生成支付长链接”，等待资格检查、Checkout 创建和 Stripe 初始化完成。
6. 查看程序显示的实际付款方式，再复制或打开链接。
7. 在官方页面逐项核对账号、套餐、金额、币种、优惠和自动续费条件后再付款。

> [!IMPORTANT]
> 选择 Pix、UPI 或其他预设不代表该方式一定出现。账号状态、付款人所在地、币种、订阅类型和支付处理器都会影响最终结果。

## ⚙️ 配置与接口

程序没有 `.env` 或用户配置文件。地区、付款方式预设和接口常量均定义在 `chatgpt_checkout_gui.py` 中：

| 常量 / 数据 | 用途 |
| --- | --- |
| `CHECKOUT_ENDPOINT` | 创建 ChatGPT Checkout |
| `PROMO_CHECK_ENDPOINT` | 检查活动 ID 资格 |
| `STRIPE_INIT_BASE` | 初始化 Stripe Payment Page |
| `COUNTRIES` | 国家代码与币种列表 |
| `PAYMENT_PRESETS` | 界面中的地区和期望付款方式组合 |
| `ALLOWED_LINK_HOSTS` | 可复制/打开的结账链接域名白名单 |

修改接口版本、请求字段或预设前，请确认服务端当前行为，并保留域名白名单检查。内部接口没有稳定性承诺。

## 🗂️ 目录结构

```text
chatgpt-checkout-link-gui/
├─ chatgpt_checkout_gui.py   # GUI、输入解析与网络请求
├─ run_checkout_gui.cmd      # Windows 启动入口
├─ .gitignore
└─ README.md
```

## 🛡️ 安全与隐私

- Token 和 Session JSON 只保存在当前 Python 进程内存中；程序没有把它们写入文件的逻辑。
- 请求会携带敏感授权信息到 ChatGPT 官方域名；Stripe 初始化请求使用 Checkout 响应中的发布密钥。
- 不要把 Access Token、Session JSON、Cookie、刷新令牌、截图或错误响应提交到 GitHub Issue。
- 不要向付款人发送 Token 或账号密码；如确需分享，只分享已核验域名的最终结账链接。
- 关闭程序可清除当前进程内存中的输入；剪贴板内容不会由程序自动清理，请自行覆盖。
- 生成的长链接也可能关联特定 Checkout 会话，不应公开发布或长期保存。
- 使用真实且匹配的国家、付款人和支付方式信息，遵守 OpenAI、Stripe 及当地法律规则。
- 如果返回域名不在白名单、页面金额异常或浏览器出现证书警告，请立即停止。

## 🧪 开发与测试

当前仓库没有自动化测试套件。提交改动前至少执行语法检查：

```powershell
python -m compileall .\chatgpt_checkout_gui.py
```

建议手动验证：

1. 空输入、无效 JSON、Bearer 文本和嵌套 Session JSON 的提示是否正确。
2. 不使用优惠、活动 ID 和普通优惠码三种分支。
3. 请求超时、HTTP 错误、资格不符和响应字段缺失时的错误显示。
4. 自定义地区、预设切换、复制、打开和清空按钮。
5. 非 HTTPS 或非白名单域名是否被拒绝。

网络测试会真实调用服务端接口，可能创建 Checkout 会话。请只使用自己的测试账号，不要把有效凭据写入测试文件、命令历史或日志。
