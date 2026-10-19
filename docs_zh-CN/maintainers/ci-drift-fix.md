# 生成状态与 CI

以[维护协议](../../docs/maintainers/maintenance-contract.md)为准。普通源代码合并不再创建 `automation/canonical-repo-state`；开发检查使用临时生成数据，分发快照只在受保护的发布 PR 中更新。不得直接推送 main 或绕过保护。发布使用已经测试的同一份不可变产物。
