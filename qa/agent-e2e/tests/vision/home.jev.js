import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';

describe('Jev截图判断', () => {
test('视觉检查：地图中有地形和设施，页面有来源提示', async ({ app, browser, agent }) => {
  await app.open('/');
  await expect(browser.locator('#loading')).toBeHidden({ timeout: 30000 });
  await agent.assert('The map canvas visibly shows terrain and facilities, and the page has a source or verification status notice.', { vision: true });
});
});
