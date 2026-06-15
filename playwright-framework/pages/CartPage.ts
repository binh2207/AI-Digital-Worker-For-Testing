import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class CartPage extends BasePage {
  readonly cartItems: Locator;
  readonly emptyMessage: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.cartItems = page.locator('.cart__item');
    this.emptyMessage = page.locator('.cart__empty-text');
    this.continueShoppingLink = page.locator('a:has-text("Continue shopping")');
  }

  async goto() {
    await this.navigate('/cart');
    await this.waitForPageLoad();
  }

  async getItemCount(): Promise<number> {
    return this.cartItems.count();
  }

  async isEmpty(): Promise<boolean> {
    return this.emptyMessage.isVisible();
  }
}
