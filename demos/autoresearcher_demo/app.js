import { initialEntries, stages, taskStatus, completedTask, submitTask, advanceRuns, taskLog } from './model.js';

const storageKey = 'autoresearcher-demo-v1';
const main = document.querySelector('#main');
const editor = document.querySelector('#editor');
const form = document.querySelector('#entry-form');
const labels = { wiki: '部门经验库', jobs: '实验任务', eval: '模型评测' };
const fields = { title: '标题', tag: '分类', scope: '适用条件', method: '判断依据', acceptance: '验收标准' };
const blankState = () => ({ entries: structuredClone(initialEntries), tasks: [] });

let state;
try {
  state = JSON.parse(localStorage.getItem(storageKey)) || blankState();
} catch {
  state = blankState();
}
let activeId = state.entries[0].id;
let editingId = null;
let query = '';
let filter = '全部';
let toastTimer;
let taskSnapshot = '';

const html = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));
const currentPage = () => Object.hasOwn(labels, location.hash.slice(1)) ? location.hash.slice(1) : 'wiki';
const currentEntry = () => state.entries.find(entry => entry.id === activeId);
const stamp = time => new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
}).format(time);

function notify(message) {
  const toast = document.querySelector('#toast');
  toast.hidden = false;
  toast.textContent = message;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 3300);
}

function save(nextState) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(nextState));
  } catch {
    notify('本地存储不可用，本次变更仅在当前页面保留。');
    state = nextState;
    return false;
  }
  state = nextState;
  return true;
}

function badge(value) {
  const tone = { 已确认: 'green', 已完成: 'green', 运行中: 'blue', 已停止: 'amber', 草稿: 'amber' }[value] || '';
  return '<span class="badge ' + tone + '">' + html(value) + '</span>';
}

function pageHeading(title, subtitle, action = '') {
  return '<div class="page-heading"><div><h1>' + title + '</h1><p>' + subtitle + '</p></div>' + action + '</div>';
}

function wikiList() {
  const matching = state.entries.filter(entry => [entry.title, entry.tag, entry.id]
    .some(value => value.toLowerCase().includes(query.trim().toLowerCase())));
  return matching.map(entry => `
    <button class="entry-row ${entry.id === activeId ? 'selected' : ''}" data-action="select" data-id="${entry.id}" aria-pressed="${entry.id === activeId}">
      <span class="entry-meta"><span>${entry.id} · v${entry.version}</span>${badge(entry.confirmed ? '已确认' : '草稿')}</span>
      <strong>${html(entry.title)}</strong><small>${html(entry.tag)}</small>
    </button>`).join('') || '<p class="empty compact">没有匹配的经验条目。</p>';
}

function workflow(entry) {
  return '<div class="workflow" aria-label="当前条目流程">' +
    ['经验条目', '仿真验证', '模型训练', '回归评测']
      .map((label, index) => {
        const done = index === 0 ? entry.confirmed : completedTask(state.tasks, entry, stages[index - 1]);
        return `<div class="step ${done ? 'done' : ''}"><span>${done ? '✓' : index + 1}</span><strong>${label}</strong></div>`;
      }).join('') + '</div>';
}

function nextAction(entry, secondary = false) {
  if (!entry.confirmed) return '<button class="primary" data-action="confirm">确认演示经验</button>';
  const running = state.tasks.find(task => task.entryId === entry.id && task.version === entry.version &&
    taskStatus(task) === '运行中');
  if (running) return '<a class="button primary" href="#jobs">查看运行任务</a>';
  const next = stages.find(kind => !completedTask(state.tasks, entry, kind));
  if (!next) return '<a class="button primary" href="#eval">查看回归结果</a>';
  return `<button class="${secondary ? '' : 'primary'}" data-action="submit" data-kind="${next}">提交${next === '评测' ? '回归评测' : next}</button>`;
}

