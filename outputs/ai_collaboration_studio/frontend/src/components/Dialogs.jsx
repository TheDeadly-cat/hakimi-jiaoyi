import { X } from "lucide-react";
import { useEffect, useState } from "react";

export function CreateRoomDialog({ open, onClose, onSubmit }) {
  const [form, setForm] = useState({ title: "", objective: "", domain: "open_collaboration" });
  useEffect(() => {
    if (open) setForm({ title: "", objective: "", domain: "open_collaboration" });
  }, [open]);
  if (!open) return null;
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <form className="dialog" onSubmit={(event) => { event.preventDefault(); onSubmit(form); }} onMouseDown={(event) => event.stopPropagation()}>
        <header><strong>新建房间</strong><button type="button" className="icon-button" onClick={onClose}><X size={18} /></button></header>
        <label>房间名称<input autoFocus required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="例如：新产品方案共创" /></label>
        <label>长期目标<textarea required value={form.objective} onChange={(event) => setForm({ ...form, objective: event.target.value })} placeholder="这个房间要持续解决什么问题？" /></label>
        <label>场景模板<select value={form.domain} onChange={(event) => setForm({ ...form, domain: event.target.value })}>
          <option value="open_collaboration">开放共创</option>
          <option value="project_research">项目研究</option>
          <option value="sports_research">体育研究</option>
          <option value="market_research">市场研究</option>
        </select></label>
        <footer><button type="button" className="secondary" onClick={onClose}>取消</button><button className="primary" type="submit">创建房间</button></footer>
      </form>
    </div>
  );
}

export function MemberDialog({ member, open, onClose, onSubmit }) {
  const [form, setForm] = useState(null);
  useEffect(() => {
    if (member) setForm({ ...member });
  }, [member]);
  if (!open || !form) return null;
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <form className="dialog member-dialog" onSubmit={(event) => { event.preventDefault(); onSubmit(form); }} onMouseDown={(event) => event.stopPropagation()}>
        <header><strong>编辑成员身份</strong><button type="button" className="icon-button" onClick={onClose}><X size={18} /></button></header>
        <div className="form-grid">
          <label>显示名<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label>身份定位<input required value={form.identity} onChange={(event) => setForm({ ...form, identity: event.target.value })} /></label>
        </div>
        <label>职责与边界<textarea className="large" required value={form.instructions} onChange={(event) => setForm({ ...form, instructions: event.target.value })} /></label>
        <div className="form-grid">
          <label>模型执行器<select value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })}><option value="openai">OpenAI</option></select></label>
          <label>模型<input value={form.model || ""} onChange={(event) => setForm({ ...form, model: event.target.value })} placeholder="留空使用默认模型" /></label>
        </div>
        <label className="checkbox-line"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} />参与讨论轮次</label>
        <footer><button type="button" className="secondary" onClick={onClose}>取消</button><button className="primary" type="submit">保存身份</button></footer>
      </form>
    </div>
  );
}

