# 原生 PPTX 的生成式背景图

本流程只复用相邻 `pptx` skill 的 GPT Image 生图能力。最终演示文稿仍由
OfficeCLI 维护：生成结果作为 `picture` 背景嵌入，标题、正文、图表、表格和交互
元素继续使用原生 PowerPoint 元素。

## 何时使用

用户明确要求生成背景图、氛围图、封面场景或装饰性插画时使用。已批准的视觉方案
需要一张生成式背景时也可以使用，但不要为了填满留白而默认生图。

以下内容优先保持原生，不要烘焙进背景：

- 标题、正文、数字、页码、Logo 和需要修改的标签；
- 数据图表、表格、流程节点和需要精确表达的结构；
- 需要动画、超链接、选择或 Web 编辑的元素。

## 复用现有生图入口

不要复制 `pptx` skill 的 AI Gateway 客户端。先确认相邻 skill 与命令可用：

```bash
test -f /opt/kernel/skills/pptx/SKILL.md
command -v ppt
```

在本地开发环境中，`ppt` 包装命令可能不存在；使用该 skill 自带的入口和虚拟环境：

```bash
/opt/kernel/skills/pptx/.venv/bin/python \
  /opt/kernel/skills/pptx/ppt.py --help
```

写 prompt 前读取相邻 skill 的
[`prompt-guide.md`](../../pptx/rules/prompt-guide.md) 和
[`visual-types.md`](../../pptx/rules/visual-types.md)。背景 prompt 应描述画面、色彩、
材质、构图和前景安全区，并明确排除文字、数字、Logo、水印、图表和 UI 控件，除非
用户明确要求这些内容也栅格化。

为每个 native deck 使用独立的素材 deck 名，并显式指定与 slide 对应的 `--slot`：

```bash
ppt gen native-quarterly-backgrounds \
  "16:9 editorial background, deep blue atmospheric gradient, subtle abstract data waves, quiet center-left safe area for native title and chart. No text, no numbers, no logo, no watermark, no chart, no UI." \
  --size 2048x1152 --quality high --slot 1
```

`gen` / `edit` 可能需要数分钟；调用 shell 工具时设置至少 `660000` ms 的显式超时。
失败后使用相同 deck、slot、prompt、model、size 和 quality 重试，让原 `pptx` skill
恢复已提交的队列任务，避免重复计费。

默认输出位于：

```text
/home/user/.workspace/outputs/native-quarterly-backgrounds/slide-01.png
```

修改现有背景时使用 `ppt edit ... --ref <slot|filepath|URL> --slot <N>`，不要通过
低质量缩放或重复压缩修改源图。

## 作为原生背景嵌入

先按运行时 schema 核对 `picture` 属性，然后把背景作为该 slide 的第一个视觉元素
加入。标准 16:9 PPTX 的全幅尺寸是 `33.867cm × 19.05cm`：

```bash
officecli help pptx add picture --json
officecli add deck.pptx '/slide[1]' --type picture \
  --prop src='/home/user/.workspace/outputs/native-quarterly-backgrounds/slide-01.png' \
  --prop x=0cm --prop y=0cm --prop width=33.867cm --prop height=19.05cm \
  --prop name='GeneratedBackgroundSlide1' \
  --prop alt='AI-generated abstract blue background' --json
```

新建 slide 时先加背景、再加原生前景。给已有 slide 补背景时，保存 `add --json`
返回的稳定 picture 路径，并把它移动到父节点索引 0：

```bash
officecli move deck.pptx '/slide[1]/picture[@id=100010]' --index 0 --json
```

不要猜 picture ID。使用 `get '/slide[1]' --depth 1 --json` 确认背景位于最底层，
并回读 picture 的位置、尺寸、`relId`、`contentType` 和 `fileSize`。若图片比例与
slide 不同，先根据视觉安全区计算 `crop`，不要拉伸变形。

## 交付检查

- 生成图片中没有意外文字、数字、Logo、水印或伪造数据；
- 背景是 slide 的底层 `picture`，原生前景仍可选择和编辑；
- 源 PNG 保留在素材目录，PPTX 中使用内嵌 relationship；
- HTML 和截图检查文字对比度、裁切、安全区、重叠与全页覆盖；
- 最终 `dump` 生成的 replay JSON 可回放背景 picture 与全部原生元素。
