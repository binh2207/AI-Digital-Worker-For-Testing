import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly addToCartButton: Locator;
  readonly cartLink: Locator;
  readonly greyJacketLink: Locator;
  readonly emptyCartMessage: Locator;
  readonly continueShoppingLink: Locator;
  // cart item row — fallbacks: tr.cart__row, tr:has(td:has-text("Grey jacket")), .cart__row
  // scope_locator: table.cart__table, form[action="/cart"]
  readonly cartItemRow: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.getByRole('button', { name: 'Add to Cart' });
    this.cartLink = page.locator('a[href="/cart"]');
    this.greyJacketLink = page.locator('a[href*="/products/grey-jacket"]');
    // locator_alternatives[0]: tr.cart__row — locator_alternatives[1]: tr:has(td:has-text("Grey jacket"))
    this.cartItemRow = page.locator('tr').filter({ hasText: /grey jacket/i }).first();
    this.emptyCartMessage = page.getByText('It appears that your cart is currently empty!');
    this.continueShoppingLink = page.getByRole('link', { name: 'Continue Shopping' });
  }

  async gotoProductPage(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket');
  }

  async gotoCartPage(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart');
  }

  async gotoEmptyCart(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart/change?line=1&quantity=0');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }
}