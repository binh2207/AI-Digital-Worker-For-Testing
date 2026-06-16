import { type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {

  readonly addToCartButton: Locator;
  readonly cartBadge: Locator;
  readonly cartItemName: Locator;
  readonly cartItemPrice: Locator;
  readonly continueShoppingLink: Locator;
  readonly emptyCartMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton      = page.locator('input[value="Add to Cart"]');
    this.cartBadge            = page.getByText(/My Cart \(\d+\)/).first();
    this.cartItemName         = page.getByText('Grey jacket');
    this.cartItemPrice        = page.getByText('£55.00');
    this.continueShoppingLink = page.getByRole('link', { name: '« Continue Shopping' });
    this.emptyCartMessage     = page.getByText('It appears that your cart is currently empty!');
  }

  async goto(): Promise<void> {
    await this.page.goto('/products/grey-jacket');
  }

  async gotoCart(): Promise<void> {
    await this.page.goto('/cart');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async getCartCount(): Promise<number> {
    const text = await this.cartBadge.textContent();
    const match = text?.match(/\((\d+)\)/);
    return match ? parseInt(match[1], 10) : 0;
  }

}