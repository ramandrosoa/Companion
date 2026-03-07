// ── PEP STATE ──────────────────────────────────────────────
let pepOpen = false;

// Restore messages from sessionStorage so they survive page navigation
const MSG_KEY = 'pep_messages';

function saveMsgs() {
  const msgs = document.getElementById('pepMsgs');
  sessionStorage.setItem(MSG_KEY, msgs.innerHTML);
}

function loadMsgs() {
  const saved = sessionStorage.getItem(MSG_KEY);
  if (saved) {
    document.getElementById('pepMsgs').innerHTML = saved;
    document.getElementById('pepMsgs').scrollTop = 999999;
  } else {
    // First ever open — show greeting
    addMsg('pep', getGreeting());
  }
}

function getGreeting() {
  const greetings = {
    1: "HI!! I AM PEP!! ASK ME ANYTHING!! 🌟",
    2: "hey, i'm pep. ask me stuff 👋",
    3: "Hey! I'm Pep. What would you like to know? 😊",
    4: "Hello. I'm Pep — ask me anything about geography.",
    5: "Greetings. I'm Pep. What would you like to explore?"
  };
  return greetings[PEP_STAGE] || greetings[1];
}

// ── TOGGLE ─────────────────────────────────────────────────
function togglePep() {
  pepOpen = !pepOpen;
  const panel = document.getElementById('pepPanel');
  if (pepOpen) {
    panel.classList.add('open');
    loadMsgs();
    if (!PEP_LOCKED) {
      document.getElementById('pepIn').focus();
    }
  } else {
    panel.classList.remove('open');
  }
}

// ── ADD MESSAGE ────────────────────────────────────────────
function addMsg(role, text) {
  const msgs = document.getElementById('pepMsgs');
  const div  = document.createElement('div');
  div.className = 'pep-msg ' + (role === 'pep' ? 'pep-p' : 'pep-u');
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  saveMsgs();
}

// ── SEND ───────────────────────────────────────────────────
function sendPep() {
  if (PEP_LOCKED) return;
  const input = document.getElementById('pepIn');
  const msg   = input.value.trim();
  if (!msg) return;

  addMsg('user', msg);
  input.value = '';

  // Typing indicator
  const msgs = document.getElementById('pepMsgs');
  const typing = document.createElement('div');
  typing.className = 'pep-msg pep-p pep-typing';
  typing.textContent = '...';
  typing.id = 'pepTyping';
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;

  fetch('/pep', {
    method:  'POST',
    headers: {'Content-Type': 'application/json'},
    body:    JSON.stringify({message: msg})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('pepTyping')?.remove();
    addMsg('pep', data.reply);
  })
  .catch(() => {
    document.getElementById('pepTyping')?.remove();
    addMsg('pep', 'Sorry, something went wrong.');
  });
}

// ── IN-GAME POP-UP MESSAGE ─────────────────────────────────
function showPepPopup(message) {
  const bubble = document.getElementById('pepBubble');
  // Create popup above bubble
  const popup = document.createElement('div');
  popup.className = 'pep-popup';
  popup.textContent = message;
  document.getElementById('pepWidget').appendChild(popup);

  // Auto-remove after 4 seconds
  setTimeout(() => popup.remove(), 4000);
}