function wikiPage() {
  const entry = currentEntry();
  const evidence = state.tasks.filter(task => task.entryId === entry.id && task.version === entry.version);
  const revisions = (state.revisions || []).filter(item => item.id === entry.id).reverse();
  const canAuto = entry.confirmed && !evidence.length;
  return pageHeading('部门经验库', '将部门 Wiki 经验转成可验证的模型能力。', '<button class="primary" data-action="new">＋ 新建经验</button>') +
    workflow(entry) + `
    <div class="wiki-grid">
      <section class="panel library" aria-label="经验条目">
        <div class="library-head"><h2>经验条目</h2><span>${state.entries.length} 条</span></div>
        <div class="search-wrap"><span aria-hidden="true">⌕</span><input id="search" type="search" aria-label="搜索经验" placeholder="搜索标题、分类或编号" value="${html(query)}"></div>
        <div id="entry-list">${wikiList()}</div>
      </section>
      <article class="panel article">
        <div class="article-head">
          <div class="record"><span>${entry.id} · v${entry.version}</span>${badge(entry.confirmed ? '已确认' : '草稿')}</div>
          <h2>${html(entry.title)}</h2><span class="tag">${html(entry.tag)}</span>
        </div>
        <div class="article-body">
          ${['scope', 'method', 'acceptance'].map(field => `<section><h3>${fields[field]}</h3><p>${html(entry[field])}</p></section>`).join('')}
          <section><h3>来源与证据</h3>
            <p>${entry.source ? '<a target="_blank" rel="noopener noreferrer" href="' + html(entry.source) + '">打开 Wiki 来源 ↗</a>' : '本地演示条目'}</p>
            ${evidence.length ? '<div class="evidence">' + evidence.map(task =>
              `<a href="#jobs" data-action="show-tasks">${task.kind} · ${task.id} · ${taskStatus(task)}</a>`).join('') + '</div>' : ''}
          </section>
          ${revisions.length ? `<section><h3>历史版本</h3>${revisions.map(item =>
            `<details><summary>v${item.version} · ${html(item.title)}</summary>${['scope', 'method', 'acceptance'].map(field =>
              `<p><strong>${fields[field]}　</strong>${html(item[field])}</p>`).join('')}</details>`).join('')}</section>` : ''}
        </div>
        <footer class="article-actions">
          ${canAuto ? '<button class="primary" data-action="submit" data-kind="仿真" data-auto="true">运行完整流程</button>' : ''}
          ${nextAction(entry, canAuto)}
          <button data-action="edit">编辑经验</button>
        </footer>
      </article>
    </div>`;
}

function jobPage() {
  const jobs = state.tasks.slice().reverse().filter(task => filter === '全部' || taskStatus(task) === filter);
  return pageHeading('实验任务', '查看仿真、训练和评测状态与日志。', '<a class="button" href="#wiki">返回经验库</a>') + `
    <section class="panel tasks">
      <div class="table-head"><h2>任务记录</h2><label>状态 <select id="task-filter">
        ${['全部', '运行中', '已完成', '已停止'].map(value => `<option ${filter === value ? 'selected' : ''}>${value}</option>`).join('')}
      </select></label></div>
      ${jobs.length ? `<div class="table-scroll"><table><thead><tr><th>任务</th><th>经验版本</th><th>提交时间</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>${jobs.map(task => `<tr><td><strong>${task.kind}</strong><small>${task.id}</small></td>
      <td>${task.entryId} · v${task.version}<small>${html(task.title)}</small></td>
      <td>${stamp(task.startedAt)}</td><td>${badge(taskStatus(task))}</td>
      <td><div class="row-actions"><button data-action="log" data-id="${task.id}">下载日志</button>
      ${taskStatus(task) === '运行中' ? `<button data-action="stop" data-id="${task.id}">停止</button>` : ''}</div></td></tr>`).join('')}</tbody></table></div>` :
      '<div class="empty">当前没有符合条件的任务。<br><a href="#wiki">从经验条目提交仿真</a></div>'}
    </section>`;
}

function evalPage() {
  const jobs = state.tasks.filter(task => task.kind === '评测' && taskStatus(task) === '已完成').reverse();
  return pageHeading('模型评测', '查看留出工况的基线与候选模型对照。', '<a class="button" href="#wiki">返回经验库</a>') +
    (jobs.length ? jobs.map(task => {
      const fixture = task.entryId === 'KB-001' && task.version === 1;
      return `<section class="panel evaluation"><div class="record"><span>${task.entryId} · v${task.version} · ${task.id}</span>${badge(fixture ? '达到演示门槛' : '已完成')}</div>
        <h2>${html(task.title)}</h2>
        ${fixture ? `<p>预设结果 · 留出集 24 个演示工况 · 验收门槛 19/24</p>
          <div class="metrics"><div><span>基线模型</span><strong>16 / 24</strong></div><div><span>候选模型</span><strong>20 / 24</strong></div><div><span>正确案例增量</span><strong>+4</strong></div></div>`
          : '<p>该版本已走完模拟流程，暂无预设评测分数。</p>'}
        <button data-action="log" data-id="${task.id}">下载评测日志</button></section>`;
    }).join('') : '<section class="panel empty">完成一次回归评测后，结果会显示在这里。<br><a href="#wiki">查看经验条目</a></section>');
}

