
import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

const BASE_URL = 'https://sauce-demo.myshopify.com';

export class SelectVariantsAndAddToCartPage extends BasePage {
  readonly variantCombobox: Locator;
  readonly addToCartButton: Locator;
  readonly cartBadge: Locator;
  readonly cartLineItem: Locator;
  readonly cartLineItemPrice: Locator;
  readonly emptyCartMessage: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.variantCombobox = page.getByRole('combobox');
    this.addToCartButton = page.getByRole('button', { name: /add to cart/i });
    this.cartBadge = page.getByRole('link', { name: /my cart/i });
    this.cartLineItem = page.getByText(/grey jacket/i).first();
    this.cartLineItemPrice = page.getByText(/£\d+\.\d{2}/);
    this.emptyCartMessage = page.getByText('It appears that your cart is currently empty!');
    this.continueShoppingLink = page.getByRole('link', { name: 'Continue Shopping' });
  }

  async gotoProduct(): Promise<void> {
    await this.page.goto(`${BASE_URL}/products/grey-jacket`);
  }

  async gotoCart(): Promise<void> {
    await this.page.goto(`${BASE_URL}/cart`);
  }

  async addToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async clickContinueShopping(): Promise<void> {
    await this.continueShoppingLink.click();
  }

  async getCartCount(): Promise<number> {
    const text = await this.cartBadge.textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0], 10) : 0;
  }
}
