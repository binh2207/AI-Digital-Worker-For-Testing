import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly variantSelect: Locator;
  readonly addToCartButton: Locator;
  readonly cartLink: Locator;
  readonly cartLinkInBanner: Locator;
  readonly greyJacketLink: Locator;
  readonly cartSubtotal: Locator;
  readonly continueShoppingLink: Locator;
  readonly emptyCartMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.variantSelect = page.locator('select#product-select-option-0');
    // fallbacks: ['.btn.add-to-cart', "input[type='submit'][value='Add to Cart']"]
    this.addToCartButton = page.locator('input#add');
    this.cartLink = page.getByRole('link', { name: /My Cart/ });
    this.cartLinkInBanner = page.getByRole('banner').getByRole('link', { name: /My Cart/ });
    this.greyJacketLink = page.getByRole('link', { name: /grey.?jacket/i });
    this.cartSubtotal = page.locator('.cart-subtotal, .total');
    this.continueShoppingLink = page.getByRole('link', { name: /Continue Shopping/ });
    this.emptyCartMessage = page.getByText('It appears that your cart is currently empty!', { exact: true });
  }

  async goto(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket');
  }

  async gotoCart(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket');
    await expect(this.addToCartButton).toBeAttached({ timeout: 10000 });
    await this.addToCartButton.click();
    await this.page.waitForLoadState('networkidle');
    await this.page.goto('https://sauce-demo.myshopify.com/cart');
    await this.page.waitForLoadState('domcontentloaded');
  }

  async gotoEmptyCart(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/cart/change?line=1&quantity=0');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }
}