function render() {
  const page = currentPage();
  document.querySelector('#breadcrumb').textContent = labels[page];
  document.querySelectorAll('[data-nav]').forEach(link => {
    if (link.dataset.nav === page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  main.innerHTML = { wiki: wikiPage, jobs: jobPage, eval: evalPage }[page]();
  taskSnapshot = state.tasks.map(task => taskStatus(task)).join(',');
}

function openEditor(entry) {
  editingId = entry?.id || null;
  form.reset();
  document.querySelector('#form-title').textContent = entry ? '编辑经验 · 新版本' : '新建经验';
  document.querySelector('#form-error').textContent = '';
  [...Object.keys(fields), 'source'].forEach(field => { form.elements[field].value = entry?.[field] || ''; });
  editor.showModal();
}

function download(task) {
  const url = URL.createObjectURL(new Blob([taskLog(task)], { type: 'text/plain;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = task.id + '.log';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

main.addEventListener('click', event => {
  const control = event.target.closest('[data-action]');
  if (!control) return;
  const { action, id, kind } = control.dataset;
  const entry = currentEntry();
  const task = state.tasks.find(item => item.id === id);
  switch (action) {
    case 'select': activeId = id; render(); break;
    case 'new': openEditor(); break;
    case 'edit': openEditor(entry); break;
    case 'confirm':
      if (save({ ...state, entries: state.entries.map(item => item.id === entry.id ? { ...item, confirmed: true } : item) })) notify('经验已确认，可以提交仿真。');
      render();
      break;
    case 'submit':
      try {
        const job = { ...submitTask(state.tasks, entry, kind), auto: control.dataset.auto === 'true' };
        if (save({ ...state, tasks: [...state.tasks, job] })) notify('已提交演示' + kind + '任务。');
        filter = '全部';
        location.hash = 'jobs';
      } catch (error) { notify(error.message); }
      break;
    case 'show-tasks': filter = '全部'; break;
    case 'log': if (task) download(task); break;
    case 'stop':
      if (task && taskStatus(task) === '运行中') {
        const tasks = state.tasks.map(item => item.id === id ? { ...item, stoppedAt: Date.now() } : item);
        if (save({ ...state, tasks })) notify('演示任务已停止。');
        render();
      }
      break;
  }
});

main.addEventListener('input', event => {
  if (event.target.id !== 'search') return;
  query = event.target.value;
  document.querySelector('#entry-list').innerHTML = wikiList();
});

main.addEventListener('change', event => {
  if (event.target.id !== 'task-filter') return;
  filter = event.target.value;
  render();
  document.querySelector('#task-filter').focus();
});

form.addEventListener('submit', event => {
  event.preventDefault();
  const values = Object.fromEntries(Array.from(new FormData(form), ([key, value]) => [key, value.trim()]));
  const error = document.querySelector('#form-error');
  const missing = Object.keys(fields).find(key => !values[key]);
  if (missing) {
    error.textContent = '请填写' + fields[missing] + '。';
    form.elements[missing].focus();
    return;
  }
  if (values.source && !/^https?:\/\//i.test(values.source)) {
    error.textContent = 'Wiki 来源链接须以 http:// 或 https:// 开头。';
    form.elements.source.focus();
    return;
  }
  const existing = state.entries.find(entry => entry.id === editingId);
  const id = existing?.id || 'KB-' + String(state.entries.length + 1).padStart(3, '0');
  const entry = { ...values, id, version: (existing?.version || 0) + 1, confirmed: false };
  const entries = existing ? state.entries.map(item => item.id === id ? entry : item) : [entry, ...state.entries];
  const revisions = [...(state.revisions || []), ...(existing ? [existing] : [])];
  if (save({ ...state, entries, revisions })) notify('经验草稿已保存。');
  activeId = id;
  query = '';
  editor.close();
  render();
});

['close', 'cancel'].forEach(id => document.getElementById(id).addEventListener('click', () => editor.close()));
window.addEventListener('hashchange', () => { render(); main.focus({ preventScroll: true }); });
setInterval(() => {
  const tasks = advanceRuns(state.tasks, state.entries);
  if (tasks !== state.tasks) save({ ...state, tasks });
  const snapshot = state.tasks.map(task => taskStatus(task)).join(',');
  if (snapshot !== taskSnapshot && !editor.open && document.activeElement?.id !== 'search') render();
}, 400);
render();
