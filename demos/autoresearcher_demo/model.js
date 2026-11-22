export const stages = ['仿真', '训练', '评测'];
export const durations = [5500, 6500, 4500];
const fixtureResults = [
  '完成调度受限、链路恶化和混合退化三组预设演示工况。',
  '已生成演示模型版本及对应的训练日志。',
  '独立工况演示集 · 基线 16/24 · 候选 20/24 · 门槛 19/24',
];

export const initialEntries = [
  {
    id: 'KB-001', version: 1, confirmed: true, tag: '性能诊断',
    title: '吞吐下降时区分调度受限与链路质量恶化',
    scope: '同一制式、带宽和负载可比的下行场景。先核对统计窗口、业务量和终端组合。',
    method: '吞吐下降且调度资源接近饱和时，先核对活跃用户数和可用资源。SINR 下降并伴随 BLER 上升时，结合 MCS 与重传检查链路质量。两类证据同时出现时，保留混合退化判断。',
    acceptance: '在独立的 24 个演示工况中至少判断正确 19 个。混合退化案例须给出两类证据，证据不足时允许请求补充仿真。',
    source: '',
  },
  {
    id: 'KB-002', version: 1, confirmed: false, tag: '时延分析',
    title: '高负载下的时延异常定位',
    scope: '负载逐步上升、数据包大小分布稳定的演示场景。',
    method: '对齐队列长度、调度等待与端到端时延的采样窗口，检查峰值先后顺序。',
    acceptance: '在典型案例中识别排队增长，并对缺失时间戳的案例请求补充数据。',
    source: '',
  },
  {
    id: 'KB-003', version: 1, confirmed: false, tag: '仿真验证',
    title: '仿真与外场结果偏差排查',
    scope: '指标定义、流量和采样窗口可对齐的单小区场景。',
    method: '先比对输入条件和指标口径，再逐项核对信道和负载假设。',
    acceptance: '定位故意注入的口径差异，并记录未能解释的剩余偏差。',
    source: '',
  },
];

export function taskStatus(task, now = Date.now()) {
  if (task.stoppedAt) return '已停止';
  return now >= task.endsAt ? '已完成' : '运行中';
}

export function completedTask(tasks, entry, kind, now = Date.now()) {
  return tasks.find(task => task.entryId === entry.id && task.version === entry.version &&
    task.kind === kind && taskStatus(task, now) === '已完成');
}

export function submitTask(tasks, entry, kind, now = Date.now()) {
  const index = stages.indexOf(kind);
  if (index < 0 || !entry.confirmed) throw new Error('请先确认经验条目。');
  const previous = index > 0 ? completedTask(tasks, entry, stages[index - 1], now) : null;
  if (index > 0 && !previous) {
    throw new Error('请先完成同版本的上一阶段任务。');
  }
  if (tasks.some(task => task.entryId === entry.id && task.version === entry.version &&
    task.kind === kind && taskStatus(task, now) === '运行中')) {
    throw new Error('同版本的任务正在运行。');
  }
  return {
    id: 'DEMO-' + crypto.randomUUID().slice(0, 8).toUpperCase(),
    entryId: entry.id, version: entry.version, title: entry.title, kind,
    startedAt: now, endsAt: now + durations[index], previousId: previous?.id,
  };
}

export function advanceRuns(tasks, entries, now = Date.now()) {
  let updated = tasks;
  for (const task of tasks) {
    const nextKind = stages[stages.indexOf(task.kind) + 1];
    if (!task.auto || !nextKind || taskStatus(task, now) !== '已完成') continue;
    if (updated.some(item => item.entryId === task.entryId && item.version === task.version && item.kind === nextKind)) continue;
    const entry = entries.find(item => item.id === task.entryId && item.version === task.version);
    if (!entry?.confirmed) continue;
    updated = [...updated, { ...submitTask(updated, entry, nextKind, now), auto: true }];
  }
  return updated;
}

export function taskLog(task) {
  const state = taskStatus(task);
  const fixture = task.entryId === 'KB-001' && task.version === 1;
  return [
    'mode=demo', 'job=' + task.id, 'wiki=' + task.entryId + '@v' + task.version,
    'stage=' + task.kind, 'started=' + new Date(task.startedAt).toISOString(),
    'previous_job=' + (task.previousId || ''),
    'status=' + state,
    state === '已完成' ? (fixture ? fixtureResults[stages.indexOf(task.kind)] : '模拟任务完成。') : '',
  ].join('\n');
}
