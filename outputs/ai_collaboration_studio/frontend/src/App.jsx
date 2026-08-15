import { Menu, Pause, Settings, Users } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, streamRound } from "./api";
import { ChatTimeline } from "./components/ChatTimeline";
import { Composer } from "./components/Composer";
import { CreateRoomDialog, MemberDialog } from "./components/Dialogs";
import { IconRail } from "./components/IconRail";
import { RoomInspector } from "./components/RoomInspector";
import { RoomSidebar } from "./components/RoomSidebar";

const emptyRoundState = () => ({ running: false, memberStatus: {}, roundId: "" });

export default function App() {
  const [rooms, setRooms] = useState([]);
  const [active, setActive] = useState(null);
  const [providers, setProviders] = useState([]);
  const [search, setSearch] = useState("");
  const [composer, setComposer] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [typingMember, setTypingMember] = useState(null);
  const [roundState, setRoundState] = useState(emptyRoundState);
  const [transientErrors, setTransientErrors] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [railSection, setRailSection] = useState("rooms");
  const abortRef = useRef(null);

  const room = active?.room || null;
  const members = active?.members || [];
  const messages = active?.messages || [];
  const providerReady = useMemo(() => providers.some((provider) => provider.configured), [providers]);

  useEffect(() => {
    api.bootstrap()
      .then((data) => {
        setRooms(data.rooms || []);
        setActive(data.active);
        setProviders(data.providers || []);
      })
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false));
    return () => abortRef.current?.abort();
  }, []);

  const loadRoom = async (roomId) => {
    if (roundState.running) return;
    setError("");
    try {
      const data = await api.room(roomId);
      setActive({ room: data.room, members: data.members, messages: data.messages, latest_round: data.latest_round });
      setProviders(data.providers || providers);
      setRoundState(emptyRoundState());
      setTransientErrors([]);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const refreshRooms = async (roomId = room?.id) => {
    const data = await api.bootstrap(roomId || "");
    setRooms(data.rooms || []);
    if (data.active) setActive(data.active);
    setProviders(data.providers || providers);
  };

  const sendMessage = async () => {
    const content = composer.trim();
    if (!content || !room || roundState.running) return;
    setComposer("");
    try {
      const data = await api.sendMessage(room.id, content);
      setActive((current) => ({ ...current, messages: [...current.messages, data.message] }));
    } catch (requestError) {
      setComposer(content);
      setError(requestError.message);
    }
  };

  const startRound = async () => {
    if (!room || roundState.running || !providerReady) return;
    const objective = composer.trim() || room.objective;
    setComposer("");
    setError("");
    setTransientErrors([]);
    setRoundState({ running: true, memberStatus: Object.fromEntries(members.filter((member) => member.enabled).map((member) => [member.id, "queued"])), roundId: "" });
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamRound(room.id, objective, (event) => {
        if (event.type === "round_started") {
          setActive((current) => ({ ...current, messages: [...current.messages, event.user_message] }));
          setRoundState((current) => ({ ...current, roundId: event.round.id }));
        } else if (event.type === "speaker_started") {
          setTypingMember(event.member);
          setRoundState((current) => ({ ...current, memberStatus: { ...current.memberStatus, [event.member.id]: "speaking" } }));
        } else if (event.type === "message") {
          setTypingMember(null);
          setActive((current) => ({ ...current, messages: [...current.messages, event.message] }));
          setRoundState((current) => ({ ...current, memberStatus: { ...current.memberStatus, [event.member.id]: "done" } }));
        } else if (event.type === "speaker_failed") {
          setTypingMember(null);
          if (event.message) {
            setActive((current) => ({ ...current, messages: [...current.messages, event.message] }));
          } else {
            setTransientErrors((current) => [...current, { id: `${event.member.id}-${Date.now()}`, name: event.member.name, message: event.error }]);
          }
          setRoundState((current) => ({ ...current, memberStatus: { ...current.memberStatus, [event.member.id]: "failed" } }));
        } else if (event.type === "round_completed") {
          setTypingMember(null);
          setRoundState((current) => ({ ...current, running: false }));
        } else if (event.type === "error") {
          throw new Error(event.error || "讨论轮次失败");
        }
      }, controller.signal);
      await refreshRooms(room.id);
    } catch (requestError) {
      if (requestError.name !== "AbortError") setError(requestError.message);
      setTypingMember(null);
      setRoundState((current) => ({ ...current, running: false }));
    } finally {
      abortRef.current = null;
    }
  };

  const pauseRound = () => {
    abortRef.current?.abort();
    setTypingMember(null);
    setRoundState((current) => ({ ...current, running: false }));
  };

  const navigateRail = (section) => {
    setRailSection(section);
    if (section === "rooms") {
      setInspectorOpen(false);
      document.querySelector(".room-search input")?.focus();
      return;
    }
    setInspectorOpen(true);
    requestAnimationFrame(() => document.getElementById(`inspector-${section}`)?.scrollIntoView({ block: "start" }));
  };

  const createRoom = async (form) => {
    try {
      const data = await api.createRoom(form);
      setCreateOpen(false);
      await refreshRooms(data.room.id);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const saveMember = async (form) => {
    try {
      const data = await api.updateMember(room.id, form.id, form);
      setActive((current) => ({ ...current, members: current.members.map((member) => member.id === data.member.id ? data.member : member) }));
      setEditingMember(null);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  if (loading) return <div className="boot-screen">正在打开 AI 共创室…</div>;

  return (
    <div className="app-shell">
      <IconRail activeSection={railSection} onNavigate={navigateRail} />
      <RoomSidebar rooms={rooms} activeRoomId={room?.id} search={search} onSearch={setSearch} onSelect={loadRoom} onCreate={() => setCreateOpen(true)} />
      <main className="conversation-panel">
        <header className="conversation-header">
          <div>
            <strong>{room?.title || "AI 共创室"}</strong>
            <span><Users size={14} />{members.filter((member) => member.enabled).length} 位成员</span>
            <span className={roundState.running ? "status live" : "status"}>{roundState.running ? "进行中" : "待讨论"}</span>
          </div>
          <div className="header-actions">
            {roundState.running && <button className="secondary" onClick={pauseRound}><Pause size={15} />暂停</button>}
            <button className="secondary inspector-toggle" onClick={() => setInspectorOpen((value) => !value)}><Menu size={16} />房间信息</button>
            <button className="icon-button" title="编辑成员身份" onClick={() => members[0] && setEditingMember(members[0])}><Settings size={18} /></button>
          </div>
        </header>
        {error && <div className="global-error">{error}<button onClick={() => setError("")}>关闭</button></div>}
        <ChatTimeline messages={messages} members={members} typingMember={typingMember} transientErrors={transientErrors} />
        <Composer value={composer} onChange={setComposer} onSend={sendMessage} onStartRound={startRound} disabled={roundState.running} members={members} />
      </main>
      <div className={inspectorOpen ? "inspector-wrap open" : "inspector-wrap"}>
        <RoomInspector room={room} members={members} providers={providers} roundState={roundState} onEditMember={setEditingMember} onStartRound={startRound} onPause={pauseRound} />
      </div>
      <CreateRoomDialog open={createOpen} onClose={() => setCreateOpen(false)} onSubmit={createRoom} />
      <MemberDialog member={editingMember} open={Boolean(editingMember)} onClose={() => setEditingMember(null)} onSubmit={saveMember} />
    </div>
  );
}
