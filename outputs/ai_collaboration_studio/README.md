# AI 共创室

AI 共创室是从哈基米交易中拆出的独立多 AI 协作项目。它不限定于行情分析，而是让用户、多个 AI 身份和共享材料在同一个房间里持续讨论、质疑、设计并形成可追踪产物。

当前第一阶段：

- 独立房间和群聊时间线。
- AI 成员的身份、职责和发言规则可编辑。
- 按顺序逐位发言，后发言者会读取并回应前序观点。
- OpenAI 作为首个真实模型适配器；同一模型可承担多个身份。
- SQLite 保存房间、成员、消息和讨论轮次。
- 不执行投注、交易、支付或其他外部高风险动作。

## 本地运行

```powershell
cd outputs\ai_collaboration_studio\frontend
npm.cmd install
npm.cmd run build
cd ..
python server.py
```

打开：http://127.0.0.1:8770/

项目会从工作区根目录的 `.env.local` 读取 `OPENAI_API_KEY`。密钥不会发送到前端，也不会写入 SQLite。

## 目录

- `docs/product_blueprint.md`：产品大纲与路线。
- `docs/design_system.md`：第一版界面规范。
- `backend/providers/`：模型适配器。
- `backend/orchestrator.py`：讨论轮次编排。
- `backend/store.py`：SQLite 持久化。
- `frontend/`：React + Vite 客户端。
- `design/ai-collaboration-studio-concept-v1.png`：首屏设计概念。

