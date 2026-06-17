import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly addToCartButton: Locator;
  readonly cartLink: Locator;
  readonly greyJacketLink: Locator;
  readonly cartPriceCell: Locator;
  readonly emptyCartMessage: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.locator('button[name="add"], input[name="add"]');
    this.cartLink = page.locator("a:has-text('My Cart')");
    this.greyJacketLink = page.locator("a[href*='/products/grey-jacket']");
    this.cartPriceCell = page.locator("td:has-text('£55.00'), .cart-price");
    this.emptyCartMessage = page.locator("p:has-text('It appears that your cart is currently empty')");
    this.continueShoppingLink = page.locator("a[href='/collections/all']:has-text('Continue Shopping')");
  }

  async goto(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket');
  }

  async gotoCart(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart');
  }

  async gotoEmptyCart(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart/change?line=1&quantity=0');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }
}