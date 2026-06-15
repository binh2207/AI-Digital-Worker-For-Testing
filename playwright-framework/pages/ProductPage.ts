import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class ProductPage extends BasePage {
  readonly addToCartButton: Locator;
  readonly sizeDropdown: Locator;
  readonly colorDropdown: Locator;
  readonly cartCount: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.locator('button[type="submit"]:has-text("Add to cart")');
    this.sizeDropdown = page.locator('select[name="size"]');
    this.colorDropdown = page.locator('select[name="color"]');
    this.cartCount = page.locator('.cart-count');
  }

  async goto(handle: string) {
    await this.navigate(`/products/${handle}`);
    await this.waitForPageLoad();
  }

  async selectSize(size: string) {
    await this.sizeDropdown.selectOption({ label: size });
  }

  async selectColor(color: string) {
    await this.colorDropdown.selectOption({ label: color });
  }

  async addToCart() {
    await this.addToCartButton.click();
    await this.page.waitForResponse(r => r.url().includes('/cart/add'));
  }

  async getCartCount(): Promise<string> {
    return this.cartCount.innerText();
  }
}
