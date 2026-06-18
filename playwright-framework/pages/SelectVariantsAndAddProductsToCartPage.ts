import { type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly addToCartButton: Locator;
  readonly cartLink: Locator;
  readonly greyJacketCartLink: Locator;
  readonly greyJacketPrice: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.locator('#add');
    this.cartLink = page.getByRole('banner').getByRole('link', { name: /My Cart/ });
    this.greyJacketCartLink = page.locator('a[href*="/products/grey-jacket"]');
    this.greyJacketPrice = page.locator('.money').first();
    this.continueShoppingLink = page.locator('a[href*="/collections"]').filter({ hasText: /continue shopping/i });
  }

  async gotoProduct(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket');
  }

  async gotoCart(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }
}