async function jsonRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `请求失败：${response.status}`);
  }
  return data;
}

export const api = {
  bootstrap: (roomId = "") => jsonRequest(`/api/bootstrap${roomId ? `?room=${encodeURIComponent(roomId)}` : ""}`),
  room: (roomId) => jsonRequest(`/api/rooms/${encodeURIComponent(roomId)}`),
  createRoom: (payload) => jsonRequest("/api/rooms", { method: "POST", body: JSON.stringify(payload) }),
  sendMessage: (roomId, content) => jsonRequest(`/api/rooms/${encodeURIComponent(roomId)}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  }),
  updateMember: (roomId, memberId, payload) => jsonRequest(
    `/api/rooms/${encodeURIComponent(roomId)}/members/${encodeURIComponent(memberId)}`,
    { method: "PATCH", body: JSON.stringify(payload) },
  ),
};

export async function streamRound(roomId, objective, onEvent, signal) {
  const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/rounds/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ objective }),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`讨论轮次启动失败：${response.status}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      onEvent(JSON.parse(line));
    }
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
}

