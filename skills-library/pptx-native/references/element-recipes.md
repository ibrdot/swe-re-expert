# OfficeCLI PPTX 元素指令配方

本文用于把用户意图编译成 OfficeCLI 指令，不是静态 API 全量镜像。以下配方已按
OfficeCLI 1.0.139 的机器可读 help 核对；运行时仍以已安装二进制返回的 schema 为准。

## 编译规则

1. 先确定目标文件、父路径、元素类型和动作。
2. 新增元素前执行 `officecli help pptx add <element> --json`；修改元素前把
   `add` 换成 `set`。
3. 只使用对应动作标记为 `true` 的属性。不要因为属性可读就假定它可新增或修改。
4. 新增时使用 `--json`，保存返回的 `@id=` 或 `@name=` 稳定路径。
5. 用 `get <stable-path> --json` 回读，再生成后续命令。

常见意图路由：

| 用户意图 | OfficeCLI element | 典型父路径 |
| --- | --- | --- |
| 新增页面 | `slide` | `/` |
| 标题、正文、标签、几何图形 | `shape` | `/slide[N]` |
| 数据图表 | `chart` | `/slide[N]` |
| 表格 | `table` | `/slide[N]` |
| 图片 | `picture` | `/slide[N]` |
| 连线、箭头 | `connector` | `/slide[N]` |
| 组合 | `group` | `/slide[N]` |
| 演讲者备注 | `notes` | `/slide[N]` |
| 动画 | `animation` | `/slide[N]` 或 schema 指定父节点 |
| 切换效果 | `transition` | `/slide[N]` |

## 最小配方

先创建文件和页面：

```bash
officecli create deck.pptx
officecli add deck.pptx / --type slide --prop title='季度复盘' --prop background=FFFFFF --json
```

新增文字。PPTX 没有必要假设一个独立的 textbox 命令；普通文本框使用带 `text`
的 `shape`：

```bash
officecli help pptx add shape --json
officecli add deck.pptx '/slide[1]' --type shape \
  --prop text='收入同比增长 25%' \
  --prop x=2cm --prop y=3cm --prop width=12cm --prop height=2cm \
  --prop font='Arial' --prop font.ea='Microsoft YaHei' \
  --prop size=24pt --prop color=333333 --prop fill=none --json
```

新增原生图表。`chartType` 和 `data` 是新增阶段的重要输入，切换类型或替换整组
数据前必须重新检查 schema；不能假设它们支持 `set`：

```bash
officecli help pptx add chart --json
officecli add deck.pptx '/slide[1]' --type chart \
  --prop chartType=column --prop title='季度收入' \
  --prop categories='Q1,Q2,Q3,Q4' \
  --prop data='收入:10,14,18,25;成本:5,7,9,11' \
  --prop x=2cm --prop y=5cm --prop width=18cm --prop height=10cm --json
```

新增原生表格：

```bash
officecli help pptx add table --json
officecli add deck.pptx '/slide[1]' --type table \
  --prop data='季度,收入,成本;Q1,10,5;Q2,14,7' \
  --prop x=2cm --prop y=5cm --prop width=18cm --prop height=7cm \
  --prop style=medium2 --prop headerFill=4472C4 --json
```

新增图片。`src` 可以是本地文件、URL 或 data URI；它是 add/set 输入，不会由
`get` 原样返回：

```bash
officecli help pptx add picture --json
officecli add deck.pptx '/slide[1]' --type picture \
  --prop src='/workspace/assets/logo.png' \
  --prop x=20cm --prop y=1cm --prop width=4cm --prop height=2cm \
  --prop name='CompanyLogo' --prop alt='公司标志' --json
```

连接两个已有元素。先从 `add`/`get` 的返回值取得稳定路径，不要猜位置索引：

```bash
officecli help pptx add connector --json
officecli add deck.pptx '/slide[1]' --type connector \
  --prop from='/slide[1]/shape[@id=7]' \
  --prop to='/slide[1]/shape[@id=8]' \
  --prop shape=straight --prop tailEnd=arrow --json
```

## 未列出的元素

用户要求 SmartArt、Morph、扩展 transition、OLE、3D、媒体、母版、布局或其他能力
时，先运行对应的 `help pptx add|set <element> --json`。结构化 schema 有能力就使用
结构化命令；没有能力才进入 `raw` / `raw-set` / `add-part` passthrough，并保留未修改
part 与 relationships。
