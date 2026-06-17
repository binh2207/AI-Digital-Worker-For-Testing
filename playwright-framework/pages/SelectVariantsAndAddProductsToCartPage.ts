import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly addToCartButton: Locator;
  readonly myCartLink: Locator;
  readonly myCartLinkInBanner: Locator;
  readonly checkOutLinkInBanner: Locator;
  readonly productHeading: Locator;
  readonly cartPrice: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.getByRole('button', { name: 'Add to Cart' });
    this.myCartLink = page.getByRole('link', { name: /My Cart/ });
    this.myCartLinkInBanner = page.getByRole('banner').getByRole('link', { name: /My Cart/ });
    this.checkOutLinkInBanner = page.getByRole('banner').getByRole('link', { name: 'Check Out' });
    this.productHeading = page.getByRole('heading', { name: 'Grey jacket - Grey jacket' });
    this.cartPrice = page.locator('.cart-price').first();
    this.continueShoppingLink = page.getByRole('link', { name: '« Continue Shopping' });
  }

  async gotoProductPage(): Promise<void> {
    await this.page.goto(
      'https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket',
    );
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async navigateToCart(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart');
    await this.page.waitForLoadState('load');
  }
}