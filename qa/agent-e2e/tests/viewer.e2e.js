import { beforeEach, describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';

describe('新版地图交互需求基线', () => {
  beforeEach(async ({ app, screen }) => {
    await app.open('/');
    await screen.getByText('正在加载 Blender 三维模型…').waitFor({ state: 'hidden', timeout: 30000 });
  });

  test('入口：审计按钮能打开来源信息', async ({ screen }) => {
    await screen.getByRole('button', '☷').tap();

    await expect(screen.getByText('代码与页面版本')).toBeVisible();
  });

  test('UI-04：提供第三个数据图层视图', async ({ screen }) => {
    await expect(screen.getByRole('button', /数据图层/)).toBeVisible();
  });

  test('UI-04：Escape退出审计并归还焦点', async ({ screen, browser }) => {
    await screen.getByRole('button', '☷').tap();
    await screen.getByText('代码与页面版本').waitFor({ state: 'visible' });

    await browser.keyboard.press('Escape');

    await expect(browser.locator('#audit-panel')).toBeHidden();
    await expect(screen.getByRole('button', '☷')).toBeFocused();
  });

  test('UI-05：未选设施时详情隐藏', async ({ browser }) => {
    await expect(browser.locator('#details')).toBeHidden();
  });
});
