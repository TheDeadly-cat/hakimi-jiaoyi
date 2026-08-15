const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

async function ensureElectron(getJson, debugPort) {
  try {
    await getJson("/json/version");
    return { spawned: false, stop() {} };
  } catch {}

  const electronPath = require("electron");
  const userDataDir = path.join(os.tmpdir(), `hakimi-trade-smoke-${process.pid}-${debugPort}`);
  const child = childProcess.spawn(
    electronPath,
    [`--user-data-dir=${userDataDir}`, __dirname],
    {
      cwd: __dirname,
      env: { ...process.env, HAKIMI_DEBUG_PORT: String(debugPort) },
      windowsHide: true,
      stdio: "ignore",
    }
  );
  let stopped = false;
  return {
    spawned: true,
    stop() {
      if (stopped) return;
      stopped = true;
      if (process.platform === "win32") {
        childProcess.spawnSync("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], {
          windowsHide: true,
          stdio: "ignore",
        });
      } else {
        child.kill("SIGTERM");
      }
      if (userDataDir.startsWith(os.tmpdir()) && path.basename(userDataDir).startsWith("hakimi-trade-smoke-")) {
        const sleeper = new Int32Array(new SharedArrayBuffer(4));
        for (let attempt = 0; attempt < 10; attempt += 1) {
          try {
            fs.rmSync(userDataDir, { recursive: true, force: true });
            break;
          } catch (error) {
            if (!["EBUSY", "ENOTEMPTY", "EPERM"].includes(error.code) || attempt === 9) break;
            Atomics.wait(sleeper, 0, 0, 120);
          }
        }
      }
    },
  };
}

module.exports = { ensureElectron };
