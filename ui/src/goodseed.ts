// Goodseed edition: discoverability and keyboard-accessible onboarding.
type CenterTab = 'live' | 'tasks' | 'feed' | 'skills' | 'eff';
export function mountGoodseed(actions: { search: () => Promise<void>; center: (tab: CenterTab) => void }) {
  const button = (id: string) => document.getElementById(id) as HTMLButtonElement;
  button('gs-search').onclick = () => void actions.search();
  let returnFocus: HTMLElement | null = null;
  const guide = document.createElement('dialog');
  guide.className = 'gs-guide';
  guide.setAttribute('aria-labelledby', 'gs-guide-title');
  guide.innerHTML = `<div class="gs-guide-heading"><span class="gs-eyebrow">GOODSEED · 0.1.1 · GSD</span><button id="gs-dismiss" aria-label="시작 안내 닫기">×</button></div>
    <h1 id="gs-guide-title">생각을, 실행으로.</h1><p class="gs-intro">터미널부터 AI 팀 관리까지. 필요한 도구를 한곳에서 시작하세요.</p>
    <div class="gs-cards">
      <button data-gs-action="terminal"><span class="gs-card-icon">▣</span><strong>터미널 열기</strong><span>명령 실행 · 작업 공간 분할</span><kbd>Ctrl T</kbd></button>
      <button data-gs-action="search"><span class="gs-card-icon">⌕</span><strong>빠르게 찾기</strong><span>명령 · 노드 · 역할 검색</span><kbd>Ctrl K</kbd></button>
      <button data-gs-action="live"><span class="gs-card-icon">◫</span><strong>작업 현황 보기</strong><span>실시간 세션 · 사용량 모니터링</span><span class="gs-card-link">현황 열기 →</span></button>
    </div>
    <div class="gs-guide-bottom"><section><h2>작업 흐름</h2><ol><li>터미널을 열고 프로젝트 폴더로 이동합니다.</li><li>설치된 Claude · Codex 등의 CLI로 작업합니다.</li><li>작업 현황에서 세션과 승인 요청을 확인합니다.</li></ol><div class="gs-links"><button data-gs-action="tasks">작업 목록</button><button data-gs-action="feed">승인 요청</button><button data-gs-action="eff">비용·효율</button></div></section>
    <section><h2>편리한 조작</h2><dl><dt>좌우 / 상하 분할</dt><dd>Ctrl D / Ctrl Shift D</dd><dt>글자 확대 / 축소</dt><dd>Ctrl + / Ctrl −</dd><dt>집중 모드</dt><dd>화면 상단에서 전환</dd></dl><p class="gs-note">AI CLI 설치·로그인은 별도입니다. 계정·세션은 별도로 설정합니다.</p></section></div>
    <footer><div><strong>Goodseed · 오경근박사</strong><br><small>MIT License · 저작권·출처 고지: LICENSE / NOTICE</small></div><label><input id="gs-on-start" type="checkbox" /> 시작할 때 표시</label></footer>`;
  document.body.append(guide);
  const location = document.createElement('p');
  location.className = 'gs-note';
  location.id = 'gs-output-location';
  location.textContent = '기본 결과물 폴더: 바탕화면의 goodseed';
  guide.querySelector('footer')!.before(location);
  if (window.__TAURI__) {
    void window.__TAURI__.core.invoke('workspace_dir').then(path => {
      location.textContent = '기본 결과물 폴더: ' + String(path);
    }).catch(() => { location.textContent = '결과물 폴더를 열 수 없습니다. 저장 위치와 권한을 확인하세요.'; });
  }
  const onStart = guide.querySelector('#gs-on-start') as HTMLInputElement;
  onStart.checked = localStorage.getItem('goodseed-guide') !== 'off';
  onStart.onchange = () => localStorage.setItem('goodseed-guide', onStart.checked ? 'on' : 'off');
  const close = () => guide.close();
  guide.addEventListener('close', () => returnFocus?.focus());
  guide.querySelector('#gs-dismiss')!.addEventListener('click', close);
  guide.addEventListener('click', e => { if (e.target === guide) { const r=guide.getBoundingClientRect(); const m=e as MouseEvent; if(m.clientX<r.left||m.clientX>r.right||m.clientY<r.top||m.clientY>r.bottom)close(); } });
  const showGuide = () => { if(guide.open)return; returnFocus=document.activeElement as HTMLElement; guide.showModal(); };
  button('gs-home').onclick = showGuide;
  guide.querySelectorAll<HTMLButtonElement>('[data-gs-action]').forEach(b => b.onclick = () => {
    close(); const action=b.dataset.gsAction;
    if(action==='terminal')button('btn-new').click();
    else if(action==='search')void actions.search();
    else actions.center(action as CenterTab);
  });
  button('gs-focus').onclick = () => {
    const on=document.body.classList.toggle('gs-focused');
    button('gs-focus').setAttribute('aria-pressed',String(on));
    button('gs-focus').textContent=on?'집중 모드 종료':'집중 모드';
    window.dispatchEvent(new Event('resize'));
  };
  // Native dialog handles Escape, focus trapping and restoration. IME remains untouched.
  if(onStart.checked)showGuide();
}
