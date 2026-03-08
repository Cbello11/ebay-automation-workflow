const fileInput = document.getElementById('fileInput');
const addFileBtn = document.getElementById('addFileBtn');
const dropZone = document.getElementById('dropZone');
const recentList = document.getElementById('recentList');
const viewerPane = document.getElementById('viewerPane');
const viewerTitle = document.getElementById('viewerTitle');
const viewer = document.getElementById('viewer');
const searchInput = document.getElementById('searchInput');
let currentFile = null;

const cacheKey = 'universal_reader_cache';
const aiCacheKey = 'universal_reader_ai_cache';

const haptic = () => navigator.vibrate && navigator.vibrate(10);

document.getElementById('themeToggle').onclick = () => {
  document.body.classList.toggle('dark');
  haptic();
};

addFileBtn.onclick = () => { fileInput.click(); haptic(); };
fileInput.onchange = () => uploadFile(fileInput.files[0]);

['dragenter','dragover'].forEach(ev => dropZone.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.add('drag'); }));
['dragleave','drop'].forEach(ev => dropZone.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.remove('drag'); }));
dropZone.addEventListener('drop', e => { if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]); });

async function uploadFile(file){
  const fd = new FormData();
  fd.append('file', file);
  fd.append('user_id', 'private_local_user');
  await fetch('/api/upload', { method:'POST', body:fd });
  await loadFiles();
}

document.getElementById('pasteBtn').onclick = async () => {
  const text = document.getElementById('pasteInput').value;
  await fetch('/api/paste', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text})});
  document.getElementById('pasteInput').value = '';
  await loadFiles();
};

searchInput.oninput = async () => {
  const q = searchInput.value.trim();
  if (!q) return loadFiles();
  const res = await fetch('/api/search?q=' + encodeURIComponent(q));
  renderList(await res.json());
};

function iconFor(type){ return ({image:'🖼️', audio:'🎧', document:'📄', text:'📝', raw:'📦'})[type] || '📁'; }

function cacheRecent(files){
  const compact = files.slice(0,10);
  localStorage.setItem(cacheKey, JSON.stringify(compact));
}

function renderList(files){
  recentList.innerHTML = '';
  cacheRecent(files);
  files.forEach(f => {
    const el = document.createElement('button');
    el.className = 'file-item';
    el.innerHTML = `<div class="thumb">${iconFor(f.type_group)}</div><div><strong>${f.name}</strong><div>${f.mime}</div></div><small>${new Date(f.last_opened_at || f.created_at).toLocaleString()}</small>`;
    el.onclick = () => openFile(f.id);
    recentList.appendChild(el);
  });
}

async function loadFiles(){
  try {
    const res = await fetch('/api/files');
    renderList(await res.json());
  } catch {
    const cached = JSON.parse(localStorage.getItem(cacheKey) || '[]');
    renderList(cached);
  }
}

function saveAiCache(fileId, payload){
  const cache = JSON.parse(localStorage.getItem(aiCacheKey) || '{}');
  cache[fileId] = payload;
  const keys = Object.keys(cache);
  if (keys.length > 10) delete cache[keys[0]];
  localStorage.setItem(aiCacheKey, JSON.stringify(cache));
}

async function openFile(id){
  const res = await fetch('/api/files/' + id);
  const f = await res.json();
  currentFile = f;
  viewerPane.classList.remove('hidden');
  viewerTitle.textContent = f.name;
  const content = f.content || '';
  document.getElementById('editContent').value = content;

  if (f.type_group === 'text') {
    const wc = content.trim() ? content.trim().split(/\s+/).length : 0;
    viewer.innerHTML = `<textarea id="editor" rows="15">${content.replaceAll('<','&lt;')}</textarea><div>Word count: ${wc}</div>`;
  } else if (f.type_group === 'document') {
    const ext = f.name.split('.').pop().toLowerCase();
    if (ext === 'pdf') viewer.innerHTML = `<iframe src="/api/files/${f.id}/download" width="100%" height="420"></iframe>`;
    else viewer.innerHTML = `<div>Document page viewer</div><pre>${content || 'Preview unavailable.'}</pre>`;
  } else if (f.type_group === 'image') {
    viewer.innerHTML = `<img src="/api/files/${f.id}/download" alt="${f.name}"/><div><button id="describeImg">Describe</button> <button id="translateImg">Translate text in image</button></div><pre id="imgAction"></pre>`;
    document.getElementById('describeImg').onclick = ()=> document.getElementById('imgAction').textContent = 'Image description: visual details ready for quick scan.';
    document.getElementById('translateImg').onclick = ()=> document.getElementById('imgAction').textContent = 'OCR translation result appears here.';
  } else if (f.type_group === 'audio') {
    viewer.innerHTML = `<audio controls src="/api/files/${f.id}/download"></audio><pre id="transcriptBox">Streaming transcription: (demo) Listening...</pre>`;
  } else {
    viewer.innerHTML = `<pre>Raw view not supported for this type.</pre><a href="/api/files/${f.id}/download"><button>Download</button></a>`;
  }
}

document.getElementById('translateBtn').onclick = async () => {
  if (!currentFile) return;
  const target = document.getElementById('targetLang').value;
  const res = await fetch('/api/ai/translate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text: currentFile.content || currentFile.summary || currentFile.name, target})});
  const data = await res.json();
  document.getElementById('translateResult').textContent = data.translated;
  saveAiCache(currentFile.id, { translate: data.translated });
};

document.getElementById('summarizeBtn').onclick = async () => {
  if (!currentFile) return;
  const res = await fetch('/api/ai/summarize', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text: currentFile.content || currentFile.summary || ''})});
  const data = await res.json();
  const output = `${data.paragraph}\n${data.bullets.join('\n')}`;
  document.getElementById('summaryResult').textContent = output;
  saveAiCache(currentFile.id, { summarize: output });
};

document.getElementById('copySummaryBtn').onclick = async () => {
  await navigator.clipboard.writeText(document.getElementById('summaryResult').textContent);
  haptic();
};

document.getElementById('saveVersionBtn').onclick = async () => {
  if (!currentFile) return;
  const content = document.getElementById('editContent').value;
  const res = await fetch('/api/ai/edit', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({file_id: currentFile.id, content})});
  const data = await res.json();
  document.getElementById('saveVersionMsg').textContent = `Saved version ${data.version_id?.slice(0,8) || ''}`;
  haptic();
};

document.getElementById('askBtn').onclick = async () => {
  if (!currentFile) return;
  const question = document.getElementById('askInput').value;
  const res = await fetch('/api/ai/ask', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question, text: currentFile.content || currentFile.summary || ''})});
  const data = await res.json();
  document.getElementById('askResult').textContent = data.answer;
  saveAiCache(currentFile.id, { ask: data.answer });
};

loadFiles();
