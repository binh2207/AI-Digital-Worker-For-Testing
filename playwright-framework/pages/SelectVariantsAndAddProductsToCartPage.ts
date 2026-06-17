import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly addToCartButton: Locator;
  readonly cartLinkBefore: Locator;
  readonly cartLinkAfter: Locator;
  readonly continueShoppingLink: Locator;
  readonly productTitle: Locator;
  readonly cartTotal: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.locator('input#add');
    this.cartLinkBefore = page.locator('a.cart-target');
    this.cartLinkAfter = page.locator('a.cart-target');
    this.continueShoppingLink = page.getByRole('link', { name: 'Continue Shopping' });
    this.productTitle = page.locator('h3');
    this.cartTotal = page.locator('h2');
  }

  async gotoProductPage(): Promise<void> {
    await this.page.goto(
      'https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket'
    );
  }

  async gotoCartPage(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async getCartLinkTextBefore(): Promise<string> {
    return (await this.cartLinkBefore.textContent()) ?? '';
  }

  async getCartLinkTextAfter(): Promise<string> {
    return (await this.cartLinkAfter.textContent()) ?? '';
  }
}