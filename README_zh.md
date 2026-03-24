# copilot-computer-use

[English](README.md) | **中文**

> **全球首个基于 GitHub Copilot API 的免费 Computer Use Agent**

截屏 → 视觉分析 → 操作执行 —— 一切通过你的 Copilot 订阅完成，无需额外付费。

## 为什么做这个？

目前所有 Computer Use Agent 都需要昂贵的 Vision API（每次截屏 $0.01-0.05）。我们发现 **GitHub Copilot API 支持 base64 图片输入**（通过 `copilot-vision-request: true` 头），这意味着你可以用已有的 Copilot 订阅构建一个**零额外成本**的 Computer Use Agent。

更重要的是：**GPT-4o 在 Copilot 中是 0 倍率模型（完全免费，不消耗 Premium 配额）！**

## 工作原理

```
┌──────────────────────────────────────────────┐
│              Agent 控制循环                     │
│                                               │
│  1. 📸 截屏 (mss + Pillow)                     │
│  2. 🔄 编码为 base64 PNG                        │
│  3. 👁️ 通过 Copilot Vision API 分析              │
│     (copilot-vision-request: true)            │
│  4. 🧠 规划下一步操作                             │
│  5. ⚡ 执行操作 (pyautogui)                     │
│  6. 🔁 重复直到任务完成                           │
└──────────────────────────────────────────────┘
```

## 核心优势

| 对比项 | 传统 Agent | copilot-computer-use |
|--------|-----------|---------------------|
| Vision API 费用 | $0.01-0.05/截屏 | **$0（Copilot 包含）** |
| 文本推理费用 | $0.003-0.06/请求 | **$0（Copilot 包含）** |
| 月成本 | $20-100+ | **$10/月（Copilot）或免费** |
| 可用模型 | 单一提供商 | GPT-4o, Claude, Gemini |
| GPT-4o 消耗 Premium | — | **0（完全免费）** |

## 前提条件

- Python 3.9+
- GitHub 账号 + Copilot 订阅（Individual/Business/Enterprise 均可）
- macOS 或 Linux

## 快速开始

```bash
# 克隆
git clone https://github.com/Zey413/copilot-computer-use.git
cd copilot-computer-use

# 安装
pip install -e .

# GitHub 认证（一次性）
python -m src.copilot.auth

# 运行
python -m src.main "打开 Chrome 搜索今天的天气"
```

## 命令行参数

```bash
python -m src.main "任务描述" [选项]

选项:
  --model MODEL          使用的模型 (默认: gpt-4o, 免费!)
  --max-iterations N     最大迭代次数 (默认: 50)
  --delay SECONDS        迭代间隔秒数 (默认: 2.0)
  --max-width PIXELS     截屏最大宽度 (默认: 1280)
  --max-height PIXELS    截屏最大高度 (默认: 800)
  --grid                 启用坐标网格覆盖层 (提升定位精度)
  --grid-spacing PIXELS  网格间距 (默认: 100)
  --xdotool              Linux: 使用 xdotool 输入 (更好的 Unicode 支持)
```

## 模型费用速查

| 模型 | Premium 倍率 | 建议 |
|------|-------------|------|
| **gpt-4o** | **0（免费）** | ✅ 推荐默认 |
| **gpt-4.1** | **0（免费）** | ✅ 推荐 |
| claude-haiku-4.5 | 0.33x | 🟡 省配额选择 |
| claude-sonnet-4 | 1x | 🟡 高质量 |
| claude-opus-4.6 | 3x | 🔴 谨慎使用 |

## Copilot Vision 工作原理

关键发现：Copilot 的 `chat/completions` API 接受 base64 图片，但需要特殊头：

```python
headers = {
    "copilot-vision-request": "true",  # 必须！否则 400 错误
    "editor-version": "vscode/1.104.3",
    # ... 其他伪装头
}
body = {
    "model": "gpt-4o",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述屏幕内容"},
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64,iVBORw0KGgo..."
            }}
        ]
    }]
}
```

⚠️ 注意：外部 URL 图片不支持，**只支持 base64 Data URL**。

## 特性

- ✅ GitHub OAuth Device Flow 认证（一次性设置）
- ✅ JWT 自动刷新（过期前 60s）
- ✅ VS Code 版本伪装
- ✅ 429 Rate Limit 自动重试（指数退避）
- ✅ 模型费用感知 + 使用统计
- ✅ 坐标网格覆盖层（提升 AI 定位精度）
- ✅ macOS + Linux 双平台支持
- ✅ 26 个单元测试
- ✅ GitHub Actions CI

## 项目架构

```
src/
├── main.py                 # CLI 入口
├── copilot/
│   ├── auth.py             # GitHub OAuth + JWT 刷新
│   ├── client.py           # API 客户端 (带重试 + 费用感知)
│   └── config.py           # 请求头伪装 + 端点配置
├── agent/
│   ├── loop.py             # 核心 Agent 循环
│   ├── actions.py          # 10 种操作类型
│   └── planner.py          # 任务分解器
├── screen/
│   ├── capture.py          # 截屏 + 缩放
│   └── annotate.py         # 网格/十字准星/编号标注
└── executor/
    ├── base.py             # 抽象执行器
    ├── macos.py            # macOS 执行器
    └── linux.py            # Linux 执行器 (pyautogui + xdotool)
```

## 研究背景

本项目基于对以下项目的深入研究（详见 Review #001-#016）：

- **[Raven](https://github.com/nocoo/raven)** — 证明了 Copilot API 可以通过 Anthropic↔OpenAI 格式翻译代理
- **[copilot-api](https://github.com/ericc-ch/copilot-api)** — 早期 Copilot 逆向工程
- **[self-operating-computer](https://github.com/OthersideAI/self-operating-computer)** — 轻量级 Computer Use 参考架构
- **[OpenClaw](https://github.com/openclaw/openclaw)** — 全功能桌面 Agent（60k+ stars）

## 局限性

- 🧪 实验性项目，非生产级软件
- ⚡ Copilot 有 Rate Limit；过于频繁的截屏可能被限流
- ⚖️ 灰色地带：通过代理使用 Copilot API 可能不被官方明确允许
- 🖼️ PNG 最可靠；JPEG 可用；WebP 可能有问题
- 🪟 暂不支持 Windows

## 许可

MIT

## 致谢

- [Raven](https://github.com/nocoo/raven) — Copilot API 认证与格式翻译的灵感来源
- [self-operating-computer](https://github.com/OthersideAI/self-operating-computer) — 轻量级 Computer Use 架构参考
- [copilot-api](https://github.com/ericc-ch/copilot-api) — 早期 Copilot 逆向工程工作
