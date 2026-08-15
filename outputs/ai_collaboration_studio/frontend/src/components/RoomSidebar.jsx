import { Plus, Search } from "lucide-react";

function roomTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}

export function RoomSidebar({ rooms, activeRoomId, search, onSearch, onSelect, onCreate }) {
  const filtered = rooms.filter((room) => room.title.toLowerCase().includes(search.trim().toLowerCase()));
  return (
    <aside className="room-sidebar">
      <div className="sidebar-brand">AI 共创室</div>
      <button className="primary wide" onClick={onCreate}><Plus size={17} />新建房间</button>
      <label className="search-box">
        <Search size={16} />
        <input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="搜索房间" />
      </label>
      <div className="sidebar-section-label">我的房间</div>
      <div className="room-list">
        {filtered.map((room) => (
          <button
            key={room.id}
            className={room.id === activeRoomId ? "room-row active" : "room-row"}
            onClick={() => onSelect(room.id)}
          >
            <span className="room-dot" />
            <span className="room-copy">
              <strong>{room.title}</strong>
              <small>{room.member_count || 0} 位成员</small>
            </span>
            <time>{roomTime(room.last_message_at || room.updated_at)}</time>
          </button>
        ))}
        {!filtered.length && <div className="empty-note">没有匹配的房间</div>}
      </div>
    </aside>
  );
}

