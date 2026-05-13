(function () {
  "use strict";

  var SCRIPT = document.currentScript;
  var API_BASE = (SCRIPT && SCRIPT.dataset.apiBase) || "";

  var STYLE = document.createElement("style");
  STYLE.textContent =
    "#ppu-widget{position:fixed;bottom:24px;right:24px;z-index:999999;direction:rtl;font-family:'Segoe UI',Tahoma,sans-serif}" +
    "#ppu-widget *{margin:0;padding:0;box-sizing:border-box}" +
    "#ppu-toggle{width:60px;height:60px;border-radius:50%;border:none;background:linear-gradient(135deg,#1a3a5c,#2d6a9f);color:#fff;font-size:28px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,0.25);transition:transform .2s,box-shadow .2s;display:flex;align-items:center;justify-content:center}" +
    "#ppu-toggle:hover{transform:scale(1.1);box-shadow:0 6px 24px rgba(0,0,0,0.35)}" +
    "#ppu-panel{position:fixed;bottom:96px;right:24px;width:380px;height:560px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.18);display:none;flex-direction:column;overflow:hidden;max-height:calc(100vh - 120px)}" +
    "#ppu-panel.open{display:flex}" +
    "#ppu-header{background:linear-gradient(135deg,#1a3a5c,#2d6a9f);color:#fff;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}" +
    "#ppu-header h3{font-size:1em;font-weight:600}" +
    "#ppu-close{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;opacity:.8;padding:0 4px}" +
    "#ppu-close:hover{opacity:1}" +
    "#ppu-messages{flex:1;overflow-y:auto;padding:16px;background:#f8f9fa}" +
    "#ppu-widget .ppu-msg{margin-bottom:20px;padding:10px 14px;border-radius:12px;line-height:1.6;font-size:0.9em;max-width:88%;word-wrap:break-word}" +
    "#ppu-widget .ppu-msg.user{background:#e3f2fd;margin-left:auto;border-bottom-left-radius:4px}" +
    "#ppu-widget .ppu-msg.bot{background:#fff;margin-right:auto;border-bottom-right-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,0.06)}" +
    "#ppu-widget .ppu-msg.bot .ppu-link{display:inline-block;margin-top:4px;padding:3px 10px;background:#e8f0fe;border-radius:5px;font-size:0.78em;color:#1a73e8;text-decoration:none}" +
    "#ppu-widget .ppu-msg.bot .ppu-link:hover{background:#d2e3fc;text-decoration:underline}" +
    ".ppu-typing{color:#888;font-style:italic;font-size:0.85em}" +
    ".ppu-excerpt{font-size:0.85em;color:#444;margin-top:4px;padding-right:8px;border-right:2px solid #2d6a9f}" +
    ".ppu-source-label{font-size:0.78em;color:#888;margin-top:6px}" +
    "#ppu-input-wrap{display:flex;gap:6px;padding:12px 16px;border-top:1px solid #e0e0e0;background:#fff;flex-shrink:0}" +
    "#ppu-input-wrap input{flex:1;padding:10px 14px;border:2px solid #ddd;border-radius:24px;font-size:0.9em;outline:none}" +
    "#ppu-input-wrap input:focus{border-color:#2d6a9f}" +
    "#ppu-input-wrap button{padding:10px 18px;background:#2d6a9f;color:#fff;border:none;border-radius:24px;font-size:0.9em;cursor:pointer;white-space:nowrap}" +
    "#ppu-input-wrap button:disabled{opacity:.5;cursor:not-allowed}" +
    "@media(max-width:480px){#ppu-panel{right:0;bottom:0;width:100%;height:100%;max-height:100%;border-radius:0}#ppu-toggle{bottom:16px;right:16px}}";
  document.head.appendChild(STYLE);

  var CONTAINER = document.createElement("div");
  CONTAINER.id = "ppu-widget";
  CONTAINER.innerHTML =
    '<button id="ppu-toggle" aria-label="فتح المحادثة">\uD83D\uDCAC</button>' +
    '<div id="ppu-panel">' +
    '<div id="ppu-header"><h3>\u0645\u0633\u0627\u0639\u062F \u062C\u0627\u0645\u0639\u0629 \u0628\u0648\u0644\u064A\u062A\u0643\u0646\u0643 \u0641\u0644\u0633\u0637\u064A\u0646</h3><button id="ppu-close">\u2716</button></div>' +
    '<div id="ppu-messages">' +
    '<div class="ppu-msg bot">\u0645\u0631\u062D\u0628\u064B\u0627 \u0628\u0643 \u0641\u064A \u0645\u0633\u0627\u0639\u062F \u062C\u0627\u0645\u0639\u0629 \u0628\u0648\u0644\u064A\u062A\u0643\u0646\u0643 \u0641\u0644\u0633\u0637\u064A\u0646.<br>\u064A\u0645\u0643\u0646\u0643 \u0633\u0624\u0627\u0644\u064A \u0639\u0646:<br>\u2022 \u0623\u0631\u0642\u0627\u0645 \u0627\u0644\u062A\u0648\u0627\u0635\u0644 \u0648\u0627\u0644\u0639\u0646\u0648\u0627\u0646<br>\u2022 \u0627\u0644\u0643\u0644\u064A\u0627\u062A \u0648\u0627\u0644\u062A\u062E\u0635\u0635\u0627\u062A<br>\u2022 \u0634\u0631\u0648\u0637 \u0627\u0644\u0642\u0628\u0648\u0644 \u0648\u0627\u0644\u062A\u0633\u062C\u064A\u0644<br>\u2022 \u0627\u0644\u0631\u0633\u0648\u0645 \u0627\u0644\u062F\u0631\u0627\u0633\u064A\u0629<br>\u2022 \u0627\u0644\u062A\u0642\u0648\u064A\u0645 \u0627\u0644\u0623\u0643\u0627\u062F\u064A\u0645\u064A<br>\u2022 \u0631\u0648\u0627\u0628\u0637 \u0627\u0644\u062E\u062F\u0645\u0627\u062A</div>' +
    "</div>" +
    '<div id="ppu-input-wrap"><input id="ppu-input" placeholder="\u0627\u0643\u062A\u0628 \u0633\u0624\u0627\u0644\u0643 \u0647\u0646\u0627..." autofocus><button id="ppu-send">\u0625\u0631\u0633\u0627\u0644</button></div>' +
    "</div>";
  document.body.appendChild(CONTAINER);

  var panel = document.getElementById("ppu-panel");
  var toggle = document.getElementById("ppu-toggle");
  var close = document.getElementById("ppu-close");
  var messages = document.getElementById("ppu-messages");
  var input = document.getElementById("ppu-input");
  var send = document.getElementById("ppu-send");

  function setPanel(open) {
    panel.classList.toggle("open", open);
    toggle.style.display = open ? "none" : "flex";
    if (open) setTimeout(function () { input.focus(); }, 200);
  }

  toggle.addEventListener("click", function () { setPanel(true); });
  close.addEventListener("click", function () { setPanel(false); });

  function addMsg(text, cls, sources) {
    var div = document.createElement("div");
    div.className = "ppu-msg " + cls;
    var html = text;
    if (sources && sources.length > 0) {
      html += '<div class="ppu-source-label">\u0627\u0644\u0645\u0635\u0627\u062F\u0631:</div>';
      for (var i = 0; i < Math.min(sources.length, 3); i++) {
        var label = sources[i].replace(/https?:\/\//, "").split("/")[0];
        html += '<a class="ppu-link" href="' + sources[i] + '" target="_blank">' + label + "</a> ";
      }
    }
    div.innerHTML = html;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function addTyping() {
    var div = document.createElement("div");
    div.className = "ppu-msg bot ppu-typing";
    div.id = "ppu-typing";
    div.textContent = "\u062C\u0627\u0631\u064A \u0627\u0644\u0628\u062D\u062B...";
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() {
    var t = document.getElementById("ppu-typing");
    if (t) t.remove();
  }

  function sendQuery() {
    var q = input.value.trim();
    if (!q) return;
    addMsg(q, "user");
    input.value = "";
    send.disabled = true;
    addTyping();
    fetch(API_BASE + "/query?q=" + encodeURIComponent(q))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        removeTyping();
        if (data.text) addMsg(data.text, "bot", data.sources || []);
      })
      .catch(function () {
        removeTyping();
        addMsg("\u0639\u0630\u0631\u064B\u0627\u060C \u062D\u062F\u062B \u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0627\u062A\u0635\u0627\u0644. \u062D\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649.", "bot");
      })
      .finally(function () { send.disabled = false; input.focus(); });
  }

  send.addEventListener("click", sendQuery);
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") sendQuery(); });
})();
