# ChatGPT Plus 支付长链接生成器

这是一个本地 Tkinter GUI。它接收 Access Token 或完整 Session JSON，先通过 ChatGPT Checkout 创建会话，再通过 Stripe 官方 `payment_pages/init` 接口取得真正的 Hosted 长链接。

> 非 OpenAI 或 Stripe 官方项目。本工具不会绕过地区、身份、促销、支付方式或风险控制限制。

## 运行

- Windows：双击 `run_checkout_gui.cmd`
- 命令行：`python chatgpt_checkout_gui.py`

程序不需要安装第三方 Python 包。

## 使用

1. 粘贴自己的 Access Token，或从当前登录会话取得的完整 Session JSON。
2. 从“国家/地区 + 支付渠道”预设中选择。预设会自动带入国家与币种；“自定义国家/地区”允许手动选择。
3. `plus-1-month-free` 应选择“活动 ID”模式；普通兑换码才选择 `promo_code`。不要填写完整邀请链接。
4. 点击“生成支付长链接”。
5. 打开或复制结果链接，在官方结账页核对套餐、币种、金额、优惠和续费规则后付款。

## 安全边界

- Token 只保存在程序内存里，不写入文件或配置。
- 请求只发送到 `https://chatgpt.com/backend-api/payments/checkout` 和 `https://api.stripe.com/v1/payment_pages/.../init`，不经过任何第三方代理。
- 程序只允许打开 `chatgpt.com`、`pay.openai.com` 和 `checkout.stripe.com` 的 HTTPS 链接。
- 只把最终支付链接发给付款人；绝不要发送 Access Token、Session JSON 或账号密码。
- 国家、付款人及支付方式应真实匹配。界面选择 Pix/UPI 只设置对应国家与币种，不能强制支付方式出现；程序会显示 Stripe 长链实际开放的方法。
- 标记为“OpenAI 官方”的渠道来自 OpenAI 当前支付方式说明；标记为“实验检测”的渠道只代表 Stripe 在部分集成中支持，OpenAI Plus 订阅不一定开放。
- “活动 ID”模式会先调用 ChatGPT 优惠资格接口，只有返回 `eligible` 才创建带 `promo_campaign` 的 Checkout。资格通过不代表任意支付方式都能使用优惠，最终价格必须在结账页核对。
- PayPal 当前未列在 OpenAI 官方网页订阅支付方式中；程序不能强制启用它。
- 不要把 Token 、Session JSON、Cookie 或 refresh token 提交到 GitHub Issue，也不要放入仓库文件。

该接口属于 ChatGPT 网站内部接口，可能随时变更或失效。
