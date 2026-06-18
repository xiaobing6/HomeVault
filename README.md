# HomeVault

HomeVault 是一个家庭物品管理系统。第一阶段包含 FastAPI 后端、SQLite 数据库迁移、token 登录、RBAC 基础角色，以及 Vue/Element Plus 登录和仪表盘骨架。

## 后端启动

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m app.cli
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

默认管理员账号来自 `backend/.env.example`：

- 账号：`admin`
- 密码：`ChangeMe123!`

## 前端启动

```powershell
Set-Location frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 测试

```powershell
Set-Location backend
python -m pytest -v

Set-Location ..\frontend
npm run build
```
