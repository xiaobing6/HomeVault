# HomeVault Phase 1 Handoff

日期：2026-06-18

## 当前状态

当前远端分支：

```text
origin/phase-1-foundation
```

已完成并推送：

- Task 1: Backend scaffold and health API
- Task 2: Database base, auth models, and migration
- Task 2 quality fixes: SQLite foreign key enforcement, safe owned-relationship cascades, `ExternalIdentity` relationship, stronger database and Alembic tests

当前最新提交：

```text
05d0c02 test: harden auth database model
```

## 下一步

继续时不要重做 Task 1 或 Task 2。

下一项应从计划文件里的 Task 3 开始：

```text
docs/superpowers/plans/2026-06-18-home-vault-phase-1-foundation.md
```

Task 3 是：

```text
Password Hashing And Token Security
```

## 继续使用的 Superpowers 流程

新的电脑或新的 Codex 会话开始后，应先使用：

```text
superpowers:using-superpowers
```

然后根据已有实现计划继续执行，应使用：

```text
superpowers:subagent-driven-development
```

执行要求：

- 从 Task 3 开始。
- 每个 Task 按实现、规格复核、代码质量复核的顺序推进。
- 不要跨阶段自动进入下一阶段；Phase 1 完成后再写下一阶段计划。

## 已验证命令

在 `backend` 目录下执行：

```powershell
python -m pytest tests/test_health.py tests/test_database_models.py -v -p no:cacheprovider --basetemp ..\pytest-basetemp
```

最近一次结果：

```text
6 passed, 1 warning
```

这个 warning 来自现有 FastAPI/Starlette TestClient 依赖路径，不是当前业务代码失败。

## 拉取方式

在另一台电脑上：

```powershell
git clone https://github.com/xiaobing6/HomeVault.git
Set-Location HomeVault
git checkout phase-1-foundation
```

如果仓库默认分支已经指向 `phase-1-foundation`，也可以 clone 后直接确认：

```powershell
git branch --show-current
git log --oneline -5
```
