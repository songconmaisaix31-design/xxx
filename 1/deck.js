/* 真实标签 TagPulse · 演示驱动
 * 依赖：无。原生 DOM，渐进增强。
 * 无 JS 时 CSS 只显示首页 —— 所以这里第一件事是把 is-on 交给 JS 管。
 */
(() => {
  'use strict';

  const slides = [...document.querySelectorAll('.slide')];
  const stage = document.getElementById('deck');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');

  const el = {
    fill: document.getElementById('hudFill'),
    now: document.getElementById('hudNow'),
    all: document.getElementById('hudAll'),
    prev: document.getElementById('btnPrev'),
    next: document.getElementById('btnNext'),
    grid: document.getElementById('btnGrid'),
    full: document.getElementById('btnFull'),
    live: document.getElementById('liveNow'),
    ctrl: document.querySelector('.hud-ctrl'),
    bar: document.querySelector('.hud-bar'),
  };

  let at = 0;
  let gridOn = false;

  /* ---------- 初始化：页码、导航标签、错峰序号 ---------- */

  slides.forEach((s, i) => {
    s.dataset.page = `${String(i + 1).padStart(2, '0')} · ${s.dataset.nav || ''}`;
    s.setAttribute('aria-roledescription', 'slide');
    s.setAttribute('aria-label', `第 ${i + 1} 页，共 ${slides.length} 页：${s.dataset.nav || ''}`);
    // 错峰：给每个 reveal 容器的直接子元素编号，CSS 用 --i 算 delay
    s.querySelectorAll('.reveal, .sh, .cover-left').forEach((box) => {
      [...box.children].forEach((c, j) => c.style.setProperty('--i', j));
    });
  });
  el.all.textContent = slides.length;

  /* ---------- 舞台缩放：1280×720 等比适配任意窗口 ---------- */

  function fit() {
    if (gridOn) return;
    const pad = 34;
    // HUD 固定在底部，展开后会压住幻灯片下沿（宽而矮的屏幕最明显）。
    // 高度实测而非写死：字号变了、按钮换行了，这里自动跟着变。
    // 交给 CSS 的 padding-bottom 去留位，居中就只发生在剩下的空间里，
    // 因此只需扣 1 倍高度（扣 2 倍会让 1366×768 白掉 14%）。
    const hudH = (el.ctrl?.offsetHeight || 56) + (el.bar?.offsetHeight || 6);
    const reserve = hudH + 8; // +8 呼吸位，别让内容贴着 HUD
    document.documentElement.style.setProperty('--hud-reserve', `${reserve}px`);
    // 必须有下限：窗口比 pad 还小时（隐藏的 iframe、折叠面板、极小窗口）
    // innerWidth-pad 会变负数，scale 取负会把整个舞台翻转并缩成一个点。
    const s = Math.max(0.08, Math.min(
      (innerWidth - pad) / 1280,
      (innerHeight - pad - reserve) / 720
    ));
    document.documentElement.style.setProperty('--s', s.toFixed(4));
  }

  /* ---------- 翻页 ---------- */

  function show(i, opts = {}) {
    at = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((s, j) => {
      const on = j === at;
      s.classList.toggle('is-on', on);
      s.setAttribute('aria-hidden', on ? 'false' : 'true');
      // 隐藏页不参与 Tab 顺序
      s.querySelectorAll('button, a[href]').forEach((n) => {
        if (on) n.removeAttribute('tabindex');
        else n.setAttribute('tabindex', '-1');
      });
    });

    el.now.textContent = at + 1;
    el.fill.style.width = `${((at + 1) / slides.length) * 100}%`;
    // 读屏播报：只播「第几页 / 共几页 · 标题」，不重复整页内容
    el.live.textContent = `第 ${at + 1} 页，共 ${slides.length} 页：${slides[at].dataset.nav || ''}`;
    el.prev.disabled = at === 0;
    el.next.disabled = at === slides.length - 1;
    if (!opts.silent) location.hash = `p${at + 1}`;

    if (gridOn) slides[at].scrollIntoView({ block: 'center', behavior: 'smooth' });
    else enter(slides[at]);
  }

  /* ---------- 进入某页时触发该页的一次性动效 ---------- */

  function enter(slide) {
    // 匹配度环：conic 角度 + 数字计数。
    // CSS 里 --pa 已经等于 --p，静态状态本身就是对的；这里只负责
    // 「先压到 0 再放回去」的扫弧动画。document.hidden 时 rAF 不跑，
    // 所以必须先确认能拿到帧，否则宁可不动 —— 不能把环留在 0%。
    slide.querySelectorAll('.ring').forEach((ring) => {
      const p = Number(ring.style.getPropertyValue('--p')) || 0;
      const num = ring.querySelector('[data-count]');
      if (reduce.matches || document.hidden) {
        ring.style.removeProperty('--pa');   // 交回 CSS 的 --pa:var(--p)
        if (num) num.textContent = p;
        return;
      }
      ring.style.setProperty('--pa', 0);
      if (num) num.textContent = '0';
      // 下一帧起跑，保证 transition 生效
      requestAnimationFrame(() => {
        ring.style.setProperty('--pa', p);
        if (num) countTo(num, p, 900);
      });
    });

    // 权重条 500ms 增长（PRD 5.7）。
    // CSS 默认满格，所以这里必须先 arm（压到 0）再 run（放回去）。
    // rAF 不跑时（document.hidden / 打印）直接不 arm，条子保持满格。
    slide.querySelectorAll('[data-weights]').forEach((w) => {
      w.classList.remove('is-run', 'is-armed');
      if (reduce.matches || document.hidden) return;
      w.classList.add('is-armed');
      requestAnimationFrame(() => {
        w.classList.remove('is-armed');
        w.classList.add('is-run');
      });
    });

    // 「？」卡回到未翻开
    slide.querySelectorAll('[data-qcards] button').forEach((b) => {
      b.classList.remove('is-open');
      b.textContent = '?';
      b.setAttribute('aria-pressed', 'false');
    });

    // 三阶段动画复位
    slide.querySelectorAll('#phases li').forEach((p) => p.classList.remove('is-run', 'is-done'));
  }

  function countTo(node, to, ms) {
    const t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / ms);
      // easeOutCubic，落点稳
      node.textContent = Math.round(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  /* ---------- 总览网格 ---------- */

  function toggleGrid(on) {
    gridOn = on ?? !gridOn;
    document.body.classList.toggle('is-grid', gridOn);
    el.grid.setAttribute('aria-pressed', String(gridOn));
    if (gridOn) {
      document.documentElement.style.setProperty('--s', 1);
      slides[at].scrollIntoView({ block: 'center' });
    } else {
      fit();
      enter(slides[at]);
    }
  }

  /* ---------- 事件 ---------- */

  el.prev.addEventListener('click', () => show(at - 1));
  el.next.addEventListener('click', () => show(at + 1));
  el.grid.addEventListener('click', () => toggleGrid());
  el.full.addEventListener('click', () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen?.();
  });

  slides.forEach((s, i) => {
    s.addEventListener('click', () => {
      if (gridOn) { toggleGrid(false); show(i); }
    });
  });

  addEventListener('keydown', (e) => {
    // target 不一定是元素（window / document 也会收到 keydown），先确认再 matches
    if (e.target?.matches?.('input, textarea')) return;
    const k = e.key;
    if (k === 'ArrowRight' || k === 'PageDown' || k === ' ') { e.preventDefault(); show(at + 1); }
    else if (k === 'ArrowLeft' || k === 'PageUp') { e.preventDefault(); show(at - 1); }
    else if (k === 'Home') { e.preventDefault(); show(0); }
    else if (k === 'End') { e.preventDefault(); show(slides.length - 1); }
    else if (k === 'o' || k === 'O') { e.preventDefault(); toggleGrid(); }
    else if (k === 'f' || k === 'F') { e.preventDefault(); el.full.click(); }
    else if (k === 'Escape' && gridOn) { e.preventDefault(); toggleGrid(false); }
  });

  addEventListener('resize', fit);
  addEventListener('hashchange', () => {
    const n = Number(location.hash.replace('#p', ''));
    if (n && n - 1 !== at) show(n - 1, { silent: true });
  });

  // 触屏左右滑
  let tx = 0, ty = 0;
  stage.addEventListener('touchstart', (e) => {
    tx = e.changedTouches[0].clientX; ty = e.changedTouches[0].clientY;
  }, { passive: true });
  stage.addEventListener('touchend', (e) => {
    if (gridOn) return;
    const dx = e.changedTouches[0].clientX - tx;
    const dy = e.changedTouches[0].clientY - ty;
    if (Math.abs(dx) > 52 && Math.abs(dx) > Math.abs(dy)) show(at + (dx < 0 ? 1 : -1));
  }, { passive: true });

  /* ---------- 「？」卡翻开 · PRD 5.6 隐私边界，不是加载占位符 ---------- */

  document.addEventListener('click', (e) => {
    const q = e.target.closest('[data-qcards] button');
    if (!q || gridOn) return;
    const open = q.classList.toggle('is-open');
    q.textContent = open ? q.dataset.reveal : '?';
    q.setAttribute('aria-pressed', String(open));
  });

  /* ---------- 破冰工具箱：摇骰子 / 抽任务卡 ---------- */

  // 1–6 点对应固定话题（PRD 4.3.2：每个点数对应一个聊天话题）
  const DICE = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];
  const TOPICS = [
    '最近最想学但一直没开始的东西是什么',
    '你一天里状态最好的是哪两个小时',
    '上一次坚持超过 100 天的事情是什么',
    '如果只能留一个 App 在手机里，留哪个',
    '你运动是为了身体还是为了脑子',
    '最近一次熬夜是因为什么',
  ];
  // 任务卡内容库按「学习 / 运动 / 生活 / 脑洞 / 价值观」分类（PRD 4.3.3 要求 30 条以上，这里取样）
  const CARDS = [
    ['学习', '说出你最近最想学的东西'],
    ['学习', '用一句话教对方一个你刚学会的知识'],
    ['运动', '描述你运动时脑子里在想什么'],
    ['运动', '说一个你放弃过又捡回来的运动'],
    ['生活', '说出你冰箱里现在有什么'],
    ['脑洞', '如果时间能存起来，你会存多少小时'],
    ['价值观', '你觉得坚持一件事最难的是哪一天'],
  ];

  const dice = document.getElementById('dice');
  const topic = document.getElementById('diceTopic');
  const card = document.getElementById('diceCard');

  document.getElementById('rollDice')?.addEventListener('click', () => {
    const n = Math.floor(Math.random() * 6);
    if (!reduce.matches) {
      dice.classList.remove('is-roll');
      void dice.offsetWidth; // 强制重排，让同一动画能重放
      dice.classList.add('is-roll');
    }
    dice.textContent = DICE[n];
    topic.textContent = `${n + 1} 点 · ${TOPICS[n]}`;
    card.querySelector('small').textContent = '系统卡片消息 · 双方都能看到';
  });

  document.getElementById('drawCard')?.addEventListener('click', () => {
    const [cat, text] = CARDS[Math.floor(Math.random() * CARDS.length)];
    dice.textContent = '▤';
    topic.textContent = text;
    card.querySelector('small').textContent = `任务卡 · ${cat}类 · 计入互动热度值`;
  });

  /* ---------- 匹配过程三阶段 · 260/1000/1740/2500ms（brand-spec §14）---------- */

  const phases = document.getElementById('phases');
  let timers = [];
  document.getElementById('runSearch')?.addEventListener('click', () => {
    timers.forEach(clearTimeout);
    timers = [];
    const items = [...phases.children];
    items.forEach((p) => p.classList.remove('is-run', 'is-done'));

    if (reduce.matches) {
      // 减弱动画：立即完成所有步骤，直接给服务端结果（brand-spec §14）
      items.forEach((p) => p.classList.add('is-done'));
      return;
    }
    items.forEach((p, i) => {
      const at = Number(p.dataset.at);
      timers.push(setTimeout(() => {
        p.classList.add('is-run');
        items.slice(0, i).forEach((q) => { q.classList.remove('is-run'); q.classList.add('is-done'); });
      }, at));
    });
    timers.push(setTimeout(() => {
      items.forEach((p) => { p.classList.remove('is-run'); p.classList.add('is-done'); });
    }, 2500 + 420));
  });

  /* ---------- 启动 ---------- */

  fit();
  const start = Number(location.hash.replace('#p', ''));
  const startAt = start ? start - 1 : 0;
  show(startAt, { silent: true });
  stage.focus({ preventScroll: true });

  /* ---------- 自检：断言页面结构与状态机不变量 ---------- */
  /* 打开 ?selftest 时跑；只做最小检查，坏了立刻在控制台喊 */
  if (location.search.includes('selftest')) {
    const fails = [];
    const ok = (cond, msg) => { if (!cond) fails.push(msg); };

    ok(slides.length >= 10, `幻灯片数量异常：${slides.length}`);
    ok(slides.filter((s) => s.classList.contains('is-on')).length === 1, '同时有多页或没有页处于 is-on');
    // 权重表必须合计 100%（PRD 4.2.1 研发要求：启动断言）
    const sum = [...document.querySelectorAll('[data-weights] li')]
      .reduce((a, li) => a + Number(li.style.getPropertyValue('--w')), 0);
    ok(sum === 100, `权重合计不等于 100：${sum}`);
    // 三阶段时序必须严格递增（brand-spec §14）
    const ats = [...document.querySelectorAll('#phases li')].map((p) => Number(p.dataset.at));
    ok(ats.every((v, i) => i === 0 || v > ats[i - 1]), `三阶段时序非递增：${ats}`);
    // 翻页边界。自检会来回翻页，跑完必须回到 URL 指定的那一页，
    // 否则带 ?selftest 打开 #p8 会被自检踢回第 1 页。
    show(0, { silent: true }); ok(at === 0 && el.prev.disabled, '首页边界失效');
    show(999, { silent: true }); ok(at === slides.length - 1 && el.next.disabled, '末页边界失效');
    show(startAt, { silent: true });
    // 每页都要有导航名和页码
    ok(slides.every((s) => s.dataset.nav && s.dataset.page), '有幻灯片缺 data-nav / data-page');
    // 「？」卡必须带 reveal 文案，否则翻开是空的
    ok([...document.querySelectorAll('[data-qcards] button')].every((b) => b.dataset.reveal), '有「？」卡缺 data-reveal');

    // 匹配度环的静态状态必须自己就是对的。
    // 这条守的是导出路径：打印 / 后台标签页 / 无 JS 时 rAF 不跑，
    // 一旦 CSS 里少了 --pa:var(--p)，两个主视觉就会变成 0% 空环，
    // 而屏幕上看起来完全正常 —— 只有导出 PDF 才会暴露。
    [...document.querySelectorAll('.ring')].forEach((r) => {
      const p = r.style.getPropertyValue('--p').trim();
      const driving = r.style.getPropertyValue('--pa') !== ''; // JS 正在做扫弧动画
      const pa = getComputedStyle(r).getPropertyValue('--pa').trim();
      ok(p !== '', '有匹配度环没写 --p');
      if (!driving) {
        ok(pa === p, `环静态值错：--pa=${pa} 应为 ${p}（打印会导出空环）`);
        const num = r.querySelector('[data-count]');
        ok(!num || num.textContent.trim() === num.dataset.count,
          `环数字静态值错：${num && num.textContent} 应为 ${num && num.dataset.count}`);
      }
    });

    // 舞台缩放必须为正。窗口比 pad 还小时旧公式会算出负数，
    // 整个舞台会被翻转并缩成一个点，而且不报任何错。
    const sNow = Number(getComputedStyle(document.documentElement).getPropertyValue('--s'));
    ok(sNow > 0, `舞台缩放非正：--s=${sNow}`);

    // 权重条静态状态必须满格（同 ring：rAF 不跑时也要对）
    const wbox = document.querySelector('[data-weights]');
    if (wbox && !wbox.classList.contains('is-armed') && !wbox.classList.contains('is-run')) {
      const flat = [...wbox.querySelectorAll('.wbar i')]
        .filter((b) => /matrix\(0,/.test(getComputedStyle(b).transform));
      ok(!flat.length, `权重条静态值被压平 ${flat.length} 根（打印会导出空条）`);
    }

    // 读屏播报：翻页只换 is-on、焦点不动，没有 live region 就是无声的
    ok(el.live && el.live.getAttribute('aria-live') === 'polite', '缺 aria-live 播报节点');
    ok(el.live && el.live.textContent.includes('第'), 'live region 没有写入页码');

    // 标题层级不能跳级（h2 → h4 会让读屏以为漏了一层）
    const skips = [];
    slides.forEach((s, i) => {
      const lv = [...s.querySelectorAll('h1,h2,h3,h4')].map((h) => +h.tagName[1]);
      lv.forEach((v, j) => { if (j && v - lv[j - 1] > 1) skips.push(`p${i + 1}: h${lv[j - 1]}→h${v}`); });
    });
    ok(!skips.length, `标题跳级：${skips.join(', ')}`);

    // 对比度：绿底/珊瑚底小字最容易掉到 AA 以下，这里守住实际算出来的比值
    const lum = ([r, g, b]) => {
      const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const parseC = (s) => { const m = (s.match(/[\d.]+/g) || []).map(Number); return { rgb: m.slice(0, 3), a: m.length > 3 ? m[3] : 1 }; };
    const over = (fg, fa, bg) => fg.map((c, i) => c * fa + bg[i] * (1 - fa));
    const ratio = (a, b) => { const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x); return (l1 + 0.05) / (l2 + 0.05); };
    const bgOf = (n) => {
      const st = []; let e = n;
      while (e && e !== document.documentElement) {
        const p = parseC(getComputedStyle(e).backgroundColor);
        if (p.a > 0) { st.push(p); if (p.a === 1) break; }
        e = e.parentElement;
      }
      let b = [255, 252, 240];
      for (let i = st.length - 1; i >= 0; i--) b = over(st[i].rgb, st[i].a, b);
      return b;
    };
    const low = [];
    slides.forEach((s, i) => {
      const prev = s.className;
      s.classList.add('is-on');
      s.querySelectorAll('*').forEach((n) => {
        if (n.children.length || !n.textContent.trim()) return;
        const cs = getComputedStyle(n);
        if (cs.visibility === 'hidden' || cs.display === 'none') return;
        const fs = parseFloat(cs.fontSize), fw = Number(cs.fontWeight) || 400;
        const need = (fs >= 24 || (fs >= 18.66 && fw >= 700)) ? 3 : 4.5;
        const fc = parseC(cs.color), bg = bgOf(n);
        if (ratio(over(fc.rgb, fc.a, bg), bg) < need) low.push(`p${i + 1} .${n.className || n.tagName}`);
      });
      s.className = prev;
    });
    ok(!low.length, `对比度不达标 ${low.length} 处：${[...new Set(low)].slice(0, 5).join(', ')}`);

    // 23 页都必须装得下 1280×720，字体加载完再量
    document.fonts.ready.then(() => {
      const over2 = [];
      slides.forEach((s, i) => {
        const prev = s.className;
        s.classList.add('is-on');
        if (s.scrollHeight - s.clientHeight > 1 || s.scrollWidth - s.clientWidth > 1) {
          over2.push(`p${i + 1}(${s.dataset.nav})`);
        }
        s.className = prev;
      });
      show(at, { silent: true });
      if (over2.length) console.error(`selftest 溢出：${over2.join(', ')}`);
      else console.log('selftest 溢出检查通过');
    });

    console[fails.length ? 'error' : 'log'](
      fails.length ? `selftest 失败 ${fails.length} 项:\n- ${fails.join('\n- ')}` : 'selftest 通过'
    );
  }
})();
