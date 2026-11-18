// Floating UI bounds and the camera use the same measured workspace.
export function createWorkspaceLayout() {
  const root = document.documentElement;
  const byId = id => document.getElementById(id);
  const visibleRect = id => {
    const element = byId(id);
    return element.getClientRects().length ? element.getBoundingClientRect() : null;
  };
  function sync() {
    const toolbar = byId('toolbar').getBoundingClientRect();
    const footer = document.querySelector('footer').getBoundingClientRect();
    const index = visibleRect('index-panel');
    root.style.setProperty('--workspace-top', `${toolbar.bottom + 16}px`);
    root.style.setProperty('--workspace-bottom', `${footer.top - 12}px`);
    root.style.setProperty('--analysis-left', `${innerWidth > 850 && index ? index.right + 16 : 96}px`);
  }
  const observer = new ResizeObserver(sync);
  for (const element of [byId('toolbar'), document.querySelector('footer'), byId('index-panel')]) observer.observe(element);
  window.addEventListener('resize', sync);
  sync();
  return {
    sync,
    safeArea() {
      sync();
      const toolbar = byId('toolbar').getBoundingClientRect();
      const footer = document.querySelector('footer').getBoundingClientRect();
      const index = visibleRect('index-panel');
      const detail = visibleRect('route-detail') || visibleRect('detail');
      const analysis = visibleRect('analysis-panel');
      return {
        left: innerWidth <= 850 ? 90 : (index ? index.right + 20 : 96),
        right: innerWidth <= 850 ? innerWidth - 24 : (detail ? detail.left - 20 : innerWidth - 64),
        top: toolbar.bottom + 20,
        bottom: Math.min(footer.top - 20,
          innerWidth <= 850 && detail ? detail.top - 18 : Infinity,
          analysis ? analysis.top - 18 : Infinity),
      };
    },
  };
}
