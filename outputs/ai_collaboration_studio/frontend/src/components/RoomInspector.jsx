import { CheckSquare, Database, Edit3, Pause, Play, Users } from "lucide-react";

function statusText(status) {
  if (status === "speaking") return "发言中";
  if (status === "done") return "已完成";
  if (status === "failed") return "未完成";
  return "等待";
}

export function RoomInspector({ room, members, providers, roundState, onEditMember, onStartRound, onPause }) {
  const providerReady = providers.some((provider) => provider.configured);
  return (
    <aside className="room-inspector">
      <section className="inspector-section objective-section" id="inspector-rooms">
        <div className="section-heading"><strong>本轮目标</strong><Edit3 size={15} /></div>
        <p>{room?.objective || "等待用户定义目标。"}</p>
        <div className="round-controls">
          <button className="primary" onClick={onStartRound} disabled={roundState.running || !providerReady}>
            <Play size={15} />开始一轮
          </button>
          <button className="secondary compact" onClick={onPause} disabled={!roundState.running} title="暂停当前轮次">
            <Pause size={15} />暂停
          </button>
        </div>
        {!providerReady && <div className="provider-warning">当前没有可用模型执行器</div>}
      </section>

      <section className="inspector-section">
        <div className="section-heading"><strong>本轮发言顺序</strong><span>{roundState.running ? "进行中" : "待开始"}</span></div>
        <ol className="speaker-order">
          {members.filter((member) => member.enabled).map((member, index) => {
            const status = roundState.memberStatus[member.id] || "queued";
            return (
              <li key={member.id} className={status}>
                <span className="order-number">{index + 1}</span>
                <span className="mini-avatar" style={{ background: member.avatar_color }}>{member.name.slice(0, 1)}</span>
                <span className="speaker-copy"><strong>{member.name}</strong><small>{statusText(status)}</small></span>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="inspector-section" id="inspector-members">
        <div className="section-heading"><strong><Users size={15} />成员与身份</strong><span>{members.length} 位</span></div>
        <div className="member-list">
          {members.map((member) => (
            <button key={member.id} className="member-row" onClick={() => onEditMember(member)}>
              <span className="mini-avatar" style={{ background: member.avatar_color }}>{member.name.slice(0, 1)}</span>
              <span><strong>{member.name}</strong><small>{member.identity}</small></span>
              <i className={member.enabled ? "online" : "offline"} />
            </button>
          ))}
        </div>
      </section>

      <section className="inspector-section compact-section" id="inspector-materials">
        <div className="section-heading"><strong><Database size={15} />共享资料</strong></div>
        <div className="empty-resource">尚未添加共享材料</div>
      </section>

      <section className="inspector-section compact-section" id="inspector-artifacts">
        <div className="section-heading"><strong><CheckSquare size={15} />结论与待办</strong></div>
        <div className="empty-resource">讨论完成后由用户确认</div>
      </section>
    </aside>
  );
}
