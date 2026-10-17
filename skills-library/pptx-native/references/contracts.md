# OfficeCLI JSON/HTML 契约

## 数据角色

| 产物 | 生成方式 | 生命周期 | 用途 |
| --- | --- | --- | --- |
| 能力 Schema | `officecli help all --json` | 跟随 OfficeCLI 版本 | 穷举元素、属性、枚举和 CRUD 能力 |
| 原始 PPTX | 用户上传或 OfficeCLI 创建 | 每份 deck 持久化 | 未修改 OOXML part 与 relationships 的保真事实源 |
| Replay JSON | `officecli dump deck.pptx / --json --out deck.replay.json` | 按需导出或 Web 编辑 revision | Web 场景构建、已导出范围的自包含回放 |
| Query JSON | `officecli get deck.pptx <path> --json` | 临时或缓存 | 查询、选择、属性 readback、编辑后对账 |
| HTML | `officecli view deck.pptx html -o deck.html` | 可再生缓存 | 静态预览和视觉回归 |

能力 Schema 是随运行时发布的静态数据，不需要复制到每份 deck。导入已有文件时，
原始 PPTX 是保真事实源；Replay JSON 是 Web 与 OfficeCLI 之间的有序编辑/重建
协议。Web 内存中的 scene tree 由 replay command reducer 计算得到，不需要成为
第二份持久化事实来源。

新建或修改完成的 native deck 默认只生成并交付 PPTX，不生成 Replay JSON。只有
用户明确要求 JSON 导出，或任务明确进入 Web 编辑/回放流程时，才运行 `dump`。生成
的 Replay JSON 保持 OfficeCLI 原生有序命令数组格式，可直接作为
`officecli batch --input deck.replay.json` 的输入；产品 envelope 在存储或 API
边界封装，不改写磁盘 replay 文件的直接可执行格式。

## Replay JSON

Replay JSON 是有序命令数组：

```json
[
  {"command":"remove","path":"/slide[*]"},
  {"command":"add","parent":"/","type":"slide","props":{"layout":"blank"}},
  {"command":"add","parent":"/slide[1]","type":"picture","props":{"id":"2","src":"data:image/png;base64,..."}}
]
```

Web renderer 必须按顺序归约 `add`、`set`、`remove`、`move` 和 `swap`。`raw-set`
与 `add-part` 属于保真载体：不理解时保留并回放，不把它们解释成不存在的结构化
元素。

必须保存 `dump` 返回的 warnings。OfficeCLI 1.0.139 的实测结果会跳过
`docProps/thumbnail.jpeg`、`ppt/presProps.xml`、`ppt/viewProps.xml` 等辅助 part。
因此 Replay JSON 对“已导出的命令范围”自包含，但不能单独证明整个 OOXML package
无损。编辑已有 deck 时必须在原始 PPTX 上执行 batch；只有 dump warnings 为空且
fixture 验证通过，才能宣称 JSON 单独无损重建。

图片的有效来源是 `picture.props.src`。`alt` 是 `cNvPr@descr` 对应的无障碍
描述，可能是文件名或历史下载 URL，不能据此判断图片是内嵌还是外链。

## Query JSON

Query JSON 的节点包含 `path`、`type`、`format`、`children` 等字段。图片通常只
返回 `relId`、`contentType` 和 `fileSize`，不会返回 add/set 输入字段 `src`。
因此 Query JSON 脱离原 PPTX 后无法独立恢复图片。

真正的 OOXML 外链图片使用 `a:blip@r:link`，对应 relationship 的
`TargetMode="External"`；内嵌图片使用 `a:blip@r:embed`。不要因为 `alt` 恰好
是 HTTPS URL 就将其识别成外链。

## Web 编辑

前端根据能力 Schema 构建编辑器控件，并把用户动作转换成 batch command：

```json
{
  "command": "set",
  "path": "/slide[1]/shape[@id=7]",
  "props": {"x":"2cm","y":"3cm"}
}
```

服务端应当：

1. 校验 command、元素类型、属性和值；
2. 检查 deck revision，拒绝覆盖并发更新；
3. 使用默认 atomic batch 写入 PPTX；
4. 通过 `get` 回读受影响稳定路径；
5. 更新内存 scene tree 和受影响页面预览；
6. 保存新的 replay JSON revision。

不要把 HTML DOM 反向解析为 PPTX 操作。HTML 是展示产物，command 才是编辑协议。

## HTML 预览

`view html` 生成可独立加载的静态 HTML。产品前端可以把它作为受控 iframe、静态
快照或视觉兜底，但交互选中和编辑状态应由宿主页面管理。用户编辑后不必整页刷新：
先乐观更新 scene tree，再在 batch 成功后替换受影响节点或页面资源。

`watch` 提供本地自动刷新与点击选择，适合开发和人工校验，不应被当成远端 Web
编辑器的长期网络协议。

## 版本与兼容

所有持久化 envelope 至少记录：

```json
{
  "schemaVersion": "1.0",
  "officecliVersion": "1.0.139",
  "deckRevision": "...",
  "sourcePptxAssetId": "...",
  "dumpWarnings": [],
  "commands": []
}
```

OfficeCLI 升级时重新生成能力 Schema，比较元素、属性、枚举和操作权限。出现删除、
收窄或语义变化时阻断发布；新增能力可以进入显式兼容测试后开放。

上游参考：`https://officecli.ai/SKILL.md`。运行时的 `officecli help ... --json`
始终优先于本文档中的示例